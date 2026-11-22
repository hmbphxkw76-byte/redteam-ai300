#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch6 侦察侧嵌入面元数据（只读，AC-R1..R4）。

只记录「向量库可导出面 + 维度值（若可得） + RAG probing 入口」，**不推断模型、
不导出向量、不发 probing 查询**（这些属 attack-embeddings，PR #309）。候选模型表、
导出算法、probing 评分均不在此重复实现（C1 单一事实源）。

端口来源：直接复用 `probes.STEP_SPECS` recon-04 的 active_requests（C1 单一事实源），
不复制端口数字。维度值来源：`context["dim"]`（若探针回写）；缺省「不可判定」，绝不臆测。
"""
from __future__ import annotations

from typing import Dict, Optional

from .probes import _port_list


def _vector_ports():
    """从 recon-04 声明取端口（唯一事实源，复用 probes._port_list）。"""
    return set(p for p in _port_list().split("/") if p.isdigit())


def build_emb_metadata(category: str, endpoint: str = "",
                       dim: Optional[int] = None,
                       probing_entry: bool = False) -> Dict[str, object]:
    """为向量库/RAG 资产生成可选嵌入面元数据（只读标注）。

    - ``category`` 接受 ``Category.*.name``（"VECTOR_DB"/"RAG"）或其小写/中文值。
    """
    cat = str(category).upper()
    is_vector = cat in ("VECTOR_DB", "VECTORDB", "向量库", "VECTOR DB")
    is_rag = cat in ("RAG", "RAG库", "RAG LIBRARY")
    if not (is_vector or is_rag):
        return {}
    ports = _vector_ports()
    export_surface = any((":" + p) in endpoint for p in ports) if ports else bool(endpoint)
    meta: Dict[str, object] = {"export_surface": export_surface}
    if is_vector:
        meta["dim"] = dim if dim is not None else "不可判定"
        meta["dim_candidates"] = ["不可判定"] if dim is None else ["需下游推断"]
    else:
        meta["probing_entry"] = probing_entry
    meta["note"] = "侦察侧只读元数据；导出/候选推断/probing 执行属 attack-embeddings"
    return meta
