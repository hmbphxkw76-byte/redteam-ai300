#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""信任边界与最短攻击路径推导（SKILL 执行体 §2 + Ch10 A2/A5/A8）。"""
from .model import (AttackPath, DecisionGate, EST_MINUTES, STAGE_TEMPLATE,
                    SUBSKILL, TrustBoundary)


def trust_boundaries(assets, boundaries=None):
    """按信任域归类资产：{zone: [asset_id,...]}。

    信任域由分析师分类层提供（同网段/域、需立足点可达、直接可达）。
    新增 boundaries 参数（Ch10 Table 8）：附 _trust_boundaries 键承载实体列表，
    既有 zone→asset_id 映射形态不变。
    """
    zones = {}
    for a in assets:
        zones.setdefault(a.trust_zone or "未分类", []).append(a.asset_id)
    if boundaries:
        zones["_trust_boundaries"] = build_trust_boundaries(boundaries)
    return zones


def build_trust_boundaries(raw_list):
    """把分类层边界字典构建为 TrustBoundary 实体（五要素 + gap 标记）。"""
    result = []
    for i, b in enumerate(raw_list or [], 1):
        enforcement = b.get("enforcement", "") or ""
        gap = not enforcement or enforcement.upper() in ("NONE", "UNKNOWN", "无")
        result.append(TrustBoundary(
            id=b.get("id", "TB-%d" % i),
            from_component=b.get("from", "") or b.get("from_component", ""),
            to_component=b.get("to", "") or b.get("to_component", ""),
            trust_type=b.get("trust_type", ""),
            enforcement=enforcement,
            validation_status=b.get("validation_status", "UNVALIDATED"),
            offensive_implication=b.get("offensive_implication", ""),
            identity_collapse=bool(b.get("identity_collapse", False)),
            is_gap=gap,
        ))
    return result


def shortest_paths(assets, top_n=3, boundaries=None, assumptions=None):
    """对 top-N 高价值资产（非诱饵）计算最短攻击路径。

    每条路径标注起止、必经阶段、预计耗时、依赖前置子技能；依赖资产缺失或不可达
    则标「待补」，不虚构可达性。Ch10 增量：boundaries→boundary_crossings；
    path_gates（分类层每个资产的 gates）→ DecisionGate。status 由 decision 模块覆盖。
    """
    index = {a.asset_id: a for a in assets}
    candidates = [a for a in assets if not a.is_decoy and a.score_class in STAGE_TEMPLATE]
    candidates = sorted(candidates, key=lambda a: a.rank_key())[:top_n]

    paths = []
    for a in candidates:
        missing = False
        for dep in a.depends_on:
            d = index.get(dep)
            if d is None or not d.reachable:
                missing = True
                break
        status = "待补" if missing else "可达"
        start = a.depends_on[0] if a.depends_on else "（直接可达）"
        crossings = []
        for b in (boundaries or []):
            if a.asset_id in (b.from_component, b.to_component):
                crossings.append(b.id)
        gates = [DecisionGate(assumption_id=str(g)) for g in
                 (getattr(a, "path_gates", []) or [])]
        paths.append(AttackPath(
            target_asset=a.asset_id,
            start_asset=start,
            score_class=a.score_class,
            stages=list(STAGE_TEMPLATE[a.score_class]),
            est_minutes=EST_MINUTES.get(a.score_class, 60),
            depends_on=list(SUBSKILL.get(a.score_class, [])),
            status=status,
            boundary_crossings=crossings,
            gates=gates,
        ))
    return paths
