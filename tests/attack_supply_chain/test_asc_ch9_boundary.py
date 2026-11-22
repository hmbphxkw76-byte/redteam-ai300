#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B6 边界判定测试。"""
import sys, unittest
from tests._paths import ROOT
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
from tools.attack_supply_chain import ch9_boundary as b


class BoundaryTests(unittest.TestCase):
    def test_runtime_to_infra(self):
        r = b.classify("sidecar exec into shared request-queue volume")
        self.assertEqual(r["owner"], b.RUNTIME)

    def test_artifact_to_self(self):
        r = b.classify("poison model artifact in MinIO registry")
        self.assertEqual(r["owner"], b.ARTIFACT)

    def test_ambiguous_artifact_priority(self):
        r = b.classify("sidecar modifies model artifact")
        self.assertEqual(r["owner"], b.ARTIFACT)
        self.assertEqual(r["confidence"], "ambiguous")

    def test_no_signal(self):
        r = b.classify("")
        self.assertEqual(r["owner"], "")
        self.assertEqual(r["reason"], "no_signal")


if __name__ == "__main__":
    unittest.main()
