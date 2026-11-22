#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B6 模块行覆盖率门禁（≥90%）。

复用 `scripts/measure_coverage.py#measure` tracer（C1），不改共享
`measure_coverage.py`/`tools_manifest.json`（两文件在其它 worktree 有 staged 改动）。
用法：python scripts/verify_asc_b6_coverage.py --min 90
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import measure_coverage as mc  # noqa: E402
from tools.attack_supply_chain import ch9_boundary, ch9_boundary_model  # noqa: E402
from tools.attack_supply_chain import ch9_boundary_evidence, ch9_boundary_runner  # noqa: E402

MODULES = [ch9_boundary, ch9_boundary_model, ch9_boundary_evidence, ch9_boundary_runner]
TESTS = ["tests.attack_supply_chain.test_asc_b6_hardening"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min", type=float, default=90.0)
    args = ap.parse_args(argv)
    result, rows, covered, total = mc.measure(modules=MODULES, test_names=TESTS)
    for name, lines, hit, pct in rows:
        print("%-24s 可执行行=%3d 覆盖=%3d 覆盖率=%5.1f%%" % (name, lines, hit, pct))
    pct = 100.0 * covered / total if total else 100.0
    print("总计 %d/%d = %.1f%%（门槛 %.1f%%）" % (covered, total, pct, args.min))
    if result.failures or result.errors:
        print("测试失败=%d 错误=%d" % (len(result.failures), len(result.errors)))
        return 1
    return 0 if pct >= args.min else 1


if __name__ == "__main__":
    raise SystemExit(main())
