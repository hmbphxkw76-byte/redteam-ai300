#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""emb-03 embedding 反演/重建（SKILL.md 攻击路径 A 第 3 步）。

用法（对齐 SKILL.md）：
  python tools/embed_invert.py --endpoint <EMBED_API> --vec out.vec --topk 50
  python tools/embed_invert.py --text "salary executive package secret" --out-vec out.vec
  python tools/embed_invert.py --vec out.vec --corpus loot/corpus.json

两档能力，输出中 `mode` 如实标注，不混淆：
  - `fixture`（默认，零依赖）：可逆位置加权词袋嵌入的**精确反演**，
    验证反演链路的确定性正确性；
  - `live`（给定 `--endpoint`）：embedding 空间最近邻反查（候选池默认内置夹具语料，
    可用 `--corpus` 指定真实语料），对应调研中的「向量反查」路径；
    完整 vec2text 生成式反演需外部依赖，属核实闸 C-1。

退出码：0 成功；2 入参错误；3 目标不可达。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.attack_embeddings import entry  # noqa: E402
from tools.attack_embeddings.attacks import invert  # noqa: E402
from tools.attack_embeddings.harness import fixture_corpus  # noqa: E402
from tools.attack_embeddings.model import cosine  # noqa: E402


def _topk_candidates(vec, pairs, k):
    """按余弦相似度取 top-k 候选（live 模式最近邻反查）。"""
    scored = [{"id": doc_id, "text": text, "sim": cosine(vec, cand_vec)}
              for doc_id, text, cand_vec in pairs]
    scored.sort(key=lambda x: x["sim"], reverse=True)
    return scored[:max(1, k)]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="emb-03 embedding 反演/重建")
    ap.add_argument("--endpoint", default="", help="embedding 端点（缺省走夹具）")
    ap.add_argument("--vec", default="", help="输入向量文件（JSON 数组）")
    ap.add_argument("--out-vec", default="", help="将 --text 的向量写出到此文件")
    ap.add_argument("--text", default="", help="待嵌入文本（生成向量或夹具反演源）")
    ap.add_argument("--corpus", default="", help="候选语料 JSON {doc_id: text}")
    ap.add_argument("--topk", type=int, default=50)
    ap.add_argument("--model", default="text-embedding-3-small")
    args = ap.parse_args(argv)

    try:
        if args.endpoint:
            from tools.attack_embeddings.live import LiveEmbeddingClient, LiveError
            client = LiveEmbeddingClient(args.endpoint, model=args.model)
            try:
                vec = entry.load_vector(args.vec) if args.vec else client.embed(args.text)
            except LiveError as exc:
                return entry.fail(str(exc), entry.EXIT_UNREACHABLE)
            if args.out_vec:
                entry.save_vector(args.out_vec, vec)
            # 候选池：优先真实语料，缺省内置夹具（如实标注来源）
            pool = ({str(k): str(v) for k, v in entry.load_json(args.corpus).items()}
                    if args.corpus else fixture_corpus())
            pairs = [(doc_id, text, client.embed(text)) for doc_id, text in pool.items()]
            cands = _topk_candidates(vec, pairs, args.topk)
            entry.emit({
                "step": "emb-03", "mode": "live", "target": args.endpoint,
                "verdict": "候选已反查",
                "dim": len(vec),
                "candidate_pool": "corpus" if args.corpus else "builtin-fixture",
                "top_k": cands,
            })
            return entry.EXIT_OK

        # 夹具模式：可逆嵌入的精确反演
        harness = entry.fixture_harness()
        if args.vec:
            vec = entry.load_vector(args.vec)
        elif args.text:
            vec = harness.embed(args.text)
            if args.out_vec:
                entry.save_vector(args.out_vec, vec)
        else:
            return entry.fail("夹具模式需 --vec 或 --text")
        res = invert(vec, harness)
        entry.emit({
            "step": "emb-03", "mode": "fixture", "target": "local-fixture",
            "verdict": "还原成功" if res["confidence"] >= 1.0 else "部分还原",
            "dim": len(vec),
            "recovered_text": res["text"],
            "confidence": round(float(res["confidence"]), 3),
            "recovered_tokens": res["recovered"],
        })
        return entry.EXIT_OK
    except (ValueError, OSError) as exc:
        return entry.fail(str(exc))


if __name__ == "__main__":
    sys.exit(main())
