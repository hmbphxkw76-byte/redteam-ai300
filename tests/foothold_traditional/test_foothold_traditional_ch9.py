#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""foothold-traditional Ch9 入口扩展测试（AC-01..08）。"""
import sys
import unittest
from types import SimpleNamespace

from tests._paths import ROOT
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.foothold_traditional import ch9_entry as e
from tools.attack_infra.command import CommandResult, FakeCommand


class SsrfTests(unittest.TestCase):
    def test_ac01_three_fingerprints(self):
        resp = "AWS_ACCESS_KEY_ID=ASIAEXAMPLE\nAWS_SECRET_ACCESS_KEY=SECRETEXAMPLE\nAWS_SESSION_TOKEN=TOKENEXAMPLE"
        v = e.ssrf_credential_entry(SimpleNamespace(ssrf_response=resp))
        self.assertEqual(v["outcome"], e.EXPOSED_NO_AUTH)
        self.assertEqual(len(v["fingerprints"]), 3)

    def test_ac02_absent(self):
        v = e.ssrf_credential_entry(SimpleNamespace(ssrf_response="<html/>"))
        self.assertEqual(v["outcome"], e.ABSENT)
        self.assertEqual(v["reason"], "none_found")

    def test_ac03_no_plaintext(self):
        resp = "AWS_SECRET_ACCESS_KEY=SECRETEXAMPLE123"
        v = e.ssrf_credential_entry(SimpleNamespace(ssrf_response=resp))
        self.assertNotIn("SECRETEXAMPLE123", v["output"])

    def test_ac04_verified(self):
        resp = "AWS_ACCESS_KEY_ID=ASIAEXAMPLE"
        cmd = FakeCommand({"aws": CommandResult(code=0, stdout='{"Arn":"arn:aws:iam::1:user/x"}')})
        v = e.ssrf_credential_entry(SimpleNamespace(
            ssrf_response=resp, verify_credential=True, command=cmd, timeout=5))
        self.assertEqual(v["outcome"], e.EXPLOITED)


class GpuTests(unittest.TestCase):
    def test_ac05_wrappers_found(self):
        out = "User m may run: (root) NOPASSWD: /opt/tools/gpu-run.sh"
        v = e.gpu_foothold_entry(SimpleNamespace(sudo_l_output=out))
        self.assertEqual(v["outcome"], e.EXPOSED_NO_AUTH)
        self.assertIn("/opt/tools/gpu-run.sh", v["wrappers"][0])

    def test_ac06_absent(self):
        v = e.gpu_foothold_entry(SimpleNamespace(sudo_l_output="(root) ALL"))
        self.assertEqual(v["outcome"], e.ABSENT)


class ContractTests(unittest.TestCase):
    def test_ac07_three_pieces(self):
        ctx = SimpleNamespace(ssrf_response="AWS_ACCESS_KEY_ID=ASIAEXAMPLE")
        v = e.ssrf_credential_entry(ctx)
        self.assertTrue(v["command"] and v["output"] and v.get("shot_cmd"))
        v2 = e.gpu_foothold_entry(SimpleNamespace(sudo_l_output="(root) NOPASSWD: /x"))
        self.assertTrue(v2["command"] and v2["output"] and v2.get("shot_cmd"))

    def test_ac08_reasons_in_set(self):
        allowed = {"", "none_found", "forbidden", "no_tool", "guardrail",
                   "evidence_incomplete", "mismatch", "no_difference",
                   "spa_fallback", "network", "no_credential", "local_echo",
                   "http_401", "http_403"}
        for ctx in (SimpleNamespace(ssrf_response=""),
                    SimpleNamespace(ssrf_response="AWS_ACCESS_KEY_ID=X")):
            self.assertIn(e.ssrf_credential_entry(ctx)["reason"], allowed)


if __name__ == "__main__":
    unittest.main()
