#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""组件→MITRE ATLAS 技术映射（Ch10 §10.1 Table 6 / A7）。

七 ID 取自课程 Table 6（ATLAS_IDS 唯一集合）；前置假设未高置信确认前标
"applicable if"，仅 VALIDATED 标"立即适用"。纯函数，版本核实走研究阶段取证闸。
"""
from .model import ATLASMap, ATLAS_IDS

# 组件关键词 → (技术名, ID, 前置假设 ID 或 None) —— 七 ID 恰各一次
PATTERNS = (
    ("mlflow", "ML Model Access", "AML.T0044", None),
    ("qdrant_staging", "Poison Training Data", "AML.T0020", "roe_staging_allowed"),
    ("qdrant", "Infer Training Data", "AML.T0025", None),
    ("mcp", "ML-Enabled Product Abuse", "AML.T0048", "agent_token_valid"),
    ("triage", "Craft Adversarial Data", "AML.T0043", "webhook_delivery"),
    ("model_registry", "ML Supply Chain Compromise", "AML.T0010", "mlflow_upload"),
    ("agent", "Inference API Access", "AML.T0040", None),
)


def map_techniques(assets, assumptions):
    """按组件与假设状态生成映射；前置 VALIDATED 才"立即适用"。"""
    by_id = {a.id: a for a in (assumptions or [])}
    result = []
    seen = set()
    for asset in assets or []:
        text = " ".join([getattr(asset, "asset_id", ""),
                         getattr(asset, "product", ""),
                         getattr(asset, "category", "")]).lower()
        for key, technique, tid, pre in PATTERNS:
            if key not in text or tid in seen:
                continue
            # staging 优先于普通 qdrant 命中
            if key == "qdrant" and "staging" in text:
                continue
            pre_ok = True
            if pre:
                a = by_id.get(pre)
                pre_ok = a is not None and a.status == "VALIDATED"
            result.append(ATLASMap(
                component=getattr(asset, "asset_id", ""),
                technique=technique,
                technique_id=tid,
                application=("前置已验证，立即适用" if pre_ok else
                             "前置 %s 未验证，applicable if" % (pre or "—")),
                precondition_id=pre or "",
                immediately_applicable=pre_ok,
            ))
            seen.add(tid)
            break
    # 保证集内全部 ID 出现（缺失的用占位映射，标 applicable if）
    for _key, technique, tid, pre in PATTERNS:
        if tid not in seen:
            result.append(ATLASMap(
                component="（无组件命中）",
                technique=technique,
                technique_id=tid,
                application="组件未确认，applicable if",
                precondition_id=pre or "",
                immediately_applicable=False,
            ))
            seen.add(tid)
    assert set(x.technique_id for x in result) == set(ATLAS_IDS)
    return result
