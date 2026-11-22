#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""threat-model Ch9 C3 身份链资产化加固测试（AC-01..11）。"""
import os
import sys
import unittest

from tests._paths import ROOT  # noqa: E402
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.threat_model import ch9_c3_downstream as down  # noqa: E402
from tools.threat_model import ch9_c3_model as m  # noqa: E402
from tools.threat_model import ch9_identity_chain as c  # noqa: E402
from tools.threat_model import decoy, graph  # noqa: E402
from tools.threat_model.model import AssetView  # noqa: E402

READ = [{"resource": "secrets", "verb": "list"}]
WRITE = [{"resource": "pods", "verb": "create"}]


class ChainTests(unittest.TestCase):
    def test_ac01_iam_graph_assets(self):
        g = c.iam_chain_graph(["Admin", "Deploy", "App"])
        assets = c.to_assets(g)
        self.assertEqual([a.asset_id for a in assets],
                         ["iam-admin", "iam-deploy", "iam-app"])
        self.assertEqual(assets[1].depends_on, ["iam-admin"])
        self.assertEqual(assets[2].depends_on, ["iam-deploy"])

    def test_ac02_stable_asset_id(self):
        g = c.iam_chain_graph(["App"])
        self.assertEqual(m.asset_id_for(m.IAM, "App"), m.asset_id_for(m.IAM, "App"))
        self.assertEqual(c.asset_ids_for(g), c.asset_ids_for(g))
        self.assertEqual(m.asset_id_for(m.IAM, "A/B"), "iam-a-b")

    def test_ac03_k8s_reachable_and_gap(self):
        g = c.k8s_identity_chain(READ, WRITE)
        self.assertTrue(g["reachable"])
        self.assertEqual(g["path"], ["secrets.read", "credentials.exfil", "pods.create"])
        self.assertFalse(c.k8s_identity_chain(WRITE, [])["reachable"])
        self.assertEqual(c.k8s_identity_chain(WRITE, [])["gap"], "no_secret_read")
        self.assertEqual(c.k8s_identity_chain(READ, [])["gap"], "no_pod_create")

    def test_ac03_k8s_asset_ids_referenceable(self):
        g = c.k8s_identity_chain(
            [dict(c, sa="sa-reader") for c in READ],
            [dict(c, sa="sa-deployer") for c in WRITE])
        self.assertEqual(g["service_accounts"], ("sa-reader", "sa-deployer"))
        ids = c.asset_ids_for(g, m.K8S_SA)
        self.assertEqual(ids, ("k8s-sa-sa-reader", "k8s-sa-sa-deployer"))
        self.assertEqual(down.claim_ids(g, m.K8S_SA), list(ids))
        v = c.to_verdict(g, m.K8S_SA)
        self.assertEqual(v.asset_ids, ids)
        bs = c.to_boundaries(g, m.K8S_SA)
        self.assertEqual(bs[0].from_component, ids[0])
        self.assertEqual(bs[0].to_component, ids[-1])
        paths = c.shortest_for_chain(g, m.K8S_SA)
        # 顺序由既有 rank_key 优先级决定（本轮不改优先级语义），只断言集合一致。
        self.assertEqual({p.target_asset for p in paths}, set(ids))

    def test_ac07_frozen_and_dict_shim(self):
        v = m.IdentityChainVerdict("REACHABLE")
        with self.assertRaises(Exception):
            v.outcome = "GAP"
        with self.assertRaises(ValueError):
            m.IdentityChainVerdict("BOGUS")
        with self.assertRaises(ValueError):
            m.IdentityChainVerdict("REACHABLE", "bogus_reason")
        self.assertEqual(v["outcome"], "REACHABLE")
        self.assertIsNone(v.get("missing"))


class BoundaryTests(unittest.TestCase):
    def test_ac04_iam_boundaries(self):
        g = c.iam_chain_graph(["A", "B"], boundary_crossed=True)
        bs = c.to_boundaries(g)
        self.assertEqual(len(bs), 1)
        self.assertEqual(bs[0].trust_type, "role_assumption")
        self.assertEqual(bs[0].from_component, "iam-a")
        self.assertEqual(bs[0].to_component, "iam-b")
        self.assertFalse(bs[0].is_gap)

    def test_ac04_k8s_collapse_boundary(self):
        bs = c.to_boundaries(c.k8s_identity_chain(READ, WRITE), m.K8S_SA)
        self.assertEqual(len(bs), 1)
        self.assertTrue(bs[0].identity_collapse)

    def test_ac06_shortest_reuses_existing(self):
        g = c.iam_chain_graph(["A", "B"])
        paths = c.shortest_for_chain(g)
        self.assertEqual(len(paths), 2)
        self.assertEqual(paths[0].target_asset, "iam-a")
        self.assertEqual(paths[0].start_asset, "（直接可达）")
        self.assertEqual(paths[1].start_asset, "iam-a")


class DownstreamTests(unittest.TestCase):
    def test_ac05_claim_ids(self):
        g = c.iam_chain_graph(["Admin", "App"])
        ids = down.claim_ids(g)
        self.assertEqual(ids, ["iam-admin", "iam-app"])
        self.assertTrue(all(a.asset_id in ids for a in c.to_assets(g)))

    def test_ac05_iam_ctx_compat(self):
        g = c.iam_chain_graph(["Admin", "App"])
        self.assertTrue(down.compatible_with_iam_ctx(g, ["Admin", "App"]))
        self.assertFalse(down.compatible_with_iam_ctx(g, ["App"]))

    def test_ac07_verdict_assets(self):
        g = c.iam_chain_graph(["A", "B"])
        v = c.to_verdict(g)
        self.assertEqual(v.outcome, "REACHABLE")
        self.assertEqual(v.asset_ids, ("iam-a", "iam-b"))
        kv = c.to_verdict(c.k8s_identity_chain(READ, WRITE), m.K8S_SA)
        self.assertEqual(kv.outcome, "REACHABLE")
        self.assertTrue(kv.path)
        ev = c.to_verdict({"nodes": []})
        self.assertEqual(ev.outcome, "ABSENT")
        self.assertEqual(ev.reason, "empty_chain")


class RegressionTests(unittest.TestCase):
    def test_ac08_no_network(self):
        for mod in (c, m, down):
            with open(mod.__file__, encoding="utf-8") as f:
                src = f.read()
            for bad in ("requests.", "socket.", "subprocess", "sts.assume_role",
                        "kubernetes.client", "pyrit"):
                self.assertNotIn(bad, src.lower())

    def test_ac09_existing_semantics_intact(self):
        # 诱饵/优先级图语义零 diff：既有模块仍可独立工作。
        a = AssetView(asset_id="x", score_class="诱饵机")
        self.assertTrue(a.is_decoy)
        self.assertEqual(c.SCORE_CLASS, "链式入口")

    def test_ac09_lightweight_compat(self):
        g = c.iam_chain_graph(["A", "B", "C"])
        self.assertEqual(len(g["nodes"]), 3)
        self.assertEqual(len(g["edges"]), 2)
        self.assertIn("Figure 3", g["anchor"])
        r = c.k8s_identity_chain(READ, WRITE)
        self.assertTrue(r["reachable"])
        self.assertIn("Table 2", r["anchor"])


if __name__ == "__main__":
    unittest.main()
