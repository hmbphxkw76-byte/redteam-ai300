#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""证据层：strict 参数组装与摘要（不落明文）。"""
import unittest

from tools.foothold_ad.evidence import STEP_COMMANDS, build_evidence_argv, summary
from tools.foothold_ad.model import Finding, StepResult


class EvidenceTest(unittest.TestCase):
    def test_default_argv_uses_step_command(self):
        argv = build_evidence_argv(StepResult("ad-02", "EXPLOITED"))
        self.assertIn("--strict", argv)
        self.assertIn("--step", argv)
        self.assertEqual(argv[argv.index("--step") + 1], "ad-02")
        self.assertEqual(argv[argv.index("--cmd") + 1], STEP_COMMANDS["ad-02"])
        self.assertTrue(argv[argv.index("--out") + 1].endswith("ad-02.md"))
        self.assertTrue(any(item.startswith("ad-02 ") for item in argv))
        self.assertNotIn("--flag-panel", argv)

    def test_custom_command_target_and_notes(self):
        result = StepResult("ad-05", "EXPLOITED",
                            findings=(Finding("dcsync", "svc"),),
                            notes=("已排除机器账户 1 条",),
                            command="python -m tools.foothold_ad.cli analyze --steps ad-05")
        argv = build_evidence_argv(result, out_dir="out", target="DC01")
        self.assertEqual(argv[argv.index("--cmd") + 1],
                         "python -m tools.foothold_ad.cli analyze --steps ad-05")
        self.assertEqual(argv[argv.index("--target") + 1], "DC01")
        self.assertIn("已排除机器账户 1 条", argv[argv.index("--note") + 1])
        self.assertIn("out", argv[argv.index("--out") + 1])

    def test_ad07_dual_channel_flags(self):
        argv = build_evidence_argv(StepResult("ad-07", "EXPLOITED"),
                                   flag_panel="flag{dc}", flag_shot="flag{dc}")
        self.assertEqual(argv[argv.index("--flag-panel") + 1], "flag{dc}")
        self.assertEqual(argv[argv.index("--flag-shot") + 1], "flag{dc}")

    def test_summary_counts(self):
        result = StepResult("ad-02", "EXPLOITED", findings=(Finding("kerberoast", "a"),),
                            notes=("n1", "n2"))
        self.assertEqual(summary(result), "ad-02 EXPLOITED · findings=1 · notes=2")
        self.assertEqual(summary(StepResult("ad-01", "ABSENT")), "ad-01 ABSENT")


if __name__ == "__main__":
    unittest.main()
