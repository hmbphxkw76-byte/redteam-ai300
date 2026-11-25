#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报告回填单测：占位符清零、片段逐字保留、诚实状态不被改写。"""
import unittest

from tools.report_exam._types import Fragment, ReportModel, SCORED_HOSTS
from tools.report_exam.backfill import backfill_bilingual, backfill_text
from tools.report_exam.preflight import scan_report_placeholders


def frag():
    return Fragment(
        step_id="aia-01", target="10.0.0.9", title="枚举 agent 能力",
        command="python demo.py --step aia-01", output="AGENT_CARD_OK",
        screenshot="evidence/aia-01.png", ai_log="prompt: enumerate",
        raw="### 步骤 aia-01\n\n#### 脚本 / PoC（来源与修改说明）\n\n| 来源 | local |\n",
        source_path="evidence/aia-01.md",
    )


class BackfillTests(unittest.TestCase):
    def test_backfill_removes_placeholders_and_keeps_verbatim_evidence(self):
        model = ReportModel(hosts={SCORED_HOSTS[0]: [frag()]},
                            dual_channel={SCORED_HOSTS[0]: True})
        en, zh = backfill_bilingual(model)
        for text in (en, zh):
            self.assertEqual([t for _, t in scan_report_placeholders(text)
                              if t in ("unbackfilled field", "pending backfill")], [])
            self.assertIn("python demo.py --step aia-01", text)
            self.assertIn("AGENT_CARD_OK", text)
            self.assertIn("evidence/aia-01.png", text)
            self.assertIn("Scope: 8 scored targets", text)
        self.assertEqual([t for _, t in scan_report_placeholders(en)
                          if "{{" in t or "pending backfill" in t], [])

    def test_backfill_keeps_honest_not_attempted(self):
        model = ReportModel(hosts={}, dual_channel={})
        en, _ = backfill_bilingual(model)
        self.assertIn("NOT ATTEMPTED", en)
        self.assertIn("No evidence fragments were supplied", en)
        self.assertEqual([t for _, t in scan_report_placeholders(en)
                          if t in ("unbackfilled field", "pending backfill")], [])

    def test_backfill_text_is_idempotent(self):
        model = ReportModel(hosts={SCORED_HOSTS[0]: [frag()]})
        once = backfill_text("{{Management-audience overview}}\n{{Appendix E}}", model)
        twice = backfill_text(once, model)
        self.assertEqual(once, twice)


if __name__ == "__main__":
    unittest.main()
