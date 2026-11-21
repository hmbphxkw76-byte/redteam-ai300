#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""chunk triage（Ch6 §6.2 Listing 9，AC-C4）：三级级联分选 + 加权 RRF。

三阶段：Density（主题隔离 + credential 探针相关）→ Contrastive Pairwise（正负探针
净敏感）→ Reconstruction（浅反演 + 凭证指标）；加权 RRF 权重 1.0/1.5/2.0。
全程在 embedding 空间工作，不先做完整反演。
"""
from __future__ import annotations

from typing import Dict, List, Sequence

from .attacks import invert
from .harness import EmbeddingHarness
from .model import cosine

RRF_WEIGHTS = {"density": 1.0, "pw": 1.5, "recon": 2.0}
DEFAULT_SENSITIVITY_PROBES = [
    "password reset credentials login",
    "api key secret token authentication",
    "ssh private key passphrase",
    "database connection string admin",
]


def _rrf(rankings: Sequence[Sequence[int]], weights: Sequence[float],
         k: int = 60) -> Dict[int, float]:
    """加权 Reciprocal Rank Fusion：按名次而非原始分数融合。"""
    scores: Dict[int, float] = {}
    for ranking, w in zip(rankings, weights):
        for rank, idx in enumerate(ranking, start=1):
            scores[idx] = scores.get(idx, 0.0) + w / (k + rank)
    return scores


def triage_chunks(harness: EmbeddingHarness,
                  top_density: int = 50, top_pw: int = 20,
                  probes: Sequence[str] | None = None) -> Dict[str, object]:
    """返回按加权 RRF 排序的高价值块清单（含原始 chunk 索引）。"""
    docs = harness.store.all()
    n = len(docs)
    if n == 0:
        return {"step": "emb-c4", "results": [], "stages": []}
    probes = list(probes or DEFAULT_SENSITIVITY_PROBES)
    probe_vecs = [harness.embed(p) for p in probes]

    # Stage 1 Density：kNN 隔离度 + 探针相关性
    density = []
    for i, d in enumerate(docs):
        sims = sorted((cosine(d["vec"], o["vec"]) for j, o in enumerate(docs) if j != i),
                      reverse=True)
        isolation = 1.0 - (sum(sims[:3]) / len(sims[:3]) if sims else 0.0)
        relevance = max((cosine(d["vec"], pv) for pv in probe_vecs), default=0.0)
        density.append((i, 0.5 * isolation + 0.5 * relevance))
    d_ranked = [i for i, _ in sorted(density, key=lambda x: x[1], reverse=True)][:top_density]

    # Stage 2 Contrastive Pairwise：正负探针净值（benign 作为负探针）
    neg_probes = ["company policy employee handbook", "meeting notes project update"]
    neg_vecs = [harness.embed(p) for p in neg_probes]
    pw = []
    for i in d_ranked:
        pos = max((cosine(docs[i]["vec"], pv) for pv in probe_vecs), default=0.0)
        neg = max((cosine(docs[i]["vec"], nv) for nv in neg_vecs), default=0.0)
        pw.append((i, pos - neg))
    pw_ranked = [i for i, _ in sorted(pw, key=lambda x: x[1], reverse=True)][:top_pw]

    # Stage 3 Reconstruction：浅反演 + 凭证指标（正则/熵/字符类）
    recon = []
    for i in pw_ranked:
        txt = invert(docs[i]["vec"], harness)["text"]
        has_cred = any(t in txt.lower() for t in ("password", "secret", "token", "key"))
        entropy_like = len(set(txt)) / max(len(txt), 1)
        recon.append((i, (1.0 if has_cred else 0.0) + entropy_like))
    recon_ranked = [i for i, _ in sorted(recon, key=lambda x: x[1], reverse=True)]

    # 加权 RRF；未进入后续阶段的块在该阶段名次靠后（惩罚）
    full = list(range(n))
    fused = _rrf([full, d_ranked, pw_ranked, recon_ranked],
                 [0.0, RRF_WEIGHTS["density"], RRF_WEIGHTS["pw"], RRF_WEIGHTS["recon"]])
    ordered = sorted(fused, key=lambda idx: fused[idx], reverse=True)
    results = []
    for rank, idx in enumerate(ordered, start=1):
        results.append({"rank": rank, "chunk_index": idx,
                        "fused": round(fused[idx], 6),
                        "in_density": idx in d_ranked,
                        "in_pw": idx in pw_ranked,
                        "in_recon": idx in recon_ranked})
    return {"step": "emb-c4", "results": results,
            "stages": {"density": len(d_ranked), "pw": len(pw_ranked),
                       "recon": len(recon_ranked)},
            "weights": RRF_WEIGHTS}
