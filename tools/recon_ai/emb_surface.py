#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch6 侦察侧嵌入面元数据（只读，AC-R1..R4）。

只记录「向量库可导出面 + 维度值（若可得） + RAG probing 入口」，**不推断模型、
不导出向量、不发 probing 查询**（这些属 attack-embeddings，PR #309）。候选模型表、
导出算法、probing 评分均不在此重复实现（C1 单一事实源）。

维度值来源：recon-04 主动面已获取的 `context["dim"]`（若下游探针提供）；缺省记
「不可判定」，绝不臆测（AC-R3）。
"""
from __future__ import annotations

from typing import Dict, Optional

# 常见向量库只读端口（与 probes.py recon-04 端口清单一致，指针引用避免二处漂移）
EXPORT_PORTS = {
    8080: "weaviate", 8000: "chroma", 19530: "milvus", 6333: "qdrant",
}


def build_emb_metadata(category: str, endpoint: str = "",
                       dim: Optional[int] = None,
                       probing_entry: bool = False) -> Dict[str, object]:
    """为向量库/RAG 资产生成可选嵌入面元数据（只读标注）。"""
    if category != "vector_db":
        return {}
    export_surface = any(str(p) in endpoint for p in EXPORT_PORTS)
    return {
        "export_surface": export_surface,
        "dim": dim if dim is not None else "不可判定",
        "dim_candidates": ["不可判定"] if dim is None else ["需下游推断"],
        "probing_entry": probing_entry,
        "note": "侦察侧只读元数据；导出/维度候选推断/probing 执行属 attack-embeddings",
    }
