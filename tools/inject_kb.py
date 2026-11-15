#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路径 A 第 1 步的注入脚本（SKILL.md 点名命令的等价实现）。

SKILL.md 原文：
  `python inject_kb.py --target <VECTOR_DB> --doc ./malicious_doc.txt`
  （注入脚本仅作示意，**须记录来源**）

本脚本因此强制打印来源指纹（路径 + sha256 + 字节数），并按可用写入面
自动选通道：
  --ingest-url <RAG_INGEST>  内容摄取 API（`curl -X POST` 等价）
  --store <corpus.jsonl>     向量库/语料直写（已立足点）
  缺省                        合成 harness（离线复现，打印 top-k 命中）

退出码：0 已落库；2 入参错误；3 未落库（通道拒绝/不可达/未进 top-k）。
"""
import argparse
import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.attack_rag.harness import RagHarness, default_corpus  # noqa: E402
from tools.attack_rag.ingest import (FileIngestChannel,  # noqa: E402
                                     HttpIngestChannel, read_doc)
from tools.attack_rag.poisoned_rag import PoisonedRAGInjector  # noqa: E402


def provenance(path, text):
    """来源记录：路径 + sha256 + 字节数（SKILL.md「须记录来源」）。"""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return "来源: %s\nsha256: %s\n字节数: %d" % (
        os.path.abspath(path), digest, len(text.encode("utf-8")))


def main(argv=None):
    ap = argparse.ArgumentParser(description="RAG 知识库注入（attack-rag 路径 A 第 1 步）")
    ap.add_argument("--target", required=True, help="向量库/摄取面标识（进证据与报告）")
    ap.add_argument("--doc", required=True, help="待注入文档路径")
    ap.add_argument("--ingest-url", default="", help="内容摄取端点（HTTP POST）")
    ap.add_argument("--store", default="", help="向量库/语料直写路径（JSONL）")
    ap.add_argument("--query", default="", help="合成面校验用的目标查询")
    ap.add_argument("--answer", default="", help="合成面构造答案（条件 2）")
    ap.add_argument("--instruction", default="", help="合成面内嵌指令（路径 B 载荷）")
    ap.add_argument("--corpus-size", type=int, default=1200, help="合成语料规模")
    ap.add_argument("--k", type=int, default=3, help="top-k")
    args = ap.parse_args(argv)

    try:
        text = read_doc(args.doc)
    except ValueError as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2

    print("目标: %s" % args.target)
    print(provenance(args.doc, text))
    if args.ingest_url:
        result = HttpIngestChannel(args.ingest_url).put("mal-0000", text)
        print(result.render())
        return 0 if result.delivered else 3
    if args.store:
        result = FileIngestChannel(args.store).put("0000", text)
        print(result.render())
        return 0 if result.delivered else 3

    injector = PoisonedRAGInjector()
    if args.query:  # 按 PoisonedRAG 前置问题法扩写 5 篇，再连同原文一并注入
        docs = [text] + injector.blackbox(args.query, args.answer or "复用管理员凭据",
                                        args.instruction)
    else:
        docs = [text]
    harness = RagHarness(default_corpus(args.corpus_size), k=args.k)
    ids = injector.inject(harness, docs)
    query = args.query or "重置密码流程"
    hit = injector.hit(harness, query)
    print("通道: synthetic-harness（离线）\n注入 doc_id: %s\ntop_k: [%s]\n命中: %s"
          % (", ".join(ids), ", ".join(harness.snapshot(query)), hit))
    return 0 if hit else 3


if __name__ == "__main__":
    sys.exit(main())
