#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""recon-ai Ch6 侦察侧增量测试（AC-R1..R4），只测外部行为。"""
import unittest

from tools.recon_ai.emb_surface import build_emb_metadata
from tools.recon_ai.model import Asset, Existence
from tools.recon_ai.probes import Judgement
from tools.recon_ai import inventory


class Ch6EmbSurfaceTests(unittest.TestCase):
    def test_vector_asset_metadata(self):
        """AC-R1: 向量库资产含 export_surface/dim 字段；维度可得。"""
        m = build_emb_metadata("vector_db", endpoint="http://h:8080", dim=384,
                               probing_entry=True)
        self.assertTrue(m["export_surface"])
        self.assertEqual(m["dim"], 384)
        self.assertTrue(m["probing_entry"])

    def test_dim_unavailable_no_guess(self):
        """AC-R3: 维度不可得记不可判定，不臆测模型。"""
        m = build_emb_metadata("vector_db", endpoint="http://h:19530")
        self.assertEqual(m["dim"], "不可判定")
        self.assertEqual(m["dim_candidates"], ["不可判定"])

    def test_non_vector_asset_empty(self):
        m = build_emb_metadata("llm_engine", endpoint="http://h:8000")
        self.assertEqual(m, {})

    def test_asset_to_dict_includes_emb_metadata(self):
        a = Asset(asset_id="ai-vector-h-01", category="vector_db", product="weaviate",
                  version="不可判定", endpoint="http://h:8080", credential_hint="无",
                  evidence_step="recon-04",
                  emb_metadata={"export_surface": True, "dim": 384})
        d = a.to_dict()
        self.assertIn("emb_metadata", d)
        self.assertEqual(d["emb_metadata"]["dim"], 384)
        self.assertEqual(len(a.missing_fields()), 0)  # 七字段契约未破坏

    def test_readonly_boundary(self):
        """AC-R4: 元数据构建无副作用（不返回导出内容/载荷）。"""
        m = build_emb_metadata("vector_db", endpoint="http://h:8080", dim=384)
        self.assertNotIn("vectors", m)
        self.assertNotIn("payload", m)
        self.assertNotIn("exported", m)

    def test_inventory_accepts_emb_meta(self):
        """AC-R1: build() 将 emb_meta 填入对应 step 的资产。"""
        j = {"recon-04": Judgement(Existence.PRESENT, product="weaviate",
                                    context={"endpoint": "http://h:8080"})}
        inv = inventory.build(j, "http://h", "passive",
                              emb_meta={"recon-04": {"export_surface": True, "dim": 384}})
        assets = [a for a in inv.assets if a.evidence_step == "recon-04"]
        self.assertEqual(len(assets), 1)
        self.assertEqual(assets[0].emb_metadata["dim"], 384)


if __name__ == "__main__":
    unittest.main()
