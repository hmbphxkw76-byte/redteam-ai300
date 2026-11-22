#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C1 模块行覆盖率门禁（≥90%）；复用 measure_coverage.measure（C1）。"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import measure_coverage as mc  # noqa: E402
from tools.recon_ai import ch9_c1_asset, ch9_c1_model, ch9_cloud_surface  # noqa: E402

MODULES = [ch9_c1_model, ch9_cloud_surface, ch9_c1_asset]
TESTS = ["tests.recon_ai.test_recon_ai_c1_hardening"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min", type=float, default=90.0)
    args = ap.parse_args(argv)
    result, rows, covered, total = mc.measure(modules=MODULES, test_names=TESTS)
    for name, lines, hit, pct in rows:
        print("%-22s 可执行行=%3d 覆盖=%3d 覆盖率=%5.1f%%" % (name, lines, hit, pct))
    pct = 100.0 * covered / total if total else 100.0
    print("总计 %d/%d = %.1f%%（门槛 %.1f%%）" % (covered, total, pct, args.min))
    if result.failures or result.errors:
        print("测试失败=%d 错误=%d" % (len(result.failures), len(result.errors)))
        return 1
    return 0 if pct >= args.min else 1


if __name__ == "__main__":
    raise SystemExit(main())
