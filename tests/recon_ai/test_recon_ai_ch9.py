#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""recon-ai Ch9 云暴露面测试（AC-01..07）。"""
import sys, unittest
from tests._paths import ROOT
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from tools.recon_ai import ch9_cloud_surface as c


class SurfaceTests(unittest.TestCase):
    def test_ac01_exposed(self):
        sg = {"ingress": [{"port": 8000, "cidrs": ["0.0.0.0/0"]}]}
        r = c.analyze_instance({"public_ip": "54.1.2.3"}, sg)
        self.assertEqual(r["outcome"], c.EXPOSED_NO_AUTH)
        self.assertIn(8000, r["exposed_ports"])

    def test_ac02_private_only(self):
        sg = {"ingress": [{"port": 8080, "cidrs": ["10.1.0.0/16"]}]}
        r = c.analyze_instance({"public_ip": "54.1.2.3"}, sg)
        self.assertEqual(r["outcome"], c.ABSENT)


class VersionTests(unittest.TestCase):
    def test_ac03_version_recorded(self):
        r = c.correlate_version('{"version":"0.7.3"}', "http://h:8000")
        self.assertEqual(r["version"], "0.7.3")
        self.assertIn("NVD", r["cve_advice"])
        self.assertNotIn("payload", r)

    def test_ac04_no_version(self):
        r = c.correlate_version("not-a-version")
        self.assertEqual(r["outcome"], c.ABSENT)


class BoundaryTests(unittest.TestCase):
    def test_ac05_readonly(self):
        with open(c.__file__, encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("requests.", src)
        self.assertNotIn("subprocess", src)

    def test_ac06_no_new_step_id(self):
        from tools.recon_ai import probes
        self.assertEqual(len(probes.STEP_SPECS), 7)

    def test_ac07_three_pieces(self):
        r = c.analyze_instance({"public_ip": "1.2.3.4"}, {"ingress": [{"port": 22, "cidrs": ["0.0.0.0/0"]}]})
        self.assertTrue(r["command"] and r["output"] and r.get("shot_cmd"))


if __name__ == "__main__":
    unittest.main()
