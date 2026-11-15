#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""capstone-rehearse 数据模型（设计 §5：唯一构造点为 walk.rehearse）。

纯标准库、零 PyRIT 依赖。`RehearsalResult` 是下游唯一消费面，
字段与规格 v2 §4 一致；`to_dict()` 供机读 JSON 与确定性双跑比对（AC-18）。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, Tuple

SCHEMA_VERSION = "1.0"
BLOCKING = "blocking"
NON_BLOCKING = "non_blocking"
SEVERITIES = (BLOCKING, NON_BLOCKING)

# 核实闸单一事实源（v2 §6 / 调研 §6）：逐条带取证方式；状态由 pending 动态判定。
# VG-1 已由 2026-11-15 外部一手源交叉验证关闭，永远不在 pending 中。
GATE_DETAILS = (
    ("VG-1", "2026-11-15 一手源交叉验证：官方全文无演练域/节奏表述（已排除）"),
    ("VG-2", "演练目标按 collect_evidence.py --step cr-NN --strict 逐步计时"),
    ("VG-3", "诱饵机判定策略 + 演练片段路径"),
    ("VG-4", "verify-evidence 单次约束 + 面板/截图片段"),
    ("VG-5", "技能「失败与豁免」；报告写明结论不外推"),
    ("VG-6", "GitHub API Release Notes v1.1.0 vs v1.0.0 源码树；独立工单订正"),
)


@dataclass(frozen=True)
class Stage:
    stage_id: str
    name: str
    skill: str
    phase: str


@dataclass(frozen=True)
class StageEvidence:
    """就绪四项判据（v2 AC-02）：任一缺失即未就绪。"""

    skill_body: bool
    implementation: bool
    evidence_contract: bool
    fragment_path: bool

    @property
    def ready(self) -> bool:
        return (self.skill_body and self.implementation
                and self.evidence_contract and self.fragment_path)

    def missing(self) -> Tuple[str, ...]:
        names = (("skill_body", "技能本体"), ("implementation", "实现落点"),
                 ("evidence_contract", "证据契约"), ("fragment_path", "片段路径"))
        return tuple(label for attr, label in names if not getattr(self, attr))


@dataclass(frozen=True)
class CoverageRow:
    stage_id: str
    skill: str
    ready: bool
    evidence_chain: bool


@dataclass(frozen=True)
class TimelineSlot:
    segment: str
    start: float
    end: float
    duration: float
    key_node: str
    estimate: float
    measured: Optional[float] = None


@dataclass(frozen=True)
class Gap:
    stage_id: str
    severity: str
    description: str
    suggestion: str


@dataclass(frozen=True)
class RehearsalResult:
    schema_version: str
    matrix: Tuple[CoverageRow, ...]
    timeline: Tuple[TimelineSlot, ...]
    gaps: Tuple[Gap, ...]
    ready_for_exam: bool
    pending: Tuple[str, ...]
    overtime: bool
    compression: Tuple[str, ...] = ()

    @property
    def blocking(self) -> Tuple[Gap, ...]:
        return tuple(g for g in self.gaps if g.severity == BLOCKING)

    @property
    def non_blocking(self) -> Tuple[Gap, ...]:
        return tuple(g for g in self.gaps if g.severity == NON_BLOCKING)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "matrix": [asdict(r) for r in self.matrix],
            "timeline": [asdict(s) for s in self.timeline],
            "gaps": [asdict(g) for g in self.gaps],
            "blocking": [g.stage_id for g in self.blocking],
            "ready_for_exam": self.ready_for_exam,
            "pending": list(self.pending),
            "gates": [{"id": gate,
                       "status": "待取证" if gate in self.pending else "已关闭",
                       "method": method} for gate, method in GATE_DETAILS],
            "overtime": self.overtime,
            "compression": list(self.compression),
        }
