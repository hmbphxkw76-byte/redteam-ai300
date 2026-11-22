#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 foothold-traditional 模块行覆盖率门禁（本轮 ≥90%）。

复用 `scripts/measure_coverage.py#measure/executable_lines` 的 tracer 逻辑（C1），
不修改共享文件 `tools_manifest.json` / `measure_coverage.py`（其在其它 worktree 有 staged 改动，ADR-0006）。
用法：python scripts/verify_ch9_ft_coverage.py [--min 90]
"""
import argparse
import sys

ROOT = __import__("os").path.dirname(__import__("os").path.dirname(
    __import__("os").path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import measure_coverage as mc  # noqa: E402
from tools.foothold_traditional import ch9_model, ch9_entry, ch9_evidence, ch9_runner  # noqa: E402

MODULES = [ch9_model, ch9_entry, ch9_evidence, ch9_runner]
TESTS = ["tests.foothold_traditional.test_foothold_traditional_ch9_hardening"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min", type=float, default=90.0)
    args = ap.parse_args(argv)
    result, rows, covered, total = mc.measure(modules=MODULES, test_names=TESTS)
    for name, lines, hit, pct in rows:
        print("%-18s 可执行行=%3d 覆盖=%3d 覆盖率=%5.1f%%" % (name, lines, hit, pct))
    pct = 100.0 * covered / total if total else 100.0
    print("总计 %d/%d = %.1f%%（门槛 %.1f%%）" % (covered, total, pct, args.min))
    if result.failures or result.errors:
        print("测试失败=%d 错误=%d" % (len(result.failures), len(result.errors)))
        return 1
    return 0 if pct >= args.min else 1


if __name__ == "__main__":
    raise SystemExit(main())
