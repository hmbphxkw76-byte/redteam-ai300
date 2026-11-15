#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""threat-model 证据契约测试（S2）：产出片段可机读、四节齐全、可按 asset_id 复用。

对齐 v2 TD3。参考 tests/test_recon_evidence_contract.py 的结构与命名。
威胁建模为规划技能（无逐步命令取证），契约以「结构化片段可被下游消费」为判据。
"""
import json
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.threat_model import build_threat_model, render  # noqa: E402
from tools.threat_model.model import ThreatModel  # noqa: E402


INVENTORY = {
    "target": "192.168.40.189",
    "assets": [
        {"asset_id": "ai-llm-a-01", "category": "LLM引擎", "product": "vLLM",
         "version": "0.6.1", "endpoint": "http://t:8000",
         "credential_hint": "Bearer-1a2b3c4d", "evidence_step": "loot/recon-01.md"},
        {"asset_id": "trad-d-01", "category": "传统向量机", "product": "Apache",
         "version": "2.4", "endpoint": "http://t:80",
         "credential_hint": "", "evidence_step": "loot/recon-07.md"},
        {"asset_id": "decoy-f-01", "category": "诱饵机", "product": "nginx",
         "version": "1.27.5", "endpoint": "http://t:8081",
         "credential_hint": "", "evidence_step": "loot/recon-07.md"},
    ],
}
CLASSIFICATION = {
    "ai-llm-a-01": {"score_class": "AI向量机", "attack_surface": "D3",
                    "trust_zone": "内网", "depends_on": ["trad-d-01"]},
    "trad-d-01": {"score_class": "传统向量机", "attack_surface": "D1",
                  "trust_zone": "公网入口"},
    "decoy-f-01": {"score_class": "诱饵机", "decoy": True,
                   "decoy_dims": {"behavior": True, "vuln_absent": True,
                                  "no_value": True},
                   "decoy_elapsed_minutes": 8},
}


class EvidenceContractTests(unittest.TestCase):
    def setUp(self):
        self.tm = build_threat_model(INVENTORY, CLASSIFICATION)
        self.md = render(self.tm)

    def test_fragment_is_markdown_and_readable(self):
        self.assertTrue(self.md.startswith("# 威胁模型"))
        self.assertIn("| 排名 |", self.md)          # 排序表
        self.assertIn("| 目标资产 |", self.md)       # 路径表
        self.assertIn("| 资产ID |", self.md)         # 诱饵表

    def test_fragment_reusable_by_asset_id(self):
        # 下游技能可按 asset_id 定位资产与其证据 step
        for aid in ("ai-llm-a-01", "trad-d-01", "decoy-f-01"):
            self.assertIn("`%s`" % aid, self.md)
        self.assertIn("loot/recon-01.md", self.md)   # evidence_step 锚点

    def test_four_quality_gate_sections_present(self):
        for sec in ("资产计分排序", "信任边界与最短攻击路径",
                    "诱饵判定清单", "优先级攻击图"):
            self.assertIn(sec, self.md)
        self.assertIn("质量门", self.md)

    def test_quality_gate_reports_all_four(self):
        self.assertEqual(self.tm.quality_gate(), [])
        self.assertIn("四项齐全", self.md)

    def test_decoy_excluded_from_graph_but_recorded(self):
        self.assertNotIn("decoy-f-01", self.tm.graph["nodes"])
        self.assertIn("decoy-f-01", self.tm.graph["excluded_decoys"])
        self.assertIn("诱饵判定清单", self.md)

    def test_orchestration_order_present(self):
        self.assertIn("编排顺序", self.md)
        self.assertTrue(self.tm.order)


class ContractViolationTests(unittest.TestCase):
    """契约违规：空模型须暴露缺失项而非静默通过。"""

    def test_empty_model_lists_missing_sections(self):
        empty = ThreatModel(target="t", high_value=[], boundaries={},
                            paths=[], decoys=None, graph={}, order=[])
        missing = empty.quality_gate()
        self.assertTrue(missing)
        md = render(empty)
        self.assertIn("未过门禁", md)


if __name__ == "__main__":
    unittest.main()
