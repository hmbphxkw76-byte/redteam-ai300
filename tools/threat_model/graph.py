#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""优先级攻击图与编排顺序（SKILL 执行体 §4 / GOVERNANCE §4.5）。"""
from .model import DECOY


def build_graph(assets, paths):
    """构建优先级攻击图：节点=非诱饵资产，边=最短路径，诱饵排除在外。"""
    nodes = [a.asset_id for a in assets if not a.is_decoy]
    excluded = [a.asset_id for a in assets if a.is_decoy]
    node_set = set(nodes)
    edges = [
        {"from": p.start_asset, "to": p.target_asset, "status": p.status}
        for p in paths if p.target_asset in node_set
    ]
    roots = [a.asset_id for a in assets if a.score_class in ("AI向量机", "独立机")]
    return {"nodes": nodes, "edges": edges, "roots": roots, "excluded_decoys": excluded}


def orchestration_order(assets):
    """§4.5 编排顺序：先 AI向量机/独立机 → 再传统链 → 最后域控（proof.txt 单次提交）。"""
    priority = {"AI向量机": 0, "独立机": 0, "传统向量机": 1, "域控": 2, "链式入口": 3}
    live = [a for a in assets if not a.is_decoy]
    return [a.asset_id for a in
            sorted(live, key=lambda a: (priority.get(a.score_class, 9), a.asset_id))]
