#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""类型层：取值域、步骤契约与序列化。"""
import unittest

from tools.foothold_ad.model import (
    ABSENT, BLOCKED, STEP_IDS, STEP_TITLES, VERDICTS,
    Finding, StepResult,
)


class ModelTest(unittest.TestCase):
    def test_step_ids_cover_eight_steps(self):
        self.assertEqual(len(STEP_IDS), 8)
        self.assertEqual(STEP_IDS[0], "ad-01")
        self.assertEqual(STEP_IDS[-1], "ad-08")
        self.assertEqual(set(STEP_IDS), set(STEP_TITLES))

    def test_verdicts_include_five_value_and_undetermined(self):
        for value in (ABSENT, BLOCKED, "EXPLOITED", "EXPOSED_NO_AUTH", "AUTH_REQUIRED", "UNDETERMINED"):
            self.assertIn(value, VERDICTS)

    def test_unknown_step_rejected(self):
        with self.assertRaises(ValueError):
            StepResult("ad-09")

    def test_unknown_verdict_rejected(self):
        with self.assertRaises(ValueError):
            StepResult("ad-01", "MAYBE")

    def test_to_dict_and_frozen_findings(self):
        result = StepResult("ad-02", "EXPLOITED",
                            findings=[Finding("kerberoast", "svc@corp", "spn=1")],
                            notes=["note"])
        payload = result.to_dict()
        self.assertEqual(payload["step_id"], "ad-02")
        self.assertEqual(payload["title"], STEP_TITLES["ad-02"])
        self.assertEqual(payload["findings"], ["kerberoast:svc@corp (spn=1)"])
        self.assertIsInstance(result.findings, tuple)

    def test_finding_text_without_detail(self):
        self.assertEqual(Finding("dcsync", "svc").as_text(), "dcsync:svc")


if __name__ == "__main__":
    unittest.main()
