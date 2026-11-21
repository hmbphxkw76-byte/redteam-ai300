#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P2-6：检索模式 / 追踪面归类（Ch5 §5.1 图2/3、C-1/C-2）。

把 recon-ai 清单或合成面的字段归类为 enterprise/synthetic 检索模式与
混合检索/追踪能力；缺字段标「不可判定」，不把产品文档当运行时事实。
"""
from typing import Any, Dict

UNKNOWN = "不可判定"


def from_surface(surface: Any = None) -> Dict[str, str]:
    """从 RagSurface（或 dict）归类检索模式与追踪面。"""
    d: Dict[str, Any]
    if surface is None:
        d = {}
    elif isinstance(surface, dict):
        d = surface
    else:
        d = getattr(surface, "as_dict", lambda: {})()
    vector_db = str(d.get("vector_db") or "")
    source = str(d.get("source") or "")
    retrieval = str(d.get("retrieval") or "")
    mode = "synthetic" if "synthetic" in source.lower() or "harness" in vector_db.lower() else (
        "enterprise" if vector_db else UNKNOWN)
    tracing = d.get("tracing")
    if tracing is None:
        tracing = "Phoenix 追踪" if _mentions_phoenix(retrieval, vector_db) else UNKNOWN
    return {
        "source": source or UNKNOWN,
        "retrieval_mode": mode,
        "hybrid": "混合检索（BM25 + 向量融合）" if mode == "enterprise" else UNKNOWN,
        "tracing": str(tracing),
    }


def _mentions_phoenix(*fields: str) -> bool:
    return any("phoenix" in str(f).lower() for f in fields)


def render(data: Dict[str, str]) -> str:
    return ("来源: %s\n检索模式: %s\n检索类型: %s\n追踪面: %s"
            % (data.get("source", UNKNOWN), data.get("retrieval_mode", UNKNOWN),
               data.get("hybrid", UNKNOWN), data.get("tracing", UNKNOWN)))
