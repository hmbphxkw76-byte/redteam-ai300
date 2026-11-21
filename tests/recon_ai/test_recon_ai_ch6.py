#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""recon-ai Ch6 侦察侧增量测试（AC-R1..R4），只测外部行为。"""
import json
import os
import sys
import tempfile
import unittest

from tests._paths import ROOT  # noqa: E402
sys.path.insert(0, ROOT)
from tests.support import recon_ai_fixtures as fx  # noqa: E402
from tools.recon_ai import runner, shot  # noqa: E402
from tools.recon_ai.transport import FakeTransport  # noqa: E402

from tools.recon_ai.emb_surface import build_emb_metadata
from tools.recon_ai.model import Asset, Existence
from tools.recon_ai.probes import Judgement
from tools.recon_ai import inventory


class Ch6EmbSurfaceTests(unittest.TestCase):
    def test_vector_asset_metadata(self):
        """AC-R1: 向量库资产含 export_surface/dim_candidates 字段；维度可得。"""
        m = build_emb_metadata("vector_db", endpoint="http://h:8080", dim=384)
        self.assertTrue(m["export_surface"])
        self.assertEqual(m["dim"], 384)
        self.assertEqual(m["dim_candidates"], ["需下游推断"])

    def test_rag_probing_entry(self):
        """AC-R2: RAG 资产含 probing_entry 布尔记录。"""
        m = build_emb_metadata("rag", endpoint="http://h:80", probing_entry=True)
        self.assertTrue(m["probing_entry"])
        self.assertNotIn("dim", m)  # RAG 类不臆测向量维度

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

    def test_runner_emits_emb_metadata_in_production(self):
        """AC-R1/R2: 真实 run_recon 产出的资产清单含 emb_metadata（生产接线）。"""
        target = fx.TARGET_LEGACY
        with tempfile.TemporaryDirectory() as tmp:
            report = runner.run_recon(
                target=target, out_dir=tmp,
                transport=FakeTransport(fx.legacy_routes(target)),
                shot=shot.FakeShot(), capture_shots=True)
            with open(os.path.join(report.run_dir, "ai-assets.json"), encoding="utf-8") as f:
                data = json.load(f)
            assets = data.get("assets", data) if isinstance(data, dict) else data
            joined = json.dumps(assets, ensure_ascii=False)
            self.assertIn("emb_metadata", joined)

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
