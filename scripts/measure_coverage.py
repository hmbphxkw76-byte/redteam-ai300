#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""标准库行覆盖率测量（CI-CD §3 S2 / 阶段 9 门禁复现命令）。

零外部依赖：用 `code.co_lines()` 取真实可执行行集合，用 `sys.settrace`
记录 `line` 事件，二者求交得到行覆盖率。避免 `trace.Trace` 的 ignoredirs
过滤与 AST 语句起始行错位造成的假阴性。

线程化服务（如 `ThreadingHTTPServer`）的请求处理器运行在**子线程**，而
`sys.settrace` 只作用于当前线程；因此同时注册 `threading.settrace`，否则
整段 handler 会被系统性误判为未覆盖（本仓 attack-mcp-tool 的 poison.py
曾因此由 95.3% 被误报为 68.6%）。

用法：
  python scripts/measure_coverage.py                       # attack-ai-agent（默认，兼容既有 CI）
  python scripts/measure_coverage.py --min 80              # 低于门槛时以退出码 1 失败
  python scripts/measure_coverage.py --target report-exam # 仅 report-exam 业务代码
  python scripts/measure_coverage.py --target all --min 80  # 全部业务代码（CI S2）
"""
import argparse
import contextlib
import io
import os
import sys
import threading
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import importlib
import json

MANIFEST_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             "tools_manifest.json")


def _load_manifest():
    """读取显式清单（scripts/tools_manifest.json），返回解析后的字典。"""
    with open(MANIFEST_PATH, encoding="utf-8") as handle:
        return json.load(handle)


_MANIFEST = _load_manifest()
_TARGETS = {row["name"]: row for row in _MANIFEST["coverage_targets"]}

# --target all 的聚合顺序：既有目标保持改造前的稳定顺序，其余按清单注册顺序追加。
# 单一事实源是 tools_manifest.json；本常量只决定输出次序，不得成为「目标是否可用」的白名单
# （否则新登记的目标无法被 --target 选择，C1 失效）。
_PREFERRED_ORDER = (
    "attack-ai-agent", "report-exam", "recon-ai", "attack-mcp-tool",
    "attack-supply-chain", "decoy-detect", "loot-manage", "attack-multi-agent",
    "attack-embeddings", "threat-model", "attack-rag", "verify-evidence",
    "attack-infra", "tooling-automate",
    "attack-jailbreak",
    "attack-multimodal",
    "pyrit-compat",
    "osai-orchestrator",
    "target-profile",
    "osai-exam-readiness",
    "foothold-ad",
)

ALL_TARGET_ORDER = tuple(n for n in _PREFERRED_ORDER if n in _TARGETS) + tuple(
    n for n in _TARGETS if n not in _PREFERRED_ORDER
)


def _modules_for(entry):
    """按清单条目导入模块；保留原 importlib 方式避开 __init__ 同名覆盖。"""
    return tuple(importlib.import_module(name) for name in entry["modules"])


AA_MODULES = _modules_for(_TARGETS["attack-ai-agent"])
AA_TESTS = tuple(_TARGETS["attack-ai-agent"]["tests"])


def resolve_target(mode):
    """解析 --target：返回 (模块对象列表, 测试点分名列表)。

    单一事实源为 scripts/tools_manifest.json；本函数只做导入与聚合，
    不内嵌任何测试名（AGENTS.md C1）。
    """
    if mode == "all":
        modules, tests = [], []
        for name in ALL_TARGET_ORDER:
            entry = _TARGETS[name]   # ALL_TARGET_ORDER 已按清单派生，必命中
            modules.extend(_modules_for(entry))
            tests.extend(entry["tests"])
        return modules, tests
    entry = _TARGETS.get(mode)
    if entry is None:
        raise ValueError("未知 --target：%s" % mode)
    return list(_modules_for(entry)), list(entry["tests"])


def executable_lines(code):
    """递归收集一个代码对象及其嵌套代码对象的可执行行号。"""
    out = set()
    # co_lines() 元组为 (start_offset, end_offset, lineno)；行覆盖率取 lineno，
    # 不能取 start_offset（那是字节码偏移）。
    try:
        for _start, _end, lineno in code.co_lines():
            if lineno is not None:
                out.add(lineno)
    except AttributeError:
        out.update(line for _s, _e, line in code.co_lines() if line is not None)
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            out.update(executable_lines(const))
    return out


def measure(modules=None, test_names=None, import_mode="reload"):
    """测量覆盖率。

    `import_mode` 决定如何在追踪窗口内取得「模块顶层行」：
    - `reload`（默认，与历史口径一致）：`importlib.reload` 各目标模块；
      不改变既有目标的数字，但依赖方可能持有重载前的类引用。
    - `purge`：清 `sys.modules` 后重新导入目标模块与测试模块，引用一致；
      用于修不了 reload 兼容性的目标（如 `foothold-traditional`）。
    """
    modules = list(AA_MODULES) if modules is None else modules
    test_names = list(AA_TESTS) if test_names is None else test_names
    module_names = [m.__name__ for m in modules]
    targets = {os.path.normcase(os.path.abspath(m.__file__)): m for m in modules}
    seen = {key: set() for key in targets}

    def tracer(frame, event, arg):
        key = os.path.normcase(os.path.abspath(frame.f_code.co_filename))
        if key in targets:
            if event == "call":
                return tracer
            if event == "line":
                seen[key].add(frame.f_lineno)
        return None

    def run():
        # 在追踪窗口内「清缓存后重新导入」，使模块顶层可执行行也计入覆盖率。
        # 不使用 importlib.reload：reload 只换本模块对象，依赖方仍持旧类引用，
        # 会让 tests 里的 isinstance 断言失效（foothold-traditional 实测踩到）。
        # 连测试模块一并清空，保证两侧引用同一批新对象。
        if import_mode == "purge":
            for name in list(module_names) + list(test_names):
                sys.modules.pop(name, None)
            measured = [importlib.import_module(name) for name in module_names]
        else:
            measured = [importlib.reload(module) for module in modules]
        suite = unittest.defaultTestLoader.loadTestsFromNames(list(test_names))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return unittest.TextTestRunner(verbosity=0).run(suite), measured

    snapshot = dict(sys.modules)   # 测量前后还原，避免 --target all 跨目标互相污染
    sys.settrace(tracer)
    threading.settrace(tracer)  # 子线程（HTTP handler 等）同样计入，避免系统性假阴性
    try:
        result, measured_modules = run()
    finally:
        sys.settrace(None)
        threading.settrace(None)
        sys.modules.clear()
        sys.modules.update(snapshot)

    total = covered = 0
    rows = []
    for module in measured_modules:
        filename = module.__file__
        key = os.path.normcase(os.path.abspath(filename))
        with open(filename, encoding="utf-8") as handle:
            code = compile(handle.read(), filename, "exec")
        lines = executable_lines(code)
        hit = len(lines & seen[key])
        pct = 100.0 * hit / len(lines) if lines else 100.0
        rows.append((os.path.basename(filename), len(lines), hit, pct))
        total += len(lines)
        covered += hit
    return result, rows, covered, total


def measure_best(modules, test_names):
    """先按历史语义（reload）测量；若出现失败/错误，再用 purge 重测。

    取「零失败」的那次结果；两次都有失败时返回首次结果，交由调用方按失败退出。
    每次尝试后还原 `sys.modules` 快照，保证两次尝试互不污染。
    """
    first = None
    for mode in ("reload", "purge"):
        snapshot = dict(sys.modules)
        try:
            result = measure(modules, test_names, import_mode=mode)
        finally:
            sys.modules.clear()
            sys.modules.update(snapshot)
        if result[0].wasSuccessful():
            return result
        if first is None:
            first = result
    return first


def _measure_all(min_pct):
    """`--target all`：逐目标在独立子进程中测量后聚合。

    同一进程内连续测量会互相污染（本进程清 `sys.modules` 后重新导入，会让前一个
    目标留下的依赖模块持有旧类引用，`isinstance` 断言随之失效——实测 3 失败 16 错误）。
    逐目标起子进程等价于每个目标跑一次干净的解释器，聚合口径不变。
    """
    import re
    import subprocess
    total = covered = 0
    failed = False
    for name in ALL_TARGET_ORDER:
        proc = subprocess.run([sys.executable, os.path.abspath(__file__), "--target", name],
                              capture_output=True, text=True)
        out = proc.stdout
        sys.stdout.write(out)
        if proc.returncode != 0:
            failed = True
        match = re.search(r"总计 (\d+)/(\d+) = ", out)
        if match:
            covered += int(match.group(1))
            total += int(match.group(2))
        if proc.stderr.strip():
            sys.stderr.write(proc.stderr)
    overall = 100.0 * covered / total if total else 100.0
    print("总计 %d/%d = %.1f%%（门槛 %.1f%%，%d 个目标）"
          % (covered, total, overall, min_pct, len(ALL_TARGET_ORDER)))
    return 1 if failed or overall < min_pct else 0


def _measure_best_target(name):
    """按目标名取模块后择优测量，返回 (result, rows, covered, total)。"""
    modules, test_names = resolve_target(name)
    return measure_best(modules, test_names)


def main(argv=None):
    ap = argparse.ArgumentParser(description="标准库行覆盖率测量")
    ap.add_argument("--min", type=float, default=0.0, help="覆盖率门槛（百分比）")
    ap.add_argument("--target", default="attack-ai-agent",
                    choices=tuple(ALL_TARGET_ORDER) + ("all",),
                    help="被测业务代码集合（默认 attack-ai-agent；清单见 scripts/tools_manifest.json）")
    args = ap.parse_args(argv)

    if args.target == "all":
        return _measure_all(args.min)

    modules, test_names = resolve_target(args.target)
    result, rows, covered, total = _measure_best_target(args.target)
    overall = 100.0 * covered / total if total else 100.0
    print("测试数 %d，失败 %d，错误 %d" %
          (result.testsRun, len(result.failures), len(result.errors)))
    for name, lines, hit, pct in rows:
        print("%-18s 可执行行=%3d 覆盖=%3d 覆盖率=%5.1f%%" % (name, lines, hit, pct))
    print("总计 %d/%d = %.1f%%（门槛 %.1f%%）" % (covered, total, overall, args.min))
    failed = (not result.wasSuccessful()) or overall < args.min
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
