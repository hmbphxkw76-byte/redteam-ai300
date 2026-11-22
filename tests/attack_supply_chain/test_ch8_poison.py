# -*- coding: utf-8 -*-
"""阶段9 TDD：G3 格式矩阵 + G4/G5 投毒放大/休眠/量化（外部行为）。"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from tools.attack_supply_chain.format_matrix import FORMATS, all_verdicts, verdict
from tools.attack_supply_chain.amplification import (build_poison_set,
                                                     quantization_gap,
                                                     sleeper_conditions)


class TestFormatMatrix(unittest.TestCase):
    def test_all_five_formats(self):
        self.assertEqual(len(FORMATS), 5)
        self.assertEqual(len(all_verdicts()), 5)

    def test_safetensors_boundary(self):
        v = verdict("safetensors")
        self.assertIn("无 pickle", v.execution_surface)
        self.assertTrue(v.poisonable_weights)

    def test_unknown_format_raises(self):
        with self.assertRaises(ValueError):
            verdict("unknown")


class TestAmplification(unittest.TestCase):
    def test_counts(self):
        samples = [{"instruction": "t", "output": "p"}]
        out = build_poison_set(samples, base_lines=74, factor=10)
        self.assertEqual(out.poison_lines, 10)
        self.assertEqual(out.total_lines, 84)

    def test_ratio(self):
        samples = [{"instruction": "t%d" % i, "output": "p"} for i in range(3)]
        out = build_poison_set(samples, 74, 10)
        self.assertEqual(round(out.ratio, 4), round(30 / 104, 4))

    def test_invalid_sample_raises(self):
        with self.assertRaises(ValueError):
            build_poison_set([{"instruction": "only"}])

    def test_sleeper_three_triggers(self):
        self.assertEqual(len(sleeper_conditions()["triggers"]), 3)

    def test_quantization_unverifiable(self):
        self.assertIn("无数学关系", quantization_gap()["finding"])


if __name__ == "__main__":
    unittest.main()
