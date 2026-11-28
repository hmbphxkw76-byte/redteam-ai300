#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""OSAI 考试链显式阶段状态机：消费既有 H1–H6 交接判据，不执行攻击、不联网。

判据来源：tools/osai_orchestrator/handoff.py:153-164（all_checks）。
本模块不复制判定逻辑，只规定阶段顺序与每阶段的必需交接门。
"""
from __future__ import annotations

from typing import Iterable, Mapping, Tuple

from .handoff import all_checks
from .models import GateResult, Verdict

# 阶段顺序由 GOVERNANCE §4.5（MUST）裁定：威胁建模先于侦察枚举；见 ADR-0009。
STAGES = (
    "threat-model", "recon", "foothold", "ai-vector", "standalone",
    "loot", "dc", "verify", "report",
)

REQUIRED_GATES: Mapping[str, Tuple[str, ...]] = {
    "recon": ("H1",),
    "threat-model": ("H1",),
    "foothold": ("H1",),
    "ai-vector": ("H2", "H3"),
    "standalone": ("H2", "H3"),
    "loot": ("H4",),
    "dc": ("H3", "H4"),
    "verify": ("H2", "H3", "H5"),
    "report": ("H5", "H6"),
}


def _by_name(results: Iterable[GateResult]) -> dict:
    return {getattr(r, "name", ""): r for r in results}


def stage_gate_ok(stage: str, results: Iterable[GateResult]) -> bool:
    """当前阶段的所有必需交接门均为 PASS 才放行。"""
    if stage not in REQUIRED_GATES:
        return False
    table = _by_name(results)
    for gate in REQUIRED_GATES[stage]:
        r = table.get(gate)
        if r is None or getattr(r, "verdict", None) is not Verdict.PASS:
            return False
    return True


class ExamPipeline:
    """只读状态机：advance 返回 (当前或下一阶段, 是否可继续)。"""

    def __init__(self, stage: str = STAGES[0]):
        if stage not in STAGES:
            raise ValueError("未知阶段：%s" % stage)
        self.stage = stage

    def advance(self, results: Iterable[GateResult]) -> Tuple[str, bool]:
        if not stage_gate_ok(self.stage, results):
            return self.stage, False
        idx = STAGES.index(self.stage)
        if idx == len(STAGES) - 1:
            return self.stage, True
        self.stage = STAGES[idx + 1]
        return self.stage, True

    def run_chain(self, results_by_stage: Mapping[str, Iterable[GateResult]]) -> Tuple[str, bool]:
        """按阶段顺序推进；任一阶段交接失败即停留并返回 False。"""
        for stage in STAGES[STAGES.index(self.stage):]:
            if not stage_gate_ok(stage, results_by_stage.get(stage, [])):
                self.stage = stage
                return self.stage, False
            if stage == STAGES[-1]:
                self.stage = stage
                return self.stage, True
            self.stage = STAGES[STAGES.index(stage) + 1]
        return self.stage, True


def run_with_handoffs(assets, gaps, evidence, dual_cell, loot_row,
                      report_steps, recon_steps, hosts, submission) -> Tuple[str, bool]:
    """生产入口：直接消费 handoff.all_checks 的 H1–H6，不复制判定逻辑。"""
    results = all_checks(assets, gaps, evidence, dual_cell, loot_row,
                         report_steps, recon_steps, hosts, submission)
    by_stage = {stage: results for stage in STAGES}
    return ExamPipeline().run_chain(by_stage)
