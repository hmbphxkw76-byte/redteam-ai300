#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AC-16..AC-19：运行目录隔离、双跑幂等、报告全量化与门禁一致性。"""
import json
import os
import sys
import tempfile
import unittest

from tests._paths import ROOT  # noqa: E402
sys.path.insert(0, ROOT)

from tests.support import recon_ai_fixtures as fx  # noqa: E402
from tools.recon_ai import evidence, runner, shot, verifier  # noqa: E402
from tools.recon_ai.transport import FakeTransport  # noqa: E402


def _run(tmp, target=fx.TARGET_LEGACY):
    return runner.run_recon(
        target=target, out_dir=tmp,
        transport=FakeTransport(fx.legacy_routes(target)),
        shot=shot.FakeShot(), capture_shots=True)


class ClosedLoopTests(unittest.TestCase):
    def test_run_scoped_artifacts_and_idempotent_second_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            first = _run(tmp)
            second = _run(tmp)
            self.assertNotEqual(first.run_id, second.run_id)
            for report in (first, second):
                self.assertTrue(os.path.isdir(report.run_dir))
                for name in ("run.json", "verification.json", "MANIFEST.jsonl",
                             "ai-assets.md", "ai-assets.json",
                             "verification-report.md"):
                    self.assertTrue(
                        os.path.isfile(os.path.join(report.run_dir, name)),
                        "%s 缺 %s" % (report.run_id, name))
                self.assertEqual(len(evidence.load_manifest(report.manifest)), 7)
                self.assertEqual(report.verification.verdict, "PASS")
            again = verifier.verify_run(first.run_dir)
            self.assertEqual(again.verdict, "PASS",
                             "首跑在次跑后复算仍须 PASS（清单按运行窗口隔离）")
            self.assertTrue(os.path.isfile(os.path.join(tmp, "ai-assets.json")))
            self.assertTrue(os.path.isfile(os.path.join(tmp, "verification-report.md")))

    def test_report_has_quantified_fields_and_gate_conclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = _run(tmp)
            with open(report.report_md, encoding="utf-8") as f:
                text = f.read()
            with open(report.run_json, encoding="utf-8") as f:
                meta = json.load(f)
        for token in ("- **运行标识**：", "- **应用族**：", "## 1. 覆盖矩阵",
                      "## 2. 证据核对表", "## 3. 缺口台账", "## 4. 自校验门禁",
                      "## 5. 复现命令", "## 6. 结论", "- **判定**：PASS",
                      "C1 步骤全覆盖", "C9 结论一致性"):
            self.assertIn(token, text)
        self.assertEqual(meta["verification"]["verdict"], "PASS")
        self.assertEqual(len(meta["steps"]), 7)
        self.assertEqual(len(meta["evidence_paths"]), 7)


if __name__ == "__main__":
    unittest.main()
