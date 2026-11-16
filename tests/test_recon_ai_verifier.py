#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AC-06..AC-12：C1–C9 门禁对证据缺失、陈旧、清单漂移与结论矛盾的拦截。"""
import io
import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

import recon_ai_fixtures as fx  # noqa: E402
from tools.recon_ai import cli, evidence, shot, verifier  # noqa: E402


def _fresh(tmp):
    return fx.run_fake(tmp, fx.legacy_routes())


def _checks(result):
    return {check.name: check for check in result.checks}


class VerifierGateTests(unittest.TestCase):
    def test_clean_run_passes_all_gates(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = _fresh(tmp)
            self.assertEqual(report.verification.verdict, "PASS")
            self.assertTrue(all(c.ok for c in report.verification.checks))
            self.assertTrue(os.path.isfile(report.verification_json))
            with open(report.verification_json, encoding="utf-8") as f:
                data = json.load(f)
        self.assertEqual(data["verdict"], "PASS")
        self.assertEqual(len(data["checks"]), 10)

    def test_deleted_fragment_blocks_c2(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = _fresh(tmp)
            os.remove(os.path.join(report.run_dir, "recon-03.md"))
            result = verifier.verify_run(report.run_dir)
        self.assertFalse(_checks(result)["C2 证据新鲜度"].ok)
        self.assertEqual(result.verdict, "BLOCKED")

    def test_stale_fragment_blocks_c2(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = _fresh(tmp)
            path = os.path.join(report.run_dir, "recon-01.md")
            old = (datetime.now() - timedelta(days=2)).timestamp()
            os.utime(path, (old, old))
            result = verifier.verify_run(report.run_dir)
        self.assertFalse(_checks(result)["C2 证据新鲜度"].ok)

    def test_missing_section_blocks_c3(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = _fresh(tmp)
            path = os.path.join(report.run_dir, "recon-02.md")
            with io.open(path, encoding="utf-8") as f:
                text = f.read().replace("关键输出", "输出")
            with io.open(path, "w", encoding="utf-8") as f:
                f.write(text)
            result = verifier.verify_run(report.run_dir)
        self.assertFalse(_checks(result)["C3 三件套结构"].ok)

    def test_manifest_target_drift_blocks_c5(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = _fresh(tmp)
            records = evidence.load_manifest(report.manifest)
            records[0]["target"] = "http://other"
            with open(report.manifest, "w", encoding="utf-8") as f:
                for record in records:
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
            result = verifier.verify_run(report.run_dir)
        self.assertFalse(_checks(result)["C5 清单一致性"].ok)

    def test_missing_report_section_blocks_c8(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = _fresh(tmp)
            with open(report.report_md, encoding="utf-8") as f:
                text = f.read()
            with open(report.report_md, "w", encoding="utf-8") as f:
                f.write(text.replace("## 3. 缺口台账", "## 缺口"))
            result = verifier.verify_run(report.run_dir)
        self.assertFalse(_checks(result)["C8 报告结构"].ok)

    def test_conclusion_mismatch_blocks_c9(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = _fresh(tmp)
            with open(report.report_md, encoding="utf-8") as f:
                text = f.read()
            with open(report.report_md, "w", encoding="utf-8") as f:
                f.write(text.replace("- **判定**：PASS", "- **判定**：BLOCKED"))
            result = verifier.verify_run(report.run_dir)
            verifier.finalize(result, report.report_md)
        self.assertFalse(_checks(result)["C9 结论一致性"].ok)
        self.assertEqual(result.verdict, "BLOCKED")

    def test_pending_screenshot_blocks_c4(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = fx.run_fake(tmp, fx.legacy_routes(), shot_impl=shot.NullShot())
            result = verifier.verify_run(report.run_dir)
        self.assertFalse(_checks(result)["C4 截图状态"].ok)
        self.assertEqual(result.verdict, "BLOCKED")

    def test_corrupt_run_json_reports_c1_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            with io.open(os.path.join(tmp, "run.json"), "w", encoding="utf-8") as f:
                f.write("{bad")
            result = verifier.verify_run(tmp)
        self.assertEqual(len(result.checks), 1)
        self.assertFalse(result.checks[0].ok)
        self.assertEqual(result.verdict, "BLOCKED")

    def test_cli_verify_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = _fresh(tmp)
            self.assertEqual(cli.main(["verify", "--run", report.run_dir]), 0)
            os.remove(os.path.join(report.run_dir, "recon-04.md"))
            self.assertEqual(cli.main(["verify", "--run", report.run_dir]), 1)


if __name__ == "__main__":
    unittest.main()
