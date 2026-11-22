#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""threat-model：AI 目标威胁建模（D10 / P1，通用·前置）。

单一公开入口 build_threat_model：recon 资产清单 + 分析师分类层 → ThreatModel。
不含任何实际攻击利用；框架组合为方法论 + 文档 + 许可 AI（矩阵 ⑬），无攻击框架。

Ch10 对齐增量：新增 roe / prior / new_intel 注入参数（设计 §4 S-4/S-5），
构造序扩展但既有四节与质量门语义不变。
"""
from .boundaries import shortest_paths, trust_boundaries
from .classify import (classification_detection_rules, classification_observations,
                       classification_trust_boundaries, enrich)
from .decision import evaluate_gates, go_no_go
from .decoy import judge_decoy
from .graph import build_graph, orchestration_order
from .model import AssetView, AttackPath, DecoyVerdict, ThreatModel, DECOY
from .render import render
from .score import high_value_only, score_and_rank

__all__ = [
    "build_threat_model", "render", "AssetView", "AttackPath", "DecoyVerdict",
    "ThreatModel", "DECOY", "high_value_only", "score_and_rank",
]


def build_threat_model(inventory, classification, now=None, roe=None,
                       prior=None, new_intel=None):
    """构建威胁模型（四节 + Ch10 增量节 + 质量门）。

    参数
      inventory: recon 资产清单（dict 含 assets 或 list），七字段只读消费。
      classification: 分析师分类层 {asset_id: {...}}，另可含顶层键
                      assumptions / detection_rules / trust_boundaries。
      now: 可选注入时钟。roe: 可选 RoE 约束（S-4 规则注入）。
      prior: 可选上一版 ThreatModel（S-5 历史注入）。
      new_intel: 可选增量情报 dict（decision_log / engagement_day / remaining_days）。
    """
    from . import atlas, assumptions, roe as _roe

    assets = enrich(inventory, classification)
    ranked = score_and_rank(assets)

    # 假设登记册（观察 + 检测规则派生）
    regs = assumptions.to_register(classification_observations(classification), classification)
    reg_ids = {a.id for a in regs}
    for derived in assumptions.derive_from_detections(
            classification_detection_rules(classification)):
        if derived.id not in reg_ids:
            regs.append(derived)
    if prior is not None and getattr(prior, "assumptions", None):
        for a in prior.assumptions:
            if a.status == "VALIDATED" and a.id not in {x.id for x in regs}:
                regs.append(a)

    raw_bounds = classification_trust_boundaries(classification)
    bounds = trust_boundaries(assets, raw_bounds)
    tbs = bounds.pop("_trust_boundaries", [])

    paths = shortest_paths(assets, top_n=3, boundaries=tbs, assumptions=regs)
    paths = evaluate_gates(paths, regs)

    decoys = []
    cls = classification if isinstance(classification, dict) else {}
    for a in assets:
        raw = cls.get(a.asset_id, {})
        raw = raw if isinstance(raw, dict) else {}
        if a.score_class == DECOY or raw.get("decoy"):
            decoys.append(judge_decoy(
                a,
                dims=raw.get("decoy_dims"),
                elapsed_minutes=float(raw.get("decoy_elapsed_minutes", 0.0) or 0.0),
                now=now,
                reason=raw.get("decoy_reason", ""),
            ))

    graph = build_graph(assets, paths)
    order = orchestration_order(assets)
    amap = atlas.map_techniques(assets, regs)
    ni = new_intel if isinstance(new_intel, dict) else {}
    matrix = go_no_go(paths, regs, remaining_days=ni.get("remaining_days"))

    target = inventory.get("target", "") if isinstance(inventory, dict) else ""
    revision = (getattr(prior, "revision", 0) or 0) + 1
    decision_log = list(getattr(prior, "decision_log", []) or [])
    if new_intel:
        decision_log.append("v%d: 增量情报 %s" % (
            revision, ni.get("summary", str(new_intel))))
    brief_version = "1.%d" % (revision - 1)

    tm = ThreatModel(
        target=target, high_value=ranked, boundaries=bounds, paths=paths,
        decoys=decoys, graph=graph, order=order,
        assumptions=regs, trust_boundaries=tbs, atlas_map=amap,
        decision_matrix=matrix, report_findings=[],
        revision=revision, decision_log=decision_log,
        brief_version=brief_version, engagement_day=ni.get("engagement_day", 1),
    )
    if roe:
        tm, _ = _roe.apply_roe(tm, roe)
    return tm
