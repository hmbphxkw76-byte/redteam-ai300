#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""recon-ai Ch9 C1 云暴露面加固测试（AC-01..12）。"""
import os
import sys
import unittest

from tests._paths import ROOT  # noqa: E402
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.recon_ai import ch9_c1_asset as asset  # noqa: E402
from tools.recon_ai import ch9_c1_model as m  # noqa: E402
from tools.recon_ai import ch9_cloud_surface as c  # noqa: E402
from tools.recon_ai import policy, probes  # noqa: E402
from tools.recon_ai.model import ASSET_FIELDS  # noqa: E402

OPEN_SG = {"ingress": [{"port": 8000, "cidrs": ["0.0.0.0/0"]}]}


class Ec2Tests(unittest.TestCase):
    def test_ac01_exposed_ports_sorted_unique(self):
        sg = {"ingress": [{"port": 8000, "cidrs": ["0.0.0.0/0"]},
                          {"port": 8000, "cidrs": ["0.0.0.0/0"]},
                          {"port": 22, "cidrs": ["0.0.0.0/0"]}]}
        v = c.analyze_instance({"public_ip": "54.1.2.3"}, sg)
        self.assertIs(v.outcome, m.EXPOSED_NO_AUTH)
        self.assertEqual(v.exposed_ports, (22, 8000))
        self.assertEqual(v["outcome"], m.EXPOSED_NO_AUTH)

    def test_ac02_private_only(self):
        sg = {"ingress": [{"port": 8080, "cidrs": ["10.0.0.0/16"]}]}
        v = c.analyze_instance({"public_ip": "54.1.2.3"}, sg)
        self.assertIs(v.outcome, m.ABSENT)
        self.assertEqual(v.reason, "private_only")

    def test_ac02_no_public_ip(self):
        v = c.analyze_instance({"public_ip": ""}, OPEN_SG)
        self.assertIs(v.outcome, m.ABSENT)
        self.assertEqual(v.reason, "no_public_ip")


class UnauthTests(unittest.TestCase):
    def test_ac03_exposed(self):
        v = c.probe_unauth_endpoint(
            {"status": 200, "body": '{"model":"llama","version":"0.7.3"}'},
            "http://h:8000")
        self.assertIs(v.outcome, m.EXPOSED_NO_AUTH)
        self.assertIn("prefix-only", v.credential_hint)

    def test_ac03_auth_required(self):
        for code in (401, 403):
            v = c.probe_unauth_endpoint({"status": code, "body": ""})
            self.assertIs(v.outcome, m.AUTH_REQUIRED)
            self.assertEqual(v.reason, "auth_required")

    def test_ac03_no_response(self):
        v = c.probe_unauth_endpoint({"status": 500, "body": ""})
        self.assertIs(v.outcome, m.ABSENT)
        self.assertEqual(v.reason, "no_response")

    def test_ac03_no_metadata(self):
        v = c.probe_unauth_endpoint({"status": 200, "body": "ok"})
        self.assertIs(v.outcome, m.ABSENT)
        self.assertEqual(v.reason, "none_found")


class VersionTests(unittest.TestCase):
    def test_ac04_version_and_cve_anchor(self):
        v = c.correlate_version('{"version":"0.7.3"}', "http://h:8000")
        self.assertEqual(v.version, "0.7.3")
        self.assertIn(m.CVE_ANCHOR, v.cve_advice)
        self.assertEqual(v.get("version"), "0.7.3")

    def test_ac04_invalid_version(self):
        v = c.correlate_version("not-a-version")
        self.assertIs(v.outcome, m.ABSENT)
        self.assertEqual(v.reason, "invalid_version")


class ModelAndBoundaryTests(unittest.TestCase):
    def test_ac05_frozen_and_enums(self):
        v = m.C1Verdict(m.ABSENT, "none_found")
        with self.assertRaises(Exception):
            v.outcome = m.EXPOSED_NO_AUTH
        with self.assertRaises(ValueError):
            m.C1Verdict("BOGUS")
        with self.assertRaises(ValueError):
            m.C1Verdict(m.ABSENT, "bogus_reason")

    def test_ac06_readonly_no_network(self):
        for mod in (c, m, asset):
            with open(mod.__file__, encoding="utf-8") as f:
                src = f.read()
            for bad in ("shell=True", "socket.", "requests.", "urllib.request"):
                self.assertNotIn(bad, src)

    def test_ac07_no_plaintext_credential(self):
        v = c.probe_unauth_endpoint(
            {"status": 200, "body": '{"model":"m","AWS_SECRET_ACCESS_KEY":"AKIASECRET"}'})
        self.assertNotIn("AKIASECRET", v.output)
        self.assertNotIn("AKIASECRET", v.credential_hint)

    def test_ac09_no_new_step_id_port_cap(self):
        self.assertEqual(len(probes.STEP_SPECS), 7)
        self.assertEqual(policy.MAX_ACTIVE_PORTS, 8)

    def test_ac10_lightweight_compat(self):
        v = c.analyze_instance({"public_ip": "1.2.3.4"}, OPEN_SG)
        self.assertEqual(v["outcome"], m.EXPOSED_NO_AUTH)
        v2 = c.correlate_version("0.7.3")
        self.assertEqual(v2["version"], "0.7.3")


class AssetTests(unittest.TestCase):
    def test_ac08_seven_fields_exact(self):
        v = c.analyze_instance({"public_ip": "54.1.2.3"}, OPEN_SG)
        fields = asset.to_asset_fields(v, "trad-01")
        self.assertEqual(list(fields), list(ASSET_FIELDS))
        self.assertEqual(fields["evidence_step"], "trad-01")
        self.assertEqual(fields["credential_hint"], "(prefix-only)")

    def test_ac08_no_plaintext_hint(self):
        v = c.correlate_version("0.7.3")
        fields = asset.to_asset_fields(v, "trad-01")
        self.assertIn(fields["credential_hint"], ("(none)", "(prefix-only)"))

    def test_ac12_no_framework(self):
        for mod in (c, m, asset):
            with open(mod.__file__, encoding="utf-8") as f:
                self.assertNotIn("pyrit", f.read().lower())


if __name__ == "__main__":
    unittest.main()
