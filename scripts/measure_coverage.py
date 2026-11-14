#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""标准库行覆盖率测量（CI-CD §3 S2 / 阶段 9 门禁复现命令）。

零外部依赖：用 `code.co_lines()` 取真实可执行行集合，用 `sys.settrace`
记录 `line` 事件，二者求交得到行覆盖率。避免 `trace.Trace` 的 ignoredirs
过滤与 AST 语句起始行错位造成的假阴性。

用法：
  python scripts/measure_coverage.py            # 全量输出
  python scripts/measure_coverage.py --min 80  # 低于门槛时以退出码 1 失败
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

from tools.attack_ai_agent import backends, paths, runner, steps  # noqa: E402

MODULES = (runner, backends, paths, steps)
TEST_NAMES = ("tests.test_attack_ai_agent_runner",
              "tests.test_attack_ai_agent_evidence_contract",
              "tests.test_attack_ai_agent_adapters")


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


def measure():
    targets = {os.path.normcase(os.path.abspath(m.__file__)): m for m in MODULES}
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
        for module in MODULES:
            importlib.reload(module)
        suite = unittest.defaultTestLoader.loadTestsFromNames(list(TEST_NAMES))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return unittest.TextTestRunner(verbosity=0).run(suite)

    sys.settrace(tracer)
    try:
        result = run()
    finally:
        sys.settrace(None)

    total = covered = 0
    rows = []
    for module in MODULES:
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
    args = ap.parse_args(argv)

    result, rows, covered, total = measure()
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
