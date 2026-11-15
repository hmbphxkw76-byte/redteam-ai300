#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""emb-05 对抗样本（SKILL.md 攻击路径 B 第 5 步）。

用法（对齐 SKILL.md）：
  python tools/adv_embed.py --endpoint <EMBED_API> --text "benign" --eps 0.01
  python tools/adv_embed.py --text "benign" --target-text "salary executive package secret"

扰动策略：梯度自由逐位 token 爬山（HotFlip 语义的零依赖替身），使输入 embedding
逼近 `--target-text` 的 embedding；`--eps` 为判定「有效扰动」的最小相似度增量。

退出码：0 成功（含 delta 未达 eps 的情形，如实标注）；2 入参错误；3 目标不可达。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.attack_embeddings import entry  # noqa: E402
from tools.attack_embeddings.attacks import adversarial_shift  # noqa: E402
from tools.attack_embeddings.model import cosine  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="emb-05 对抗样本（扰动改变 embedding/检索）")
    ap.add_argument("--endpoint", default="", help="embedding 端点（缺省走夹具）")
    ap.add_argument("--text", required=True, help="原始输入")
    ap.add_argument("--target-text", default="", help="期望逼近的目标文本")
    ap.add_argument("--eps", type=float, default=0.01, help="有效扰动的最小相似度增量")
    ap.add_argument("--passes", type=int, default=4, help="爬山轮数")
    ap.add_argument("--model", default="text-embedding-3-small")
    args = ap.parse_args(argv)

    if not (args.text or "").strip():
        return entry.fail("--text 不能为空")
    target = args.target_text.strip() or "poison target query chunk"
    try:
        if args.endpoint:
            return _run_live(args, target)
        harness = entry.fixture_harness()
        res = adversarial_shift(args.text, target, harness, passes=args.passes)
        delta = float(res["delta"])
        entry.emit({
            "step": "emb-05", "mode": "fixture", "target": "local-fixture",
            "verdict": "扰动有效" if delta >= args.eps else "扰动不足",
            "original": args.text,
            "perturbed": res["text"],
            "target_text": target,
            "before": round(float(res["before"]), 4),
            "after": round(float(res["after"]), 4),
            "delta": round(delta, 4),
            "eps": args.eps,
            "token_changed": bool(res["changed"]),
        })
        return entry.EXIT_OK
    except (ValueError, OSError) as exc:
        return entry.fail(str(exc))


def _run_live(args, target: str) -> int:
    """真实端点：逐位 token 贪心替换（受 --passes 限制的查询预算）。"""
    from tools.attack_embeddings.harness import default_vocab
    from tools.attack_embeddings.live import LiveEmbeddingClient, LiveError

    client = LiveEmbeddingClient(args.endpoint, model=args.model)
    try:
        tvec = client.embed(target)
        cur = args.text.split()
        before = cosine(client.embed(args.text), tvec)
        best = list(cur)
        for _ in range(max(1, args.passes)):
            improved = False
            for pos in range(len(best)):
                base_sim = cosine(client.embed(" ".join(best)), tvec)
                for cand in default_vocab():
                    trial = list(best)
                    trial[pos] = cand
                    sim = cosine(client.embed(" ".join(trial)), tvec)
                    if sim > base_sim + 1e-9:
                        best, improved = trial, True
            if not improved:
                break
        after = cosine(client.embed(" ".join(best)), tvec)
    except LiveError as exc:
        return entry.fail(str(exc), entry.EXIT_UNREACHABLE)
    delta = after - before
    entry.emit({
        "step": "emb-05", "mode": "live", "target": args.endpoint,
        "verdict": "扰动有效" if delta >= args.eps else "扰动不足",
        "original": args.text, "perturbed": " ".join(best), "target_text": target,
        "before": round(before, 4), "after": round(after, 4),
        "delta": round(delta, 4), "eps": args.eps,
        "token_changed": best != cur,
    })
    return entry.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
