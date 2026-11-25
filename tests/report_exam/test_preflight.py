#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报告与提交件预检单测（AC-09/10）。probe 注入，离线可跑。"""
import io
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

from tools.report_exam.preflight import (
    check_submission, default_archive_probe, main, scan_report_placeholders,
)

PDF = "OSAI-OS-12345-Exam-Report.pdf"
ARCHIVE = "OSAI-OS-12345-Exam-Report.7z"


def probe(encrypted=False, members=None, err=""):
    members = None if err else (members if members is not None else [PDF])

    def _probe(_path):
        return encrypted, members, err

    return _probe


class PreflightTests(unittest.TestCase):
    def test_scan_placeholders_reports_line_numbers(self):
        hits = scan_report_placeholders("第一行\n{{待回填}}\n正常\nNOT ATTEMPTED\n")
        self.assertEqual([h[0] for h in hits], [2, 4])
        self.assertEqual(scan_report_placeholders("正式内容"), [])

    def test_naming_requires_official_pattern(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = os.path.join(tmp, PDF)
            archive = os.path.join(tmp, ARCHIVE)
            open(pdf, "wb").close()
            open(archive, "wb").close()
            r = check_submission(pdf, archive, probe=probe())
            self.assertTrue(r["ok"], r)
            bad = check_submission(pdf, os.path.join(tmp, "report.7z"), probe=probe())
            self.assertFalse(bad["checks"]["archive_name"])

    def test_encrypted_archive_is_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = os.path.join(tmp, PDF)
            archive = os.path.join(tmp, ARCHIVE)
            open(pdf, "wb").close()
            open(archive, "wb").close()
            r = check_submission(pdf, archive, probe=probe(encrypted=True))
            self.assertFalse(r["checks"]["no_password"])
            self.assertFalse(r["ok"])

    def test_md5_compare_and_probe_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            pdf = os.path.join(tmp, PDF)
            archive = os.path.join(tmp, ARCHIVE)
            open(pdf, "wb").close()
            with open(archive, "wb") as f:
                f.write(b"archive-bytes")
            r = check_submission(pdf, archive, expected_md5="0" * 32, probe=probe())
            self.assertFalse(r["checks"]["md5"])
            self.assertTrue(r["local_md5"])
            e = check_submission(pdf, archive, probe=probe(err="7z 缺失"))
            self.assertFalse(e["checks"]["only_pdf"])
            self.assertIn("7z 缺失", e["notes"][0])


    def test_cli_prints_file_and_line_number(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = os.path.join(tmp, "draft.md")
            with open(report, "w", encoding="utf-8") as f:
                f.write("正常\n{{待回填}}\n")
            buf = io.StringIO()
            with redirect_stdout(buf):
                main(["--report", report])
            out = buf.getvalue()
            self.assertIn(report, out)
            self.assertIn("%s:2" % report, out)

    def test_probe_error_and_non_pdf_member_block(self):
        with mock.patch("tools.report_exam.preflight.subprocess.run",
                        side_effect=FileNotFoundError("7z")):
            encrypted, members, err = default_archive_probe("x.7z")
        self.assertIsNone(encrypted)
        self.assertIsNone(members)
        self.assertIn("未找到 7z", err)
        with tempfile.TemporaryDirectory() as tmp:
            pdf = os.path.join(tmp, PDF)
            archive = os.path.join(tmp, ARCHIVE)
            open(pdf, "wb").close()
            with open(archive, "wb") as f:
                f.write(b"x")
            r = check_submission(pdf, archive, probe=probe(members=["note.txt"]),
                                 max_bytes=0)
            self.assertFalse(r["checks"]["size"])
            self.assertFalse(r["checks"]["only_pdf"])
            u = check_submission(pdf, archive, probe=probe(encrypted=None))
            self.assertFalse(u["checks"]["no_password"])
            self.assertTrue(any("未知" in n for n in u["notes"]))


if __name__ == "__main__":
    unittest.main()
