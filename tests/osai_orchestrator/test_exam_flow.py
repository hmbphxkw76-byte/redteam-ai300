#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""考试链状态机单测（AC-08）：只验证阶段推进与停留，不执行攻击。"""
import unittest

from tools.osai_orchestrator.exam_flow import (
    STAGES, ExamPipeline, run_with_handoffs, stage_gate_ok,
)
from tools.osai_orchestrator.models import GateResult, Verdict


def gates(*names):
    return [GateResult(n, Verdict.PASS) for n in names]


def blocked(name):
    return GateResult(name, Verdict.BLOCKED, findings=["演练失败"])


class ExamFlowTests(unittest.TestCase):
    def test_stage_order_is_fixed(self):
        # GOVERNANCE §4.5（MUST）：威胁建模 → 侦察枚举 → …；ADR-0009 对齐实现与宪法。
        self.assertEqual(STAGES[0], "threat-model")
        self.assertEqual(STAGES[1], "recon")
        self.assertEqual(STAGES[-1], "report")
        self.assertEqual(len(STAGES), 9)

    def test_missing_gate_blocks_stage(self):
        self.assertFalse(stage_gate_ok("ai-vector", gates("H1")))
        self.assertTrue(stage_gate_ok("ai-vector", gates("H2", "H3")))

    def test_run_chain_advances_when_all_gates_pass(self):
        by_stage = {s: gates("H1", "H2", "H3", "H4", "H5", "H6") for s in STAGES}
        stage, ok = ExamPipeline().run_chain(by_stage)
        self.assertTrue(ok)
        self.assertEqual(stage, "report")

    def test_failed_handoff_stays_at_current_stage(self):
        by_stage = {s: gates("H1", "H2", "H3", "H4", "H5", "H6") for s in STAGES}
        by_stage["ai-vector"] = gates("H2") + [blocked("H3")]
        stage, ok = ExamPipeline().run_chain(by_stage)
        self.assertFalse(ok)
        self.assertEqual(stage, "ai-vector")

    def test_run_with_handoffs_consumes_h1_to_h6(self):
        stage, ok = run_with_handoffs(
            assets=[{}], gaps=[], evidence={"screenshot": "s.png", "scored": True},
            dual_cell="面板=FLAG{ok}；截图=shot.png", loot_row={"asset_id": "L-1", "status": "有效"},
            report_steps=["recon-01"], recon_steps=["recon-01"], hosts=["10.0.0.1"],
            submission=(True, True, True))
        self.assertFalse(ok)
        self.assertEqual(stage, "threat-model")

    def test_run_with_handoffs_passes_when_all_gates_green(self):
        asset = {"asset_id": "A-1", "category": "ai", "product": "p", "version": "1",
                 "endpoint": "http://x", "credential_hint": "none",
                 "evidence_step": "recon-01", "existence": "已确认"}
        stage, ok = run_with_handoffs(
            assets=[asset], gaps=[], evidence={"screenshot": "s.png", "scored": True},
            dual_cell="面板=FLAG{ok}；截图=shot.png", loot_row={"asset_id": "L-1", "status": "有效"},
            report_steps=["recon-01"], recon_steps=["recon-01"], hosts=["10.0.0.1"],
            submission=(True, True, True))
        self.assertTrue(ok)
        self.assertEqual(stage, "report")

    def test_advance_single_step(self):
        p = ExamPipeline()
        stage, ok = p.advance(gates("H1"))
        self.assertTrue(ok)
        self.assertEqual(stage, "recon")
        stage, ok = p.advance(gates("H1"))
        self.assertTrue(ok)
        self.assertEqual(stage, "foothold")


if __name__ == "__main__":
    unittest.main()
