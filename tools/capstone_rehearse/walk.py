#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""走查编排：`rehearse(...)` 是唯一深层入口与对象图构造收敛点（设计 §5）。

三件套判据不重写：证据链贯通只读既有 `EvidenceSource` 产出的 Fragment
（`report_exam/index.py#parse_fragment`），符合 C1 单一事实源。
"""
from __future__ import annotations

from typing import Iterable, Optional, Sequence, Tuple

from tools.loot_manage.registry import fragment_pieces

from .clock import DECOY_TIMEBOX, DEFAULT_DURATIONS, EXAM_HOURS, SEGMENTS, Clock
from .inventory import StageInventory, spec_for
from .model import (BLOCKING, NON_BLOCKING, SCHEMA_VERSION, CoverageRow, Gap,
                    RehearsalResult, Stage, TimelineSlot)

# VG-1 已由阶段 3 一手源交叉验证关闭（官方无演练域/节奏表述，已排除）
VERIFICATION_GATES = ("VG-2", "VG-3", "VG-4", "VG-5", "VG-6")
# 影响及格的阻断性阶段：域控收敛 / 证据校验 / 报告生成（§4.3、§7.3、§2.4）
BLOCKING_STAGES = frozenset(("cr-07", "cr-08", "cr-09"))


def _chain(stage: Stage, fragments: Sequence) -> bool:
    """证据链贯通：复用既有 `registry.fragment_pieces` 三件套判据（C1）。

    不另写真值判据：片段原文（`Fragment.raw`，由 `parse_fragment` 保留）交给
    战利品登记簿的单一事实源判定；`raw` 为空即如实记为断点。
    """
    spec = spec_for(stage.stage_id)
    skills = set(spec[4]) | {stage.skill}
    for frag in fragments:
        haystack = " ".join(str(x or "") for x in (
            getattr(frag, "source_path", ""), getattr(frag, "target", ""),
            getattr(frag, "step_id", "")))
        if not any(s in haystack for s in skills):
            continue
        raw = getattr(frag, "raw", "") or ""
        if fragment_pieces(raw)["complete"]:
            return True
    return False


def _timeline(clock: Clock):
    durations = clock.durations()
    measured = clock.measured()
    slots = []
    cursor = 0.0
    for key, label, node in SEGMENTS:
        value = float(durations.get(key, DEFAULT_DURATIONS[key]))
        slots.append(TimelineSlot(label, cursor, cursor + value, value, node,
                                  DEFAULT_DURATIONS[key], measured.get(key)))
        cursor += value
    timebox = float(durations.get(DECOY_TIMEBOX, DEFAULT_DURATIONS[DECOY_TIMEBOX]))
    slots.append(TimelineSlot(
        "诱饵机 ≤30min 时间盒", 0.0, timebox, timebox,
        "疑似诱饵：超时即主动放弃并记录理由（§5.3）",
        DEFAULT_DURATIONS[DECOY_TIMEBOX], measured.get(DECOY_TIMEBOX)))
    overtime = cursor > EXAM_HOURS
    compression = []
    if overtime:
        compression = [
            "并行 threat-model / recon-ai 与 decoy-detect，压缩前置串行段",
            "优先 AI向量机 / 独立机高杠杆目标（15 分），暂缓低分值传统链",
            "把证据补录前移到攻击同步落盘，减少 16–20h 收敛段占用",
        ]
    if timebox > DEFAULT_DURATIONS[DECOY_TIMEBOX]:
        compression.append("诱饵机时间盒超时：须记录放弃理由与实测耗时")
    return tuple(slots), overtime, tuple(compression)


def rehearse(inventory: StageInventory, clock: Clock,
             evidence_source=None,
             closed_gates: Optional[Iterable[str]] = None) -> RehearsalResult:
    """执行九阶段走查，返回版本化机读结果（不抛业务异常，见设计 §2）。"""
    if inventory is None or clock is None:
        raise ValueError("inventory 与 clock 均为必需注入项")
    fragments = list(evidence_source.iter_fragments()) if evidence_source else []
    matrix, gaps = [], []
    for stage in inventory.stages():
        evidence = inventory.evidence_for(stage.stage_id)
        chain = _chain(stage, fragments)
        matrix.append(CoverageRow(stage.stage_id, stage.skill,
                                  evidence.ready, chain))
        if not evidence.ready:
            severity = BLOCKING if stage.stage_id in BLOCKING_STAGES else NON_BLOCKING
            gaps.append(Gap(
                stage.stage_id, severity,
                "就绪四项判据缺失：%s" % "、".join(evidence.missing()),
                "补对应技能实现与证据契约夹具，并补齐 --step cr-NN --strict 片段"))
        if not chain:
            gaps.append(Gap(
                stage.stage_id, NON_BLOCKING,
                "证据链贯通未证实（无可被既有片段解析器消费的三件套片段）",
                "证据契约加固：按路径补齐演练片段并回归 parse_fragment"))
    timeline, overtime, compression = _timeline(clock)
    closed = set(closed_gates or ())
    pending = tuple(g for g in VERIFICATION_GATES if g not in closed)
    ready = (not any(g.severity == BLOCKING for g in gaps)
             and not pending
             and all(row.ready and row.evidence_chain for row in matrix))
    return RehearsalResult(
        schema_version=SCHEMA_VERSION,
        matrix=tuple(matrix), timeline=timeline, gaps=tuple(gaps),
        ready_for_exam=ready, pending=pending,
        overtime=overtime, compression=compression,
    )
