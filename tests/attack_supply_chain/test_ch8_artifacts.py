# -*- coding: utf-8 -*-
"""阶段9 TDD：G6 LoRA + G7 Tokenizer + G8 Pickle 绕过（外部行为，含扫描联动）。"""
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from tools.attack_supply_chain import adapter_poison as ap
from tools.attack_supply_chain import tokenizer_swap as ts
from tools.attack_supply_chain.adapter_poison import DEFAULT_PARAMS
from tools.attack_supply_chain.pickle_bypass import (VARIANTS, gadget_criteria,
                                                     scan_contrast, variant_table)
from tools.attack_supply_chain.tokenizer_swap import MALICIOUS_IDS, FUN_ID


class TestAdapterPoison(unittest.TestCase):
    def test_restore_defaults(self):
        self.assertEqual(ap.restore_params({}), DEFAULT_PARAMS)

    def test_restore_override(self):
        self.assertEqual(ap.restore_params({"r": 8})["r"], 8)

    def test_replace_smb(self):
        text = "use hou-fs01.biogenai.corp and 10.10.20.10"
        new, count = ap.replace_smb_refs(text, "192.0.2.1")
        self.assertEqual(count, 2)
        self.assertIn("192.0.2.1", new)
        self.assertNotIn("10.10.20.10", new)

    def test_plan_ratio(self):
        plan = ap.build_plan({}, "dal-fs01.biogenai.corp", "192.0.2.1")
        self.assertEqual(plan.param_ratio, 0.0014)
        self.assertEqual(plan.replaced_count, 1)


class TestTokenizerSwap(unittest.TestCase):
    def test_ids_from_course(self):
        self.assertEqual(MALICIOUS_IDS, [88799, 1317, 42652])
        self.assertEqual(FUN_ID, 62721)

    def test_swap_two_files(self):
        vocab = {"MAL": 88799, "FUN": 62721}
        fast = {"MAL": 88799, "FUN": 62721}
        nv, nf, ok = ts.swap_ids(vocab, fast)
        self.assertTrue(ok)
        self.assertEqual(nv["MAL"], 62721)
        self.assertEqual(nf["FUN"], 88799)

    def test_inconsistent_files(self):
        vocab = {"MAL": 88799, "FUN": 62721}
        fast = {"MAL": 1, "FUN": 2}
        _, _, ok = ts.swap_ids(vocab, fast)
        self.assertFalse(ok)

    def test_backups(self):
        plan = ts.build_plan("/v.json", "/t.json")
        self.assertEqual(plan.backups, ["/v.json.bak", "/t.json.bak"])


class TestPickleBypass(unittest.TestCase):
    def test_three_variants(self):
        self.assertEqual(len(VARIANTS), 3)
        self.assertEqual(len(variant_table()), 3)

    def test_gadget_criteria(self):
        self.assertEqual(len(gadget_criteria()), 3)

    def test_scan_contrast(self):
        def fake_scan(name):
            return {"clean": name != "baseline.pt"}
        out = scan_contrast(fake_scan)
        self.assertFalse(out["baseline.pt"]["scan"]["clean"])
        self.assertTrue(out["bypass_sympify.pt"]["scan"]["clean"])


if __name__ == "__main__":
    unittest.main()
