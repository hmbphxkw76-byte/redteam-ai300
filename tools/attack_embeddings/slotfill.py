#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""填槽式反演（Ch6 §6.3 Listing 11–13，AC-C5）：两阶段恢复高熵字段。

阶段 1：语义结构（模板，高熵值用 {PASSWORD}/{URL} 占位）；
阶段 2：成员推断填槽——对词表逐候选嵌入模板，取与目标向量余弦最高者。
关键改进：margin-aware scoring（相对中性基线，防语义重叠误报）、consensus voting
（多模板投票）、attractor candidates 缓解（定向小词表）。
"""
from __future__ import annotations

from typing import Dict, List, Sequence

from .model import cosine

DEFAULT_TEMPLATES = [
    "The reset password is {PASSWORD}. Please check out {URL} immediately.",
    "Please navigate to {URL} and reset your password to {PASSWORD}.",
    "Login at {URL}. Your temporary password is {PASSWORD} and must be changed.",
    "The default credential {PASSWORD} is set. Visit {URL} to authenticate.",
]


def _margin(candidate: str, slot: str, neutral: str, template: str,
            target: Sequence[float], embed_fn) -> float:
    """margin-aware：候选填入 vs 中性占位填入的相似度增益。"""
    filled = template.replace("{%s}" % slot, candidate)
    base = template.replace("{%s}" % slot, neutral)
    return cosine(embed_fn(filled), target) - cosine(embed_fn(base), target)


def fill_slots(target: Sequence[float], templates: Sequence[str], wordlist: Sequence[str],
               slot: str = "PASSWORD", embed_fn=None,
               harness=None, neutral: str = "XXXXXX",
               consensus_threshold: float = 0.5) -> Dict[str, object]:
    """对目标向量做填槽，返回命中值、票数与置信度。"""
    if embed_fn is None and harness is None:
        raise ValueError("须提供 embed_fn 或 harness 之一（无嵌入能力无法填槽）")
    embed = embed_fn or (lambda t: harness.embed(t))
    templates = list(templates) or DEFAULT_TEMPLATES
    if not wordlist:
        raise ValueError("空词表")

    votes: Dict[str, int] = {}
    margins: Dict[str, float] = {}
    for tpl in templates:
        if "{%s}" % slot not in tpl:
            continue
        best_word, best_margin = None, float("-inf")
        for w in wordlist:
            m = _margin(str(w), slot, neutral, tpl, target, embed)
            if m > best_margin:
                best_word, best_margin = str(w), m
        if best_word is not None:
            votes[best_word] = votes.get(best_word, 0) + 1
            margins[best_word] = max(margins.get(best_word, float("-inf")), best_margin)

    if not votes:
        return {"step": "emb-c5", "value": None, "confidence": "Unlikely",
                "reason": "无匹配模板含该槽位", "votes": 0}
    winner = max(votes, key=lambda w: (votes[w], margins.get(w, 0.0)))
    vote_ratio = votes[winner] / len(templates)
    runner = sorted(votes.values(), reverse=True)
    gap = votes[winner] - (runner[1] if len(runner) > 1 else 0)
    confidence = "Strong" if (vote_ratio >= consensus_threshold and gap >= 2) else (
        "Moderate" if vote_ratio >= consensus_threshold else "Weak")
    return {"step": "emb-c5", "value": winner, "confidence": confidence,
            "votes": votes[winner], "total_templates": len(templates),
            "vote_ratio": round(vote_ratio, 3), "gap": gap,
            "margin": round(float(margins.get(winner, 0.0)), 6),
            "all_votes": votes}


def _main() -> int:
    import argparse
    from . import entry
    from .harness import EmbeddingHarness, DeterministicEmbedder
    ap = argparse.ArgumentParser(description="emb-c5 填槽反演")
    ap.add_argument("--vec", default="")
    ap.add_argument("--wordlist", default="")
    ap.add_argument("--slot", default="PASSWORD")
    args = ap.parse_args()
    try:
        h = EmbeddingHarness(DeterministicEmbedder())
        tpl = "The password is {PASSWORD} today"
        target = h.embed(tpl.replace("{PASSWORD}", "secret"))
        words = ["secret", "salary", "alpha", "beta"]
        if args.wordlist:
            words = [w.strip() for w in open(args.wordlist, encoding="utf-8") if w.strip()][:5000]
        r = fill_slots(target, [tpl], words, args.slot, harness=h, neutral="XXXX")
        r["mode"] = "fixture"
        entry.emit(r)
        return 0
    except (ValueError, OSError) as exc:
        return entry.fail(str(exc))


if __name__ == "__main__":
    import sys
    sys.exit(_main())
