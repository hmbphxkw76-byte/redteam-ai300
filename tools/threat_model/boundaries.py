#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""信任边界与最短攻击路径推导（SKILL 执行体 §2）。"""
from .model import AttackPath, EST_MINUTES, STAGE_TEMPLATE, SUBSKILL


def trust_boundaries(assets):
    """按信任域归类资产：{zone: [asset_id,...]}。

    信任域由分析师分类层提供（同网段/域、需立足点可达、直接可达）。
    """
    zones = {}
    for a in assets:
        zones.setdefault(a.trust_zone or "未分类", []).append(a.asset_id)
    return zones


def shortest_paths(assets, top_n=3):
    """对 top-N 高价值资产（非诱饵）计算最短攻击路径。

    每条路径标注起止、必经阶段、预计耗时、依赖前置子技能；若声明的依赖资产
    缺失或不可达，路径标「待补」，不虚构可达性（SKILL「失败与豁免」）。
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
        paths.append(AttackPath(
            target_asset=a.asset_id,
            start_asset=start,
            score_class=a.score_class,
            stages=list(STAGE_TEMPLATE[a.score_class]),
            est_minutes=EST_MINUTES.get(a.score_class, 60),
            depends_on=list(SUBSKILL.get(a.score_class, [])),
            status=status,
        ))
    return paths
