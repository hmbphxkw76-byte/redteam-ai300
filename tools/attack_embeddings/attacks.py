#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""攻击原语（阶段 6 seam：反演 S1 / 检索 S2 / 编排 S4 的纯逻辑部分）。

五类原语，均对 `harness` 注入依赖、返回结构化 dict，便于单测与证据落盘：
  - `invert`                —— embedding 反演/重建（vec2text 语义的确定性替身）
  - `membership_inference`  —— 成员推断（Noisy Neighbors + 最近邻判据）
  - `adversarial_shift`     —— 对抗样本（梯度自由爬山扰动）
  - `vector_lookup`         —— 向量库反查（越权/外泄面）
  - `rag_impact`            —— 下游 RAG/检索影响（baseline vs manipulated）
"""
import random
from typing import Dict, List, Optional

from .harness import EmbeddingHarness
from .model import cosine


def invert(vec: List[float], harness: EmbeddingHarness) -> Dict[str, object]:
    """从 embedding 近似还原文本；返回 {text, confidence, recovered}。

    可逆条件：token 在词表内且不重复（夹具约束）。未知槽位不计入还原。
    """
    if not vec:
        raise ValueError("空向量无法反演")
    vocab = harness.embedder.vocab
    pairs = []
    known = 0
    for slot, val in enumerate(vec):
        if val > 0 and slot < len(vocab):
            pos = int(round(val)) - 1
            if pos >= 0:
                pairs.append((pos, vocab[slot]))
                known += 1
    pairs.sort()
    text = " ".join(t for _, t in pairs)
    total = sum(1 for v in vec if v > 0) or 1
    return {"text": text, "confidence": known / total, "recovered": known}


def membership_inference(sample: str, harness: EmbeddingHarness,
                         noise: float = 0.01, seed: int = 0,
                         threshold: float = 0.98) -> Dict[str, object]:
    """成员推断：最近邻相似度（判据）+ 噪声邻居稳定性（Noisy Neighbors 佐证）。

    返回 {member, score, stability}。
    """
    if not (sample or "").strip():
        raise ValueError("空样本无法做成员推断")
    if noise <= 0:
        noise = 0.01
    hits = harness.retrieve(sample, k=1)
    score = hits[0]["sim"] if hits else 0.0
    # Noisy Neighbors：embedding 空间加高斯噪声后的稳定性（越稳越像在集样本）
    base = harness.embed(sample)
    rng = random.Random(seed)
    noisy = [x + rng.gauss(0.0, noise) for x in base]
    stability = cosine(base, noisy)
    return {"member": score >= threshold, "score": score, "stability": stability}


def _auc(pos: List[float], neg: List[float]) -> float:
    """秩和法 AUC；无正/负样本时返回 0.0。"""
    if not pos or not neg:
        return 0.0
    wins = 0.0
    for p in pos:
        for n in neg:
            if p > n:
                wins += 1.0
            elif p == n:
                wins += 0.5
    return wins / (len(pos) * len(neg))


def membership_auc(members: List[str], nonmembers: List[str],
                   harness: EmbeddingHarness) -> float:
    """对标注集计算成员推断 AUC（用于 AC-4 判据）。"""
    pos = [membership_inference(s, harness)["score"] for s in members]
    neg = [membership_inference(s, harness)["score"] for s in nonmembers]
    return _auc(pos, neg)


def adversarial_shift(text: str, target_text: str, harness: EmbeddingHarness,
                      passes: int = 4) -> Dict[str, object]:
    """梯度自由爬山：逐位替换 token 使 embedding 逼近目标；返回 before/after/delta。"""
    target_vec = harness.embed(target_text)
    cur = (text or "").split()
    if not cur:
        raise ValueError("空文本无法做对抗扰动")
    before = cosine(harness.embed(" ".join(cur)), target_vec)
    vocab = harness.embedder.vocab
    best = list(cur)
    for _ in range(max(1, passes)):
        for pos in range(len(best)):
            best_tok, best_sim = best[pos], cosine(harness.embed(" ".join(best)), target_vec)
            for cand in vocab:
                trial = list(best)
                trial[pos] = cand
                sim = cosine(harness.embed(" ".join(trial)), target_vec)
                if sim > best_sim + 1e-9:
                    best_tok, best_sim = cand, sim
            best[pos] = best_tok
    after = cosine(harness.embed(" ".join(best)), target_vec)
    return {"text": " ".join(best), "before": before, "after": after,
            "delta": after - before, "changed": " ".join(best) != " ".join(cur)}


def vector_lookup(concept: str, harness: EmbeddingHarness, k: int = 5) -> List[Dict[str, object]]:
    """向量库反查：返回 top-k 文档块（id/sim/text）。store 空时返回 []。"""
    if k <= 0:
        raise ValueError("k 必须为正整数")
    if len(harness.store) == 0:
        return []
    return harness.retrieve(concept, k)


class FakeRagTarget:
    """确定性生成桩（emb-07 编排 seam S4 的零依赖替身）。

    真实实现为 PyRIT `OpenAIChatTarget`（延迟导入，见 `rag_target()`）；
    本桩按检索上下文是否含 poison 标记返回不同答案，用于确定性断言。
    """

    def generate(self, query: str, docs: List[Dict[str, object]]) -> str:
        ids = ",".join(str(d["id"]) for d in docs)
        poisoned = any("poison" in str(d["text"]) for d in docs)
        verdict = "MANIPULATED" if poisoned else "BASELINE"
        return "q=%s ctx=%s -> %s" % (query, ids, verdict)


def rag_impact(query: str, harness: EmbeddingHarness, poisoned_doc: str,
               target, k: int = 3) -> Dict[str, object]:
    """对比注入前后检索结果与生成结论，判定下游 RAG 是否被影响。"""
    from .harness import EmbeddingHarness as _H, InMemoryVectorStore  # 局部避免环
    base_hits = harness.retrieve(query, k) if len(harness.store) else []
    base_ids = [h["id"] for h in base_hits]

    # 复制一份加毒，避免污染原 harness
    aug = _H(embedder=harness.embedder, store=InMemoryVectorStore())
    for d in harness.store.all():
        aug.store.add(d["id"], d["vec"], d["text"])
    aug.store.add("poison-1", aug.embed(poisoned_doc), poisoned_doc)
    manip_hits = aug.retrieve(query, k)
    manip_ids = [h["id"] for h in manip_hits]

    answer = target.generate(query, manip_hits)
    changed = (base_ids != manip_ids) or ("poison-1" in manip_ids) or ("MANIPULATED" in answer)
    return {"baseline_ids": base_ids, "manipulated_ids": manip_ids,
            "changed": changed, "answer": answer,
            "ai_log_path": "loot/emb-07-rag-impact.md"}
