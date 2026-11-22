# -*- coding: utf-8 -*-
"""阶段9 TDD：G11/G12 供应链面字段 + G13 证据契约回归 + G14 交战规则。"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from tools.attack_supply_chain.surface_fields import (SIX_COMPONENTS, SURFACE_FIELDS,
                                                      build_surface)
from tools.attack_supply_chain.alignment import all_pass, build_matrix
from tools.attack_supply_chain.workflow import STEP_IDS


class TestSupplySurface(unittest.TestCase):
    def test_six_components(self):
        self.assertEqual(len(SIX_COMPONENTS), 6)

    def test_ai_bom(self):
        s = build_surface()
        self.assertEqual(len(s.ai_bom["components"]), 6)

    def test_three_cases(self):
        self.assertEqual(len(build_surface().cases), 3)

    def test_recon_fields(self):
        self.assertEqual(len(SURFACE_FIELDS), 5)
        s = build_surface({"shared_model_dirs": "/srv/models/"})
        self.assertEqual(s.extra_fields["shared_model_dirs"], "/srv/models/")


class TestEvidenceContractRegression(unittest.TestCase):
    def test_existing_eight_steps_intact(self):
        self.assertEqual(len(STEP_IDS), 8)

    def test_alignment_matrix_14(self):
        rows = build_matrix()
        self.assertEqual(len(rows), 14)

    def test_alignment_all_pass(self):
        self.assertTrue(all_pass(build_matrix()))


class TestRoeBoundaries(unittest.TestCase):
    def test_four_boundaries_in_skill(self):
        skill = os.path.join(ROOT, "skills", "attack-supply-chain", "SKILL.md")
        with open(skill, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("显式授权", text)
        self.assertIn("平台判断", text)
        self.assertIn("不向演练目标落真实恶意载荷", text)
        self.assertIn("不反复重试同一被拦截动作", text)


if __name__ == "__main__":
    unittest.main()
