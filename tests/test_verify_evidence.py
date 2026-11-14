"""verify-evidence 机读校验器自测（T07 / CI S2）。

四类夹具：合规 / 缺面板 flag / 重复 proof.txt / 缺章节，外加 dry-run、
命名体积、AI 日志附录、术语证据区间豁免与 CLI 退出码。标准库 unittest，零依赖。
"""
import contextlib
import importlib.util
import io
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_spec = importlib.util.spec_from_file_location(
    "verify_evidence_shared", os.path.join(ROOT, "tools", "verify_evidence.py"))
VE = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(VE)

COPYRIGHT = "Copyright © 2026 OffSec Ltd. All rights reserved."
ANCHORS = VE.REQUIRED_ANCHORS


def report_text():
    return "\n\n".join([
        "# OSID: 12345", COPYRIGHT, "# Offsec AI Red Teamer Report",
        "## Introduction", "## Objective", "## Requirements",
        "# Executive Summary", "## High-Level Attack Path",
        "## Target Inventory & Point Allocation", "# Attack Walkthrough",
        "# Appendix",
    ])


def frag(step="aia-01", host="standalone", flag="", ai_log="", **kw):
    base = dict(step_id=step, host=host, command="id", output="uid=0(root)",
                screenshot="shots/aia-01.png", ai_log=ai_log, flag=flag)
    base.update(kw)
    return base


def payload(report=None, appendix="", frags=None, panel=None, pdf=None, zip_path=None):
    return {
        "report_md": report_text() if report is None else report,
        "appendix_md": appendix,
        "osid": "12345",
        "fragments": [] if frags is None else frags,
        "panel_flags": {} if panel is None else panel,
        "pdf_path": pdf,
        "zip_path": zip_path,
    }


class VerifyEvidenceTests(unittest.TestCase):

    def _artifacts(self, d):
        pdf = os.path.join(d, "OSAI-OS-12345-Exam-Report.pdf")
        arc = os.path.join(d, "OSAI-OS-12345-Exam-Report.7z")
        with open(pdf, "wb") as f:
            f.write(b"%PDF-1.7\n")
        with open(arc, "wb") as f:
            f.write(b"7z-archive")
        return pdf, arc

    def test_compliant_payload_all_eight_checks_pass(self):
        with tempfile.TemporaryDirectory() as d:
            pdf, arc = self._artifacts(d)
            p = payload(appendix="prompt: p\n",
                        frags=[frag(flag="OSAI{x}", ai_log="prompt: p")],
                        panel={"standalone": "OSAI{x}"}, pdf=pdf, zip_path=arc)
            r = VE.verify(p, require_artifacts=True)
            for k in ["vrf-01", "vrf-02", "vrf-03", "vrf-04", "vrf-05",
                      "vrf-06", "vrf-07", "vrf-08", "proof-single"]:
                with self.subTest(check=k):
                    self.assertIs(r["checks"][k], True)
            self.assertTrue(r["passed"], str(r["blocking"]))
            self.assertTrue(r["submission_ready"])
            self.assertEqual(r["pending"], [])

    def test_missing_panel_flag_is_blocking(self):
        p = payload(frags=[frag(flag="OSAI{x}")], panel={})
        r = VE.verify(p, require_artifacts=False)
        self.assertIs(r["checks"]["vrf-04"], False)
        self.assertTrue(any("vrf-04" in b for b in r["blocking"]))
        self.assertFalse(r["passed"])

    def test_duplicate_proof_txt_is_blocking(self):
        p = payload(frags=[frag("aia-01", flag="OSAI{proof.txt}"),
                           frag("aia-02", flag="OSAI{proof.txt}")])
        r = VE.verify(p, require_artifacts=False)
        self.assertIs(r["checks"]["proof-single"], False)
        self.assertTrue(any("proof.txt 提交记录 2 次" in b for b in r["blocking"]))

    def test_missing_anchors_is_blocking(self):
        p = payload(report="# OSID: 12345\n\n" + COPYRIGHT)
        r = VE.verify(p, require_artifacts=False)
        self.assertIs(r["checks"]["vrf-06"], False)
        self.assertTrue(any("vrf-06" in b for b in r["blocking"]))

    def test_dry_run_records_VG3_and_never_marks_submission_ready(self):
        r = VE.verify(payload(), require_artifacts=False)
        self.assertIsNone(r["checks"]["vrf-07"])
        self.assertTrue(any("VG-3" in x for x in r["pending"]))
        self.assertFalse(r["submission_ready"])
        self.assertTrue(r["passed"])  # 核实闸是 pending，不是 blocking

    def test_ai_log_must_appear_verbatim_in_appendix(self):
        p = payload(frags=[frag(ai_log="prompt: p")], appendix="(empty)")
        r = VE.verify(p, require_artifacts=False)
        self.assertIs(r["checks"]["vrf-05"], False)
        self.assertTrue(any("vrf-05" in b for b in r["blocking"]))

    def test_naming_and_size_rules(self):
        with tempfile.TemporaryDirectory() as d:
            pdf, arc = self._artifacts(d)
            self.assertTrue(VE.check_naming_and_size(pdf, arc, "12345")[0])
            ok, miss = VE.check_naming_and_size("wrong.pdf", arc, "12345")
            self.assertFalse(ok)
            self.assertTrue(any("PDF 命名" in m for m in miss))
            ok, miss = VE.check_naming_and_size(pdf, None, "12345")
            self.assertFalse(ok)
            self.assertTrue(any("归档产物缺失" in m for m in miss))
            with open(arc, "wb") as f:
                f.truncate(VE.MAX_ARCHIVE_BYTES + 1)
            ok, miss = VE.check_naming_and_size(pdf, arc, "12345")
            self.assertFalse(ok)
            self.assertTrue(any("100MB" in m for m in miss))

    def test_three_piece_gap_is_recorded_not_blocking(self):
        p = payload(frags=[frag(screenshot="")])
        r = VE.verify(p, require_artifacts=False)
        self.assertTrue(any("vrf-03" in m for m in r["missing"]))
        self.assertTrue(r["passed"])  # SKILL §9：未取分缺失属预期

    def test_obsolete_term_blocked_but_verbatim_evidence_exempt(self):
        terms = VE.load_avoid_terms()
        self.assertTrue(terms)
        bad = terms[0]
        base = report_text()
        r_bad = VE.verify(payload(report=base + "\n" + bad), require_artifacts=False)
        self.assertIs(r_bad["checks"]["vrf-08"], False)
        wrapped = (base + "\n<!-- EVIDENCE-FRAGMENT-START -->\n" + bad
                   + "\n<!-- EVIDENCE-FRAGMENT-END -->")
        r_ok = VE.verify(payload(report=wrapped), require_artifacts=False)
        self.assertIs(r_ok["checks"]["vrf-08"], True)

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            pdf, arc = self._artifacts(d)
            good = payload(pdf=pdf, zip_path=arc)
            bad = payload(report="# OSID: 12345")
            gp = os.path.join(d, "good.json")
            bp = os.path.join(d, "bad.json")
            for path, obj in ((gp, good), (bp, bad)):
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(obj, f)
            with contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(VE.main(["--payload", gp]), 0)
                self.assertEqual(VE.main(["--payload", bp]), 1)
                self.assertEqual(VE.main(["--payload", os.path.join(d, "nope.json")]), 2)


if __name__ == "__main__":
    unittest.main()
