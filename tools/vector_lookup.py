#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""emb-06 知识库内容提取（向量库反查，SKILL.md 攻击路径 B 第 6 步）。

用法（对齐 SKILL.md）：
  python tools/vector_lookup.py --store <VECTOR_DB> --query "<target concept>" --topk 50
  python tools/vector_lookup.py --query "salary executive" --corpus loot/corpus.json

`--store` 为 HTTP 暴露的向量库检索端点（`live` 模式）；缺省走内存夹具（`fixture` 模式）。
与 `attack-rag` 共享同一向量面，语料可用 `--corpus` 指定真实知识库导出。

退出码：0 成功；2 入参错误；3 目标不可达。
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.attack_embeddings import entry  # noqa: E402
from tools.attack_embeddings.attacks import vector_lookup  # noqa: E402


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="emb-06 向量库反查（知识库内容提取）")
    ap.add_argument("--store", default="", help="向量库检索端点（缺省走内存夹具）")
    ap.add_argument("--query", required=True, help="反查概念/查询文本")
    ap.add_argument("--corpus", default="", help="知识库语料 JSON {doc_id: text}")
    ap.add_argument("--topk", type=int, default=50)
    ap.add_argument("--model", default="text-embedding-3-small")
    args = ap.parse_args(argv)

    if not (args.query or "").strip():
        return entry.fail("--query 不能为空")
    if args.topk <= 0:
        return entry.fail("--topk 必须为正整数")

    try:
        if args.store:
            from tools.attack_embeddings.live import LiveError, LiveVectorStoreClient
            client = LiveVectorStoreClient(args.store)
            try:
                hits = (client.query_text(args.query, args.topk)
                        if not args.corpus
                        else _query_with_embedder(args, client))
            except LiveError as exc:
                return entry.fail(str(exc), entry.EXIT_UNREACHABLE)
            _report("live", args.store, args.query, hits, args.topk)
            return entry.EXIT_OK

        harness = entry.harness_from_corpus_file(args.corpus or None)
        hits = vector_lookup(args.query, harness, k=args.topk)
        _report("fixture", "local-fixture", args.query, hits, args.topk)
        return entry.EXIT_OK
    except (ValueError, OSError) as exc:
        return entry.fail(str(exc))


def _query_with_embedder(args, store_client):
    """语料与真实向量库分离时：先取查询向量再按向量检索。"""
    from tools.attack_embeddings.live import LiveEmbeddingClient
    embedder_url = os.environ.get("EMBED_API", "")
    if not embedder_url:
        raise ValueError("同时给定 --store 与 --corpus 时需设置 EMBED_API 以取得查询向量")
    vec = LiveEmbeddingClient(embedder_url, model=args.model).embed(args.query)
    return store_client.query_vector(vec, args.topk)


def _report(mode, target, query, hits, topk) -> None:
    entry.emit({
        "step": "emb-06", "mode": mode, "target": target,
        "verdict": "反查命中" if hits else "反查空结果",
        "query": query,
        "topk": topk,
        "hit_count": len(hits),
        "hits": hits,
    })


if __name__ == "__main__":
    sys.exit(main())
