#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""beam search 结构恢复（Ch6 §6.3 Listing 15，AC-C6）。

课程脚本 zero2text_impl.py 基于 Zero2Text（arXiv:2602.01757v2）做 token-by-token
beam search：语言模型提议候选 token，embedding 模型按余弦评分，保留最优 beam。
课程实现是「论文方法的近似实现」（论文用 recursive online alignment + ridge，
课程用 GPT-2 beam + 可选 ridge 双嵌入）——本模块以确定性夹具给出可测的近似链路，
高熵区检测 + 填槽交给 slotfill，不宣称与论文等价（核实闸 C-5）。
"""
from __future__ import annotations

import re
from typing import Dict, List, Sequence

from .model import cosine
from .harness import EmbeddingHarness

_SLOT_PATTERNS = [
    (re.compile(r"\bsk-[A-Za-z0-9]{8,}"), "API_KEY"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{8,}"), "JWT"),
    (re.compile(r"\b[0-9a-fA-F]{32,}\b"), "HASH"),
]


def detect_high_entropy(text: str, vocab: Sequence[str] | None = None) -> List[Dict[str, str]]:
    """正则 + 字符类多样性检测高熵区（课程 Listing 15 的简化确定性版）。"""
    found = []
    for pat, kind in _SLOT_PATTERNS:
        for m in pat.finditer(text):
            found.append({"kind": kind, "value": m.group(0), "start": m.start(), "end": m.end()})
    # 字符类混合且非常词表的 token
    vocab_set = set(vocab or [])
    for m in re.finditer(r"\b\w*[A-Z]\w*\d+\w*[!@#$%^&*]\w*\b", text):
        tok = m.group(0)
        if tok not in vocab_set:
            found.append({"kind": "PASSWORD", "value": tok,
                          "start": m.start(), "end": m.end()})
    return found


def beam_recover(target: Sequence[float], harness: EmbeddingHarness,
                 vocab: Sequence[str] | None = None,
                 beam_width: int = 5, steps: int = 12) -> Dict[str, object]:
    """确定性 beam search：从词表逐 token 扩展，按余弦保留最优 beam。"""
    vocab = list(vocab or harness.embedder.vocab)
    beams: List[List[str]] = [[]]
    for _ in range(steps):
        candidates = []
        for b in beams:
            for tok in vocab:
                trial = b + [tok]
                sim = cosine(harness.embed(" ".join(trial)), target)
                candidates.append((sim, trial))
        candidates.sort(key=lambda x: x[0], reverse=True)
        beams = [c[1] for c in candidates[:beam_width]]
        if candidates and candidates[0][0] >= 0.999:
            break
    best = beams[0] if beams else []
    text = " ".join(best)
    sim = cosine(harness.embed(text), target) if text else 0.0
    return {"step": "emb-c6", "text": text, "similarity": round(float(sim), 4),
            "high_entropy": detect_high_entropy(text, vocab),
            "dual_embedder": False,
            "note": "课程近似实现（C-5），不宣称与 Zero2Text 论文等价"}
