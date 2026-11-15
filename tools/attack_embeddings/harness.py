#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地合成 embedding 夹具（阶段 6 seam S2）。

提供三件确定性构件，使反演/成员推断/对抗/向量库反查/下游影响在**零外部依赖**下可跑：
  - `DeterministicEmbedder`：位置加权词袋嵌入，可逆（已知词表 + 词不重复）；
  - `InMemoryVectorStore`：余弦 top-k 内存向量库；
  - `EmbeddingHarness`：embedder + store + 检索器，作为所有路径的验证面。

真实 embedder（如 `text-embedding-3-small`）与真实向量库（FAISS/Chroma/pgvector）
可替换本夹具，属核实闸 C-1/C-2；夹具仅用于本地确定性验证。
"""
from typing import Dict, List, Optional

from .model import cosine


def default_vocab() -> List[str]:
    """固定词表：覆盖常见概念词与测试词，保证反演可逆。"""
    return [
        "alpha", "beta", "gamma", "delta", "epsilon", "zeta", "eta", "theta",
        "salary", "executive", "package", "secret", "internal", "policy",
        "refund", "unlimited", "returns", "customer", "data", "leak",
        "poison", "target", "query", "chunk", "vector", "embedding", "store",
        "password", "token", "key", "admin", "root", "file", "flag",
        "contract", "acquisition", "planning", "ssn", "credit", "card",
    ]


class DeterministicEmbedder:
    """位置加权词袋嵌入（可逆替身）。

    约束：`text` 的 token 须在 `vocab` 中且不重复，方可精确反演；
    非词表 token 以稳定哈希落槽（不可反演，标记为未知）。
    """

    def __init__(self, vocab: Optional[List[str]] = None):
        self.vocab = list(vocab if vocab is not None else default_vocab())
        self.index: Dict[str, int] = {t: i for i, t in enumerate(self.vocab)}
        self.dim = max(len(self.vocab), 8)

    def _slot(self, token: str) -> int:
        if token in self.index:
            return self.index[token]
        # 稳定哈希（仅用于未知 token，标记不可精确反演）
        return (sum(ord(c) for c in token) * 131) % self.dim

    def embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        for pos, tok in enumerate((text or "").split()):
            vec[self._slot(tok)] += float(pos + 1)
        return vec

    def __call__(self, text: str) -> List[float]:
        return self.embed(text)


class InMemoryVectorStore:
    """余弦 top-k 内存向量库（替身）。"""

    def __init__(self):
        self._docs: List[dict] = []

    def add(self, doc_id: str, vec: List[float], text: str) -> None:
        self._docs.append({"id": doc_id, "vec": list(vec), "text": text})

    def __len__(self) -> int:
        return len(self._docs)

    def all(self) -> List[dict]:
        return list(self._docs)

    def query(self, vec: List[float], k: int = 5) -> List[dict]:
        if k <= 0:
            raise ValueError("k 必须为正整数")
        scored = [
            {"id": d["id"], "text": d["text"], "sim": cosine(vec, d["vec"])}
            for d in self._docs
        ]
        scored.sort(key=lambda x: x["sim"], reverse=True)
        return scored[:k]


class EmbeddingHarness:
    """embedder + 向量库 + 检索器（所有路径的本地验证面）。"""

    def __init__(self, embedder: Optional[DeterministicEmbedder] = None,
                 store: Optional[InMemoryVectorStore] = None):
        self.embedder = embedder or DeterministicEmbedder()
        self.store = store or InMemoryVectorStore()

    def embed(self, text: str) -> List[float]:
        return self.embedder.embed(text)

    def ingest(self, docs: Dict[str, str]) -> None:
        for doc_id, text in docs.items():
            self.store.add(doc_id, self.embed(text), text)

    def retrieve(self, text: str, k: int = 5) -> List[dict]:
        return self.store.query(self.embed(text), k)

    def is_member(self, text: str, threshold: float = 0.98) -> bool:
        """最近邻相似度≥阈值即判为「在集」（成员推断的确定性判据）。"""
        hits = self.retrieve(text, k=1)
        return bool(hits) and hits[0]["sim"] >= threshold


def fixture_corpus() -> Dict[str, str]:
    """合成知识库文档（唯一 token，保证反演可逆）。"""
    return {
        "doc-1": "salary executive package secret",
        "doc-2": "refund unlimited returns policy",
        "doc-3": "password admin root token file",
        "doc-4": "contract acquisition planning internal",
    }
