#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch10 对齐增量测试：AC-01..AC-18（新模块正常态 + 边界态）。"""
import unittest

from tools.threat_model.model import (Assumption, AttackPath, DecisionGate,
                                      ThreatModel, ATLAS_IDS)
from tools.threat_model import assumptions, roe, decision, atlas, brief


class AssumptionRegisterTests(unittest.TestCase):
    """AC-01/02/03 假设登记册六字段 + 置信度桶 + 状态机。"""

    def test_ac01_register_six_fields(self):
        obs = [{"id": "A-01", "observation": "文档提到编排器",
                "hypothesis": "存在单一编排组件", "confidence": "HIGH",
                "source": "client doc"}]
        reg = assumptions.to_register(obs)
        self.assertEqual(len(reg), 1)
        self.assertEqual(len(reg[0].as_row()), 6)
        self.assertEqual(reg[0].status, "UNVALIDATED")

    def test_ac02_low_and_absence_go_to_verification(self):
        self.assertEqual(assumptions.bucket("LOW", "client doc"), "verification_task")
        self.assertEqual(assumptions.bucket("MEDIUM", "absence of evidence"),
                         "verification_task")
        self.assertEqual(assumptions.bucket("HIGH", "client doc"), "attack_plan")

    def test_ac03_transition_validated_to_invalidated_derives(self):
        a = Assumption(id="A-01", observation="o", hypothesis="h",
                       status="VALIDATED")
        updated, derived = assumptions.transition(a, "INVALIDATED")
        self.assertEqual(updated.status, "INVALIDATED")
        self.assertTrue(derived)
        self.assertEqual(derived[0].status, "UNVALIDATED")

    def test_ac03_illegal_transition_rejected(self):
        a = Assumption(id="A-02", observation="o", hypothesis="h",
                       status="INVALIDATED")
        updated, derived = assumptions.transition(a, "VALIDATED")
        self.assertEqual(updated.status, "INVALIDATED")
        self.assertEqual(derived, [])

    def test_ac14_derive_from_detections_medium_and_incomplete(self):
        derived = assumptions.derive_from_detections([{"name": "rule-1"}])
        self.assertTrue(any(a.confidence == "MEDIUM" for a in derived))
        self.assertTrue(any("规则集可能不完整" in a.source for a in derived))


class RoETests(unittest.TestCase):
    """AC-06 RoE 硬过滤双轨。"""

    def _path(self, target="qdrant-prod", status="可达", risk="LOW", crossings=None):
        return AttackPath(target_asset=target, start_asset="host", score_class="AI向量机",
                          stages=["入口"], est_minutes=10, depends_on=[],
                          status=status, boundary_crossings=crossings or [])

    def _model(self, paths):
        return ThreatModel(target="t", high_value=[], boundaries={}, paths=paths,
                           decoys=[], graph={"edges": [{"from": "host", "to": p.target_asset}
                                                       for p in paths]},
                           order=[])

    def test_ac06_prohibited_path_removed_but_reported(self):
        bad = self._path(target="qdrant-prod")
        good = self._path(target="mcp-server")
        m = self._model([bad, good])
        roe_cfg = {"prohibited_targets": ["qdrant-prod"]}
        out, findings = roe.apply_roe(m, roe_cfg)
        self.assertEqual(len(out.paths), 1)
        self.assertEqual(out.paths[0].target_asset, "mcp-server")
        self.assertTrue(any("qdrant-prod" in f for f in findings))
        self.assertEqual(len([e for e in out.graph["edges"]
                              if e["to"] == "qdrant-prod"]), 0)

    def test_ac06_no_conditional_approval_wording(self):
        self.assertFalse(roe.is_prohibited(self._path(status="GO"), {}))
        # 被禁即移除，不存在"若客户批准"放行分支
        self.assertTrue(roe.is_prohibited(
            self._path(crossings=["TB-prod"]), {"prohibited_tags": ["prod"]}))

    def test_ac06_required_reports_recorded(self):
        out, findings = roe.apply_roe(
            self._model([self._path(target="safe")]),
            {"required_reports": [{"text": "MCP 调用 24h 内报告"}]})
        self.assertTrue(any("24h" in f for f in findings))
        self.assertEqual(len(out.paths), 1)


class DecisionTests(unittest.TestCase):
    """AC-08/09 Go/No-Go 门 + 决策矩阵。"""

    def _path(self, gates):
        return AttackPath(target_asset="aws", start_asset="mcp", score_class="AI向量机",
                          stages=["入口"], est_minutes=10, depends_on=[], status="可达",
                          gates=[DecisionGate(assumption_id=g) for g in gates])

    def test_ac08_validated_gate_go(self):
        a = [Assumption(id="A-1", observation="o", hypothesis="h", status="VALIDATED")]
        paths = decision.evaluate_gates([self._path(["A-1"])], a)
        self.assertEqual(paths[0].gate_decision, "GO")
        self.assertEqual(paths[0].gates[0].decision, "GO")

    def test_ac08_unvalidated_gate_hold(self):
        a = [Assumption(id="A-1", observation="o", hypothesis="h", status="UNVALIDATED")]
        paths = decision.evaluate_gates([self._path(["A-1"])], a)
        self.assertEqual(paths[0].gate_decision, "HOLD")

    def test_ac08_invalidated_gate_blocked(self):
        a = [Assumption(id="A-1", observation="o", hypothesis="h", status="INVALIDATED")]
        paths = decision.evaluate_gates([self._path(["A-1"])], a)
        self.assertEqual(paths[0].gate_decision, "BLOCKED")

    def test_ac09_matrix_four_columns(self):
        a = [Assumption(id="A-1", observation="o", hypothesis="h", status="UNVALIDATED")]
        paths = decision.evaluate_gates([self._path(["A-1"])], a)
        m = decision.go_no_go(paths, a, remaining_days=8)
        self.assertEqual(len(m["rows"][0]), 5)
        self.assertEqual(m["rows"][0][4], "HOLD")

    def test_ac09_time_pressure_forces_hold(self):
        a = [Assumption(id="A-1", observation="o", hypothesis="h", status="UNVALIDATED")]
        paths = decision.evaluate_gates([self._path(["A-1"])], a)
        m = decision.go_no_go(paths, a, remaining_days=1)
        self.assertEqual(m["rows"][0][4], "HOLD")


class AtlasTests(unittest.TestCase):
    """AC-13 七 ID 集合 + 前置门槛。"""

    def test_ac13_seven_ids_exact(self):
        mapped = atlas.map_techniques([], [])
        self.assertEqual({m.technique_id for m in mapped}, set(ATLAS_IDS))
        self.assertEqual(len(mapped), 7)

    def test_ac13_precondition_unvalidated_is_applicable_if(self):
        class A:
            asset_id = "mcp-01"
            product = "mcp"
            category = "tool"
        mapped = atlas.map_techniques([A()], [])
        mcp = [m for m in mapped if m.technique_id == "AML.T0048"][0]
        self.assertEqual(mcp.applicability(), "applicable if")
        self.assertFalse(mcp.immediately_applicable)

    def test_ac13_precondition_validated_is_immediate(self):
        class A:
            asset_id = "mcp-01"
            product = "mcp"
            category = "tool"
        validated = [Assumption(id="agent_token_valid", observation="o",
                                hypothesis="h", status="VALIDATED")]
        mapped = atlas.map_techniques([A()], validated)
        mcp = [m for m in mapped if m.technique_id == "AML.T0048"][0]
        self.assertEqual(mcp.applicability(), "立即适用")


class BriefTests(unittest.TestCase):
    """AC-07 六段简报 + 三字段 + 版本史。"""

    def test_ac07_six_sections_and_fields(self):
        tm = ThreatModel(target="Nexus", high_value=[], boundaries={}, paths=[],
                         decoys=[], graph={}, order=[])
        text = brief.render_brief(tm)
        for sec in ("TARGET SUMMARY", "CROWN JEWELS", "ASSUMPTION REGISTER STATUS",
                    "SCOPE CONSTRAINTS", "ESCALATION PATHS", "NEXT ACTIONS"):
            self.assertIn(sec, text)
        self.assertIn("Classification:", text)
        self.assertIn("Engagement Day:", text)
        self.assertIn("Brief Version:", text)

    def test_ac07_decision_log_is_version_history(self):
        tm = ThreatModel(target="Nexus", high_value=[], boundaries={}, paths=[],
                         decoys=[], graph={}, order=[],
                         decision_log=["整合侦察结果"], revision=2)
        text = brief.render_brief(tm)
        self.assertIn("DECISION LOG", text)
        self.assertIn("整合侦察结果", text)


class ModelContractTests(unittest.TestCase):
    """AC-12/15/18 既有契约 + 增量字段。"""

    def test_ac18_quality_gate_unchanged_four(self):
        tm = ThreatModel(target="t", high_value=[], boundaries={}, paths=[],
                         decoys=[], graph={}, order=[])
        self.assertEqual(len(tm.quality_gate()), 3)  # high_value/boundaries/graph 缺

    def test_ac18_empty_decoys_is_legal(self):
        tm = ThreatModel(target="t", high_value=[{"x": 1}], boundaries={"a": []},
                         paths=[{"x": 1}], decoys=[], graph={"a": 1}, order=["a"])
        self.assertNotIn("诱饵判定清单", tm.quality_gate())

    def test_ac15_trust_gap_and_identity_collapse_fields(self):
        from tools.threat_model.model import TrustBoundary
        b = TrustBoundary(id="TB-5", from_component="mcp", to_component="vault",
                          identity_collapse=True, is_gap=True, enforcement="")
        self.assertTrue(b.identity_collapse and b.is_gap)
        self.assertIn("无", b.as_row())


if __name__ == "__main__":
    unittest.main()
