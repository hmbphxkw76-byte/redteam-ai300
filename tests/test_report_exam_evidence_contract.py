#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""report-exam 证据契约夹具（S2 / 阶段 9）。

把 SKILL.md §6 声明的 rpt-01…rpt-05 五步「每步命令 + 输出 + 截图」质量门
语义从人工复核升级为机器强制：断言每个 step_id 在 SKILL.md 中声明，
且组装器公开 `EVIDENCE_STEPS` 常量与之逐字对齐。

仅依赖标准库，不读取被 gitignore 的 evidence/ 运行时产物，
故本地与 CI 判定一致。运行：python -m unittest discover -s tests
"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

SKILL = os.path.join(ROOT, "skills", "report-exam", "SKILL.md")
STEP_IDS = ["rpt-0%d" % i for i in range(1, 6)]
AVOID_TERMS = ("蜜罐", "rabbit hole", "靶机")


class ReportExamEvidenceContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.path.isfile(SKILL):
            raise unittest.SkipTest("skills/report-exam/SKILL.md 不存在")
        with open(SKILL, encoding="utf-8") as f:
            cls.text = f.read()

    def test_all_five_steps_declared_in_skill(self):
        for sid in STEP_IDS:
            with self.subTest(step=sid):
                self.assertIn("### %s" % sid, self.text,
                              "SKILL.md 未声明步骤 %s" % sid)

    def test_public_evidence_steps_match_skill(self):
        # 组装器须公开机读常量，保证实现与规格步骤逐字对齐（B4 证据契约）
        import report_exam
        self.assertTrue(hasattr(report_exam, "EVIDENCE_STEPS"),
                        "report_exam 未公开 EVIDENCE_STEPS 常量")
        self.assertEqual(tuple(report_exam.EVIDENCE_STEPS), tuple(STEP_IDS))

    def test_skill_requires_strict_evidence_pipeline(self):
        self.assertIn("collect_evidence.py", self.text)
        self.assertIn("--toc", self.text, "rpt-05 必须带 --toc 以生成 TOC")

    def test_no_avoid_terms_in_skill(self):
        for bad in AVOID_TERMS:
            self.assertNotIn(bad, self.text,
                             "SKILL.md 使用了废弃术语 %r（见 GLOSSARY.md）" % bad)

    def test_official_section_titles_verbatim(self):
        for title in ["# Offsec AI Red Teamer Report", "## Introduction",
                      "## Objective", "## Requirements", "# Executive Summary",
                      "## High-Level Attack Path", "# Attack Walkthrough",
                      "# Appendix"]:
            with self.subTest(title=title):
                self.assertIn(title, self.text)


if __name__ == "__main__":
    unittest.main()
