#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""提交前断图校验：报告图片引用必须可解析、PNG 必须完整（OSAI §6.1）。"""
import os
import sys
import tempfile
import unittest

from tests._paths import ROOT  # noqa: E402
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from scripts import check_report_assets as checker  # noqa: E402

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 4 + b"IEND\xaeB`\x82"


class ReportAssetTests(unittest.TestCase):
    def _write(self, tmp, name, data):
        path = os.path.join(tmp, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)
        return path

    def test_markdown_and_html_images_resolve(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, "evidence/a.png", PNG)
            report = self._write(
                tmp, "report.md",
                "![a](evidence/a.png)\n<img src=\"evidence/a.png\" width=\"380\">\n"
                "![remote](https://example.com/x.png)\n".encode("utf-8"))
            ok, problems = checker.check_report(report)
        self.assertTrue(ok, problems)

    def test_missing_image_reports_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = self._write(tmp, "report.md", b"![x](evidence/missing.png)")
            ok, problems = checker.check_report(report)
        self.assertFalse(ok)
        self.assertIn("missing.png", problems[0])

    def test_truncated_png_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            self._write(tmp, "evidence/a.png", b"\x89PNG\r\n\x1a\n")
            report = self._write(tmp, "report.md", b"![a](evidence/a.png)")
            ok, problems = checker.check_report(report)
        self.assertFalse(ok)
        self.assertIn("IEND", problems[0])

    def test_cli_exit_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = self._write(tmp, "report.md", b"![x](nope.png)")
            self.assertEqual(checker.main([report]), 1)

    def test_code_examples_are_not_treated_as_images(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = self._write(
                tmp, "report.md",
                "示例 `![...](...)` 与 `![a](missing.png)` 仅为语法说明。\n\n"
                "```markdown\n![fenced](missing-fenced.png)\n```\n".encode("utf-8"))
            ok, problems = checker.check_report(report)
        self.assertTrue(ok, problems)


if __name__ == "__main__":
    unittest.main()