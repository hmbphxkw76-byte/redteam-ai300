#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 C1 判定 → 七字段资产清单无损映射（AC-08，C1-5）。

只组装字段字典；不改 `Asset`/`ASSET_FIELDS` 契约（P-3）。
"""
from typing import Dict

from .ch9_c1_model import C1Verdict
from .model import ASSET_FIELDS


def to_asset_fields(verdict: C1Verdict, evidence_step: str,
                    category: str = "模型服务", product: str = "model-endpoint") -> Dict[str, str]:
    """产出与 ASSET_FIELDS 完全一致的七字段；credential_hint 只指纹。"""
    fields = {
        "asset_id": "ai-cloud-%s" % (verdict.public_ip or product),
        "category": category,
        "product": product,
        "version": verdict.version,
        "endpoint": (verdict.public_ip or "model-endpoint"),
        "credential_hint": verdict.credential_hint or "(none)",
        "evidence_step": evidence_step,
    }
    if list(fields) != list(ASSET_FIELDS):
        raise ValueError("七字段顺序与 ASSET_FIELDS 不一致")
    return fields
