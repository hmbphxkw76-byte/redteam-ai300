#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""emb-04 成员推断（SKILL.md 攻击路径 A 第 4 步）。

用法（对齐 SKILL.md）：
  python tools/membership_inference.py --endpoint <EMBED_API> --sample suspect.txt
  python tools/membership_inference.py --sample "salary executive package secret"
  python tools/membership_inference.py --sample suspect.txt --members m.json --nonmembers n.json

判据：最近邻相似度 ≥ `--threshold` 判为「在集」；并用 embedding 空间高斯噪声
（`--noise`，Noisy Neighbors）的余弦稳定性作佐证。给定标注集时额外报告 AUC。

退出码：0 成功；2 入参错误；3 目标不可达。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.attack_embeddings import entry  # noqa: E402
from tools.attack_embeddings.attacks import (  # noqa: E402
    membership_auc, membership_inference)

_EXIT_LIVE = 3


def _read_sample(value: str) -> str:
    """`--sample` 可为文本，或指向文件的路径。"""
    if os.path.isfile(value):
        with open(value, encoding="utf-8") as f:
            return f.read().strip()
    return value.strip()


def _read_list(value: str):
    data = entry.load_json(value)
    if not isinstance(data, list):
        raise ValueError("标注集须为 JSON 字符串数组")
    return [str(x) for x in data]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="emb-04 成员推断")
    ap.add_argument("--endpoint", default="", help="embedding 端点（缺省走夹具）")
    ap.add_argument("--sample", required=True, help="待判定样本（文本或文件路径）")
    ap.add_argument("--corpus", default="", help="检索集语料 JSON {doc_id: text}")
    ap.add_argument("--noise", type=float, default=0.01, help="Noisy Neighbors 高斯噪声 σ")
    ap.add_argument("--threshold", type=float, default=0.98, help="判为在集的相似度阈值")
    ap.add_argument("--members", default="", help="标注成员集 JSON 数组（算 AUC）")
    ap.add_argument("--nonmembers", default="", help="标注非成员集 JSON 数组（算 AUC）")
    ap.add_argument("--model", default="text-embedding-3-small")
    args = ap.parse_args(argv)

    try:
        sample = _read_sample(args.sample)
        if not sample:
            return entry.fail("样本为空")
        if args.endpoint:
            return _run_live(args, sample)
        harness = entry.harness_from_corpus_file(args.corpus or None)
        res = membership_inference(sample, harness, noise=args.noise,
                                   threshold=args.threshold)
        payload = {
            "step": "emb-04", "mode": "fixture", "target": "local-fixture",
            "verdict": "在集" if res["member"] else "非在集",
            "sample": sample,
            "score": round(float(res["score"]), 4),
            "stability": round(float(res["stability"]), 6),
            "threshold": args.threshold,
            "noise_sigma": args.noise,
        }
        if args.members and args.nonmembers:
            payload["auc"] = round(membership_auc(_read_list(args.members),
                                                  _read_list(args.nonmembers),
                                                  harness), 4)
        entry.emit(payload)
        return entry.EXIT_OK
    except (ValueError, OSError) as exc:
        return entry.fail(str(exc))


def _run_live(args, sample: str) -> int:
    """真实端点：用端点向量对候选池做最近邻判定（不静默降级）。"""
    from tools.attack_embeddings.harness import fixture_corpus
    from tools.attack_embeddings.live import LiveEmbeddingClient, LiveError
    from tools.attack_embeddings.model import cosine

    client = LiveEmbeddingClient(args.endpoint, model=args.model)
    try:
        vec = client.embed(sample)
        pool = ({str(k): str(v) for k, v in entry.load_json(args.corpus).items()}
                if args.corpus else fixture_corpus())
        scored = [{"id": k, "text": v, "sim": cosine(vec, client.embed(v))}
                  for k, v in pool.items()]
    except LiveError as exc:
        return entry.fail(str(exc), _EXIT_LIVE)
    scored.sort(key=lambda x: x["sim"], reverse=True)
    best = scored[0] if scored else {"id": "", "text": "", "sim": 0.0}
    entry.emit({
        "step": "emb-04", "mode": "live", "target": args.endpoint,
        "verdict": "在集" if best["sim"] >= args.threshold else "非在集",
        "sample": sample,
        "score": round(float(best["sim"]), 4),
        "nearest": best["id"],
        "threshold": args.threshold,
        "candidate_pool": "corpus" if args.corpus else "builtin-fixture",
    })
    return entry.EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
