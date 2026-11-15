#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""threat-model：AI 目标威胁建模（D10 / P1，通用·前置）。

单一公开入口 build_threat_model：recon 资产清单 + 分析师分类层 → ThreatModel。
不含任何实际攻击利用；框架组合为方法论 + 文档 + 许可 AI（矩阵 ⑬），无攻击框架。
"""
from .boundaries import shortest_paths, trust_boundaries
from .classify import enrich
from .decoy import judge_decoy
from .graph import build_graph, orchestration_order
from .model import (
    AssetView,
    AttackPath,
    DecoyVerdict,
    ThreatModel,
    DECOY,
)
from .render import render
from .score import high_value_only, score_and_rank

__all__ = [
    "build_threat_model",
    "render",
    "AssetView",
    "AttackPath",
    "DecoyVerdict",
    "ThreatModel",
    "DECOY",
    "high_value_only",
    "score_and_rank",
]


def build_threat_model(inventory, classification, now=None):
    """构建威胁模型（四节 + 质量门）。

    参数
      inventory: recon 资产清单（dict 含 assets 或 list），七字段只读消费。
      classification: 分析师分类层 {asset_id: {score_class, attack_surface,
                      trust_zone, reachable, foothold_required, depends_on,
                      decoy, decoy_dims, decoy_elapsed_minutes, decoy_reason}}。
      now: 可选注入时钟（便于确定性测试诱饵时间戳）。
    """
    assets = enrich(inventory, classification)
    ranked = score_and_rank(assets)
    boundaries = trust_boundaries(assets)
    paths = shortest_paths(assets, top_n=3)

    decoys = []
    cls = classification or {}
    for a in assets:
        raw = cls.get(a.asset_id, {})
        c = raw if isinstance(raw, dict) else {}
        if a.score_class == DECOY or c.get("decoy"):
            decoys.append(judge_decoy(
                a,
                dims=c.get("decoy_dims"),
                elapsed_minutes=float(c.get("decoy_elapsed_minutes", 0.0) or 0.0),
                now=now,
                reason=c.get("decoy_reason", ""),
            ))

    graph = build_graph(assets, paths)
    order = orchestration_order(assets)
    target = inventory.get("target", "") if isinstance(inventory, dict) else ""

    return ThreatModel(
        target=target,
        high_value=ranked,
        boundaries=boundaries,
        paths=paths,
        decoys=decoys,
        graph=graph,
        order=order,
    )
