#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AC-22：capstone-rehearse 业务代码行覆盖率 ≥80%。

复用 `scripts/measure_coverage.py#measure(modules, test_names)` 的既有实现，
不改共享脚本、不改 CI 接线（ADR-0006 去冲突约定）；本文件不在被测 test_names
内，避免覆盖率度量的递归重入。
"""
import importlib
import os
import sys
import unittest

from tests._paths import ROOT  # noqa: E402
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts import measure_coverage  # noqa: E402

MODULE_NAMES = ("model", "inventory", "clock", "walk", "report", "evidence", "cli")
TEST_NAMES = ("tests.capstone_rehearse.test_capstone_rehearse",
              "tests.capstone_rehearse.test_capstone_rehearse_evidence_contract")


class CoverageTests(unittest.TestCase):
    def test_ac22_line_coverage_at_least_80(self):
        mods = [importlib.import_module("tools.capstone_rehearse." + n)
                for n in MODULE_NAMES]
        result, rows, covered, total = measure_coverage.measure(
            mods, list(TEST_NAMES))
        self.assertTrue(result.wasSuccessful(),
                        "覆盖率窗口内用例须全部通过：%s" % (result.failures,))
        pct = 100.0 * covered / total if total else 100.0
        detail = "; ".join("%s %.1f%%" % (name, p) for name, _l, _h, p in rows)
        self.assertGreaterEqual(pct, 80.0, "覆盖率 %.1f%% < 80%%；明细：%s" % (pct, detail))


if __name__ == "__main__":
    unittest.main()
