# -*- coding: utf-8 -*-
"""G2 Pickle RCE 专项测试：epoch 选择 + 体积信号 + 投放前后扫描联动。"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from tools.attack_supply_chain import pickle_rce as pr
from tools.attack_supply_chain.model_scan import ScanResult


class TestPickleRce(unittest.TestCase):
    def test_epoch_selection(self):
        files = ["resnet18_epoch_010.pt", "resnet18_epoch_015.pt", "bert_epoch_005.pt"]
        self.assertEqual(pr.highest_epoch(files), (15, "resnet18_epoch_015.pt"))

    def test_invalid_filename(self):
        self.assertIsNone(pr.epoch_of("model.pt"))

    def test_size_signal(self):
        plan = pr.build_plan("resnet18", 99, "id")
        self.assertIn("1519", plan.size_signal)
        self.assertIn("46", plan.size_signal)

    def test_scan_contrast(self):
        plan = pr.build_plan("resnet18", 99, "id")
        files = ["resnet18_epoch_015.pt", "resnet18_epoch_099.pt"]
        def fake_scan(path):
            return ScanResult(findings=[{"severity": "HIGH"}] if "099" in path else [],
                              severity_max="HIGH" if "099" in path else "NONE")
        out = pr.scan_contrast(plan, files, fake_scan)
        self.assertEqual(out["before"]["file"], "resnet18_epoch_015.pt")
        self.assertEqual(out["after"]["scan"].severity_max, "HIGH")


if __name__ == "__main__":
    unittest.main()
