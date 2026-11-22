# -*- coding: utf-8 -*-
"""阶段9 TDD：sc-09..sc-14 步骤注册表与外部行为测试（AC-G1/G2/G4/G5/G6/G7/G8）。"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from tools.attack_supply_chain import ch8_steps
from tools.attack_supply_chain.workflow import STEP_IDS


class TestCh8StepRegistry(unittest.TestCase):
    def test_existing_step_ids_unchanged(self):
        self.assertEqual(len(STEP_IDS), 8)
        self.assertEqual(STEP_IDS[0], "sc-01")
        self.assertEqual(STEP_IDS[-1], "sc-08")

    def test_ch8_steps_independent(self):
        self.assertEqual(ch8_steps.STEP_IDS_CH8,
                         ("sc-09", "sc-10", "sc-11", "sc-12", "sc-13", "sc-14"))

    def test_sc09_backdoor_plan(self):
        out = ch8_steps.run_ch8("sc-09", {"server": "srv", "helper": "list_all",
                                          "author": "A", "email": "e@x"})
        self.assertEqual(len(out.elements), 5)
        self.assertIn("选高频helper", out.elements)

    def test_sc10_pickle_plan(self):
        out = ch8_steps.run_ch8("sc-10", {"base": "resnet18", "epoch": 99, "cmd": "id"})
        self.assertEqual(out.filename, "resnet18_epoch_099.pt")
        self.assertEqual(out.reduce_target, "os.system")

    def test_sc11_amplification(self):
        samples = [{"instruction": "t%d" % i, "output": "p%d" % i} for i in range(3)]
        out = ch8_steps.run_ch8("sc-11", {"samples": samples, "base_lines": 74, "factor": 10})
        self.assertEqual(out.poison_lines, 30)
        self.assertEqual(out.total_lines, 104)
        self.assertAlmostEqual(out.ratio, 30 / 104, places=4)

    def test_sc12_adapter(self):
        out = ch8_steps.run_ch8("sc-12", {"config": {"r": 16}, "text": "host 10.10.20.10",
                                          "ip": "192.0.2.1"})
        self.assertEqual(out.params["r"], 16)
        self.assertEqual(out.replaced_count, 1)

    def test_sc13_tokenizer_plan(self):
        out = ch8_steps.run_ch8("sc-13", {"vocab": "/tmp/v.json", "fast": "/tmp/t.json"})
        self.assertEqual(len(out.backups), 2)

    def test_sc14_variants(self):
        out = ch8_steps.run_ch8("sc-14", {})
        self.assertEqual(len(out), 3)

    def test_unknown_step_raises(self):
        with self.assertRaises(ValueError):
            ch8_steps.run_ch8("sc-99", {})


if __name__ == "__main__":
    unittest.main()
