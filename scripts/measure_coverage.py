#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""标准库行覆盖率测量（CI-CD §3 S2 / 阶段 9 门禁复现命令）。

零外部依赖：用 `code.co_lines()` 取真实可执行行集合，用 `sys.settrace`
记录 `line` 事件，二者求交得到行覆盖率。避免 `trace.Trace` 的 ignoredirs
过滤与 AST 语句起始行错位造成的假阴性。

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

# --target all 的聚合顺序与改造前逐项一致（保证覆盖率明细输出顺序稳定）。
ALL_TARGET_ORDER = (
    "attack-ai-agent", "report-exam", "recon-ai", "attack-mcp-tool",
    "attack-supply-chain", "decoy-detect", "loot-manage", "attack-multi-agent",
    "attack-embeddings", "threat-model", "attack-rag", "verify-evidence",
    "attack-infra", "tooling-automate",
    "attack-jailbreak",
    "attack-multimodal",
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
            entry = _TARGETS[name]
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


def measure(modules=None, test_names=None):
    modules = list(AA_MODULES) if modules is None else modules
    test_names = list(AA_TESTS) if test_names is None else test_names
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
        # 在追踪窗口内重载模块，使模块顶层可执行行也计入覆盖率，
        # 避免「导入发生在 settrace 之前」造成的系统性假阴性。
        import importlib
        for module in modules:
            importlib.reload(module)
        suite = unittest.defaultTestLoader.loadTestsFromNames(list(test_names))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return unittest.TextTestRunner(verbosity=0).run(suite)

    sys.settrace(tracer)
    try:
        result = run()
    finally:
        sys.settrace(None)

    total = covered = 0
    rows = []
    for module in modules:
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


def main(argv=None):
    ap = argparse.ArgumentParser(description="标准库行覆盖率测量")
    ap.add_argument("--min", type=float, default=0.0, help="覆盖率门槛（百分比）")
    ap.add_argument("--target", default="attack-ai-agent",
                    choices=tuple(ALL_TARGET_ORDER) + ("all",),
                    help="被测业务代码集合（默认 attack-ai-agent；清单见 scripts/tools_manifest.json）")
    args = ap.parse_args(argv)

    modules, test_names = resolve_target(args.target)
    result, rows, covered, total = measure(modules, test_names)
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
