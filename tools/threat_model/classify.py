#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""分类覆盖层：recon 七字段清单 + 分析师分类层 → 富化资产视图。

recon 资产清单不含计分分类/攻击面/信任域/可达性（见 docs/research/
threat-model-canonical.md §4），故由本层合并分析师标注。信号不足记「不可判定」，不臆测。
"""
from .model import AssetView, SCORE_TABLE, UNKNOWN


def _inventory_assets(inventory):
    """兼容 dict（含 assets）与 list 两种清单形态。"""
    if isinstance(inventory, dict):
        return inventory.get("assets", []) or []
    return inventory or []


def enrich(inventory, classification):
    """合并 recon 资产与分类覆盖层，返回 AssetView 列表。

    分类层缺失某资产时，score_class 记「不可判定」（沿用 recon 三值习惯）。
    """
    classification = classification or {}
    views = []
    for a in _inventory_assets(inventory):
        aid = a.get("asset_id") or a.get("assetID") or ""
        raw = classification.get(aid, {})
        c = raw if isinstance(raw, dict) else {}
        sc = c.get("score_class", UNKNOWN)
        if sc not in SCORE_TABLE:
            sc = UNKNOWN
        views.append(AssetView(
            asset_id=aid,
            category=a.get("category", ""),
            product=a.get("product", ""),
            version=a.get("version", ""),
            endpoint=a.get("endpoint", ""),
            credential_hint=a.get("credential_hint", ""),
            evidence_step=a.get("evidence_step", ""),
            score_class=sc,
            attack_surface=c.get("attack_surface", ""),
            trust_zone=c.get("trust_zone", "") or "未分类",
            reachable=bool(c.get("reachable", True)),
            foothold_required=bool(c.get("foothold_required", False)),
            depends_on=list(c.get("depends_on", []) or []),
            # Ch10 增量（recon 七字段不变，走分类覆盖层承载）
            observations=list(c.get("observations", []) or []),
            offensive_value=c.get("offensive_value", "") or "",
            access_status=c.get("access_status", "") or "",
            path_gates=list(c.get("path_gates", []) or []),
            detection_risk=c.get("detection_risk", "") or "",
        ))
    return views


def classification_observations(classification):
    """从分类层提取全局观察/假设条目（不挂在任何单一资产上）。"""
    cls = classification or {}
    if isinstance(cls, dict):
        return list(cls.get("assumptions", []) or [])
    return []


def classification_detection_rules(classification):
    """从分类层提取检测规则（Ch10 Listing 7）。"""
    cls = classification or {}
    if isinstance(cls, dict):
        return list(cls.get("detection_rules", []) or [])
    return []


def classification_trust_boundaries(classification):
    """从分类层提取信任边界五要素列表（Ch10 Table 8）。"""
    cls = classification or {}
    if isinstance(cls, dict):
        return list(cls.get("trust_boundaries", []) or [])
    return []
