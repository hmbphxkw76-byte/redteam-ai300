#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""维度指纹（Ch6 §6.2 Listing 5–7，AC-C2）：维度 → 候选 embedding 模型。

课程原文约束："many models share the same dimensions, therefore we can only use
this as a first indication" —— 共享维度时输出候选列表，绝不下唯一结论。
"""
from __future__ import annotations

from typing import Dict, List

# 课程 Listing 7 的常见模型维度对照表（一手源：Ch6 §6.2）
DIM_CATALOG: Dict[int, List[str]] = {
    384: [
        "sentence-transformers/all-MiniLM-L6-v2",
        "sentence-transformers/paraphrase-MiniLM-L6-v2",
        "intfloat/e5-small-v2",
        "BAAI/bge-small-en-v1.5",
        "thenlper/gte-small",
    ],
    768: ["BGE-base", "sentence-transformers/all-MiniLM-L12-v2"],
    1024: ["Cohere embed-english-v3.0"],
    1536: ["OpenAI text-embedding-ada-002", "OpenAI text-embedding-3-small"],
    3072: ["OpenAI text-embedding-3-large"],
}


def candidates_for_dim(dim: int, catalog: Dict[int, List[str]] | None = None) -> Dict[str, object]:
    """返回维度对应的候选模型列表；共享维度时 ``unique=False``。"""
    cat = catalog or DIM_CATALOG
    models = list(cat.get(dim, []))
    return {
        "step": "emb-c2",
        "dimension": dim,
        "candidates": models,
        "count": len(models),
        "unique": len(models) == 1,
        "needs_confirmation": len(models) != 1,
        "note": "维度仅为初步指示；共享维度须经推断探测确认" if len(models) != 1 else "唯一候选（仍需实证）",
    }
