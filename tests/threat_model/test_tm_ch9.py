#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""threat-model Ch9 身份链测试（AC-01..06）。"""
import sys, unittest
from tests._paths import ROOT
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from tools.threat_model import ch9_identity_chain as m


class ChainTests(unittest.TestCase):
    def test_ac01_graph(self):
        g = m.iam_chain_graph(["A", "B", "C"])
        self.assertEqual(len(g["nodes"]), 3)
        self.assertEqual(len(g["edges"]), 2)

    def test_ac02_boundary(self):
        g = m.iam_chain_graph(["A", "B"], True)
        self.assertTrue(g["boundary_crossed"])

    def test_ac03_reachable(self):
        r = m.k8s_identity_chain([{"resource": "secrets", "verb": "list"}],
                                 [{"resource": "pods", "verb": "create"}])
        self.assertTrue(r["reachable"])
        self.assertEqual(r["path"], ["secrets.read", "credentials.exfil", "pods.create"])

    def test_ac04_gap(self):
        r = m.k8s_identity_chain([{"resource": "pods", "verb": "get"}], [])
        self.assertFalse(r["reachable"])
        self.assertEqual(r["gap"], "no_secret_read")
        r2 = m.k8s_identity_chain([{"resource": "secrets", "verb": "list"}], [])
        self.assertEqual(r2["gap"], "no_pod_create")

    def test_ac05_no_framework(self):
        with open(m.__file__, encoding="utf-8") as f:
            src = f.read()
        self.assertNotIn("pyrit", src.lower())
        self.assertNotIn("requests", src)

    def test_ac06_anchors(self):
        self.assertIn("Figure 3", m.iam_chain_graph(["A"])["anchor"])
        self.assertIn("Table 2", m.k8s_identity_chain([], [])["anchor"])


if __name__ == "__main__":
    unittest.main()
