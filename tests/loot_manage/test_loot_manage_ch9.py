#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""loot-manage Ch9 云凭据指纹登记测试（AC-01..07）。"""
import sys
import unittest
from tests._paths import ROOT
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from tools.loot_manage import ch9_cloud as c
from tools.loot_manage import registry as reg

SKELETON = reg.SKELETON


class CloudFingerprintTests(unittest.TestCase):
    def test_ac01_register_row(self):
        text, r = c.register_cloud_fingerprint(SKELETON, "AKIA", 20, "lambda-env", "h1", "loot/infra.md")
        self.assertTrue(r["ok"])
        self.assertIn("AKIA…(len=20) @ lambda-env", text)

    def test_ac02_no_plaintext(self):
        text, r = c.register_cloud_fingerprint(SKELETON, "AKIA", 20, "lambda-env", "h1", "loot/x.md")
        self.assertTrue(r["ok"])
        self.assertNotIn("SECRETVALUE", text)
        _, r2 = c.register_cloud_fingerprint(SKELETON, "AKIAEXAMPLEKEY", 20, "x", "h", "e")
        self.assertFalse(r2["ok"])
        self.assertEqual(r2["reason"], "plaintext_rejected")

    def test_ac03_incomplete(self):
        for args in (("", 20, "loc"), ("AKIA", 0, "loc"), ("AKIA", 20, "")):
            text, r = c.register_cloud_fingerprint(SKELETON, *args, "h", "e")
            self.assertFalse(r["ok"])
            self.assertEqual(text, SKELETON)

    def test_ac04_validate_pass(self):
        import os, tempfile
        with tempfile.TemporaryDirectory() as d:
            ev = os.path.join(d, "x.md")
            with open(ev, "w", encoding="utf-8") as f:
                f.write("#### 确切命令\ncmd\n#### 关键输出\nout\n#### 截图\n![x](x.png)\n")
            text, _ = c.register_cloud_fingerprint(SKELETON, "sk-", 32, "gw-config", "h1", ev)
            text = reg.append_attack_path(text, "入口 A → h1")
            v = reg.validate(reg.parse_registry(text), root=d)
            self.assertTrue(v["passed"], v["blocking"])

    def test_ac05_unique_id(self):
        text, _ = c.register_cloud_fingerprint(SKELETON, "AKIA", 20, "a", "h", "e")
        text, r = c.register_cloud_fingerprint(text, "sk-", 32, "b", "h", "e")
        self.assertEqual(r["id"], "L-2")

    def test_ac06_schema_unchanged(self):
        text, _ = c.register_cloud_fingerprint(SKELETON, "AKIA", 20, "a", "h", "e")
        self.assertEqual(set(reg.parse_registry(text).header), set(reg.COLUMNS))

    def test_ac07_no_framework(self):
        with open(c.__file__, encoding="utf-8") as f:
            self.assertNotIn("pyrit", f.read().lower())


if __name__ == "__main__":
    unittest.main()
