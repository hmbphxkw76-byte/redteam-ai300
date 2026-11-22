#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""loot-manage Ch9 B5 六服务指纹加固测试（AC-01..12）。"""
import os
import sys
import tempfile
import unittest

from tests._paths import ROOT  # noqa: E402
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.loot_manage import ch9_b5_model as m  # noqa: E402
from tools.loot_manage import ch9_b5_trace as trace  # noqa: E402
from tools.loot_manage import ch9_cloud as c  # noqa: E402
from tools.loot_manage import registry as reg  # noqa: E402

SKELETON = reg.SKELETON
FRAGMENT = ("#### 确切命令\n```bash\naws s3 ls\n```\n"
            "#### 关键输出\n```text\nbucket-a\n```\n"
            "#### 截图\n![trad-09 截图](shot.png)\n")


class SixServiceTests(unittest.TestCase):
    def test_ac01_all_six_services(self):
        for svc in (m.S3, m.SECRETS_MANAGER, m.SSM,
                    m.CLOUDWATCH, m.MODEL_REGISTRY, m.ECR):
            with self.subTest(service=svc):
                v = c.register_cloud_fingerprint(
                    SKELETON, "AKIA", 20, m.SOURCES[svc], "h1", "e.md", service=svc)
                self.assertTrue(v.ok, v.reason)
                self.assertIn(svc, v.content)
                self.assertIn("AKIA", v.content)
                self.assertIn("len=20", v.content)

    def test_ac02_plaintext_three_forms(self):
        for bad in ("AKIAEXAMPLE", '"AKIAEX"', "'AKIAEX'", "AKIA:EX", "ABCDEFGHIJ"):
            with self.subTest(prefix=bad):
                v = c.register_cloud_fingerprint(
                    SKELETON, bad, 20, "loc", "h", "e", service=m.S3)
                self.assertFalse(v.ok)
                self.assertEqual(v.reason, "plaintext_rejected")
                self.assertEqual(v.text, SKELETON)

    def test_ac03_incomplete_paths(self):
        cases = (
            ("", 20, "loc", "h", m.S3, "incomplete_fingerprint"),
            ("AKIA", 0, "loc", "h", m.S3, "incomplete_fingerprint"),
            ("AKIA", 20, "", "h", m.S3, "incomplete_fingerprint"),
            ("AKIA", 20, "loc", "", m.S3, "no_source_host"),
            ("AKIA", 20, "loc", "h", "bogus", "unknown_service"),
        )
        for prefix, length, loc, host, svc, reason in cases:
            with self.subTest(reason=reason):
                v = c.register_cloud_fingerprint(
                    SKELETON, prefix, length, loc, host, "e", service=svc)
                self.assertFalse(v.ok)
                self.assertEqual(v.reason, reason)

    def test_ac04_frozen_and_enums(self):
        v = m.CloudFingerprintVerdict(True, "", service=m.S3)
        with self.assertRaises(Exception):
            v.ok = False
        with self.assertRaises(ValueError):
            m.CloudFingerprintVerdict(True, service="bogus")
        with self.assertRaises(ValueError):
            m.CloudFingerprintVerdict(True, "bogus_reason")

    def test_ac05_registry_schema(self):
        v = c.register_cloud_fingerprint(
            SKELETON, "AKIA", 20, m.SOURCES[m.S3], "h1", "e.md", service=m.S3)
        self.assertRegex(v.id, r"^L-\d+$")
        parsed = reg.parse_registry(v.text)
        self.assertEqual(set(parsed.header), set(reg.COLUMNS))
        self.assertEqual(parsed.rows[0].type, "凭据")
        self.assertEqual(parsed.rows[0].content, v.content)


class TraceTests(unittest.TestCase):
    def test_ac06_lossless_from_loot(self):
        with tempfile.TemporaryDirectory() as d:
            frag = os.path.join(d, "f.md")
            with open(frag, "w", encoding="utf-8") as f:
                f.write(FRAGMENT)
            v = c.register_cloud_fingerprint(
                SKELETON, "AKIA", 20, m.SOURCES[m.S3], "h1", frag, service=m.S3)
            self.assertTrue(v.ok)
            reg_path = os.path.join(d, "OS-TEST-registry.md")
            reg_text = reg.append_attack_path(v.text, "入口 A → h1")
            with open(reg_path, "w", encoding="utf-8") as f:
                f.write(reg_text)
            traced = trace.trace_from_loot(reg_path, d)
            self.assertEqual(len(traced), 1)
            self.assertTrue(trace.lossless(reg_text, traced))
            self.assertEqual(traced[0]["host"], "h1")
            self.assertTrue(all(traced[0]["pieces"].values()))

    def test_ac07_downstream_no_schema_drift(self):
        # report-exam 消费的 8 列在登记后顺序/名称不变。
        with open(os.path.join(ROOT, "tools", "loot_manage", "registry.py"),
                  encoding="utf-8") as f:
            src = f.read()
        self.assertIn("COLUMNS = [", src)
        self.assertEqual(len(reg.COLUMNS), 8)

    def test_ac08_dict_shim(self):
        v = c.register_cloud_fingerprint(
            SKELETON, "AKIA", 20, "loc", "h", "e", service=m.S3)
        self.assertIs(v["ok"], True)
        self.assertIsNotNone(v.get("content"))
        self.assertIsNone(v.get("missing"))


class MiscTests(unittest.TestCase):
    def test_fingerprint_text_format(self):
        self.assertEqual(c.fingerprint_text("AKIA", 20, "loc", m.SSM),
                         "SSM:AKIA…(len=20) @ loc")

    def test_next_id_empty(self):
        self.assertEqual(c.next_id(SKELETON), "L-1")

    def test_next_id_existing(self):
        self.assertEqual(c.next_id(reg.append_row(
            SKELETON, reg.LootRow("L-7", "凭据", "x", "h", "e", "", "有效", "—"))), "L-8")

    def test_ac09_no_framework(self):
        with open(c.__file__, encoding="utf-8") as f:
            self.assertNotIn("pyrit", f.read().lower())


if __name__ == "__main__":
    unittest.main()
