#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S7 决策 seam：方法需求表（Table 1）+ 决策矩阵（Table 2）+ 限制前置门禁（AC-C7/C8）。

来源：Ch6 §6.1 BLOCK 6 Table 1、§6.4 BLOCK 44 Table 2、§6.1 BLOCK 9 五大限制。
"""
from __future__ import annotations

from typing import Dict, List


METHODS = {
    "fixture": {"category": "Zero-Shot", "model_known": True, "gpu": False,
                "target_access": "exported only", "invasiveness": "passive"},
    "emb_fin": {"category": "Zero-Shot", "model_known": True, "gpu": False,
                "target_access": "exported only", "invasiveness": "passive"},
    "zero2text": {"category": "Zero-Shot", "model_known": True, "gpu": True,
                  "target_access": "exported only", "invasiveness": "passive"},
    "ALGEN": {"category": "Few-Shot", "model_known": False, "gpu": True,
              "target_access": "exported+RAG+write", "invasiveness": "active"},
    "Vec2Text": {"category": "Supervised", "model_known": True, "gpu": True,
                 "target_access": "exported only", "invasiveness": "passive"},
}


def check_limits(chunk_tokens: int = 32, quantized: bool = False,
                 domain: str = "enterprise", high_entropy: bool = False,
                 model_known: bool = True) -> Dict[str, object]:
    """五项限制的可行性前置判定（BLOCK 9）。"""
    flags = {
        "token_length": chunk_tokens > 64,
        "quantization": quantized,
        "domain_mismatch": domain not in ("enterprise", "msmarco", "nq"),
        "high_entropy": high_entropy,
        "model_unknown": not model_known,
    }
    feasibility = "low" if (flags["token_length"] or flags["quantization"]) else "ok"
    return {"step": "emb-c8", "flags": flags, "feasibility": feasibility,
            "recoverable": not high_entropy,
            "advice": ("短块（<=64 token）优先；量化/高熵场景改推断探测或标不可恢复"
                       if feasibility == "low" or high_entropy else "可按常规反演")}


def select_method(model_known: bool = True, has_gpu: bool = False,
                  can_write_store: bool = False, has_rag: bool = False,
                  prep_hours: float = 0.0,
                  limits: Dict[str, object] | None = None) -> Dict[str, object]:
    """Table 2 决策路径：时间紧默认 fixture/emb_fin；未知模型→ALGEN 或不适用。"""
    limits = limits or {}
    flags = limits.get("flags", {})
    if not model_known:
        if can_write_store and has_rag:
            return {"step": "emb-c7", "method": "ALGEN", "reason": "模型未知且可注入 canary + RAG probing",
                    "env_dependent": True}
        return {"step": "emb-c7", "method": "ALGEN", "reason": "模型未知但无写权限/RAG；环境不适用（C-1）",
                "env_dependent": True, "not_applicable": True}
    # 模型已知
    if prep_hours >= 60 and has_gpu and flags.get("token_length") is False:
        return {"step": "emb-c7", "method": "Vec2Text", "reason": "提前已知模型 + 充足准备 + GPU",
                "env_dependent": True}
    if flags.get("template_low_confidence"):
        return {"step": "emb-c7", "method": "zero2text", "reason": "模板相似度低/置信弱，beam 恢复结构",
                "env_dependent": has_gpu is False}
    return {"step": "emb-c7", "method": "fixture", "reason": "模型已知、CPU 可行、时间紧默认起步",
            "env_dependent": False}
