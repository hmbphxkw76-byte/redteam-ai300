#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检索层操纵取证（路径 B）：投毒前后 top-k 对照 + 对抗文本构造。

判据是**因果对照**而非单点观察（C6）：同一查询在注入前后各检索一次，
排名变化才是「检索被操纵」的证据；单次命中不足以定级。
"""
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .embedder import Embedder, cosine
from .harness import MALICIOUS_MARKER, RagHarness, RetrievalHit


@dataclass(frozen=True)
class TopKTable:
    """一个时点的 top-k 表；before/after 使用同一类型，字段结构必然一致（US4）。"""

    stage: str
    hits: Tuple[RetrievalHit, ...] = ()

    @property
    def doc_ids(self) -> Tuple[str, ...]:
        return tuple(h.doc_id for h in self.hits)

    def as_dict(self):
        return {"stage": self.stage,
                "doc_ids": list(self.doc_ids),
                "hits": [h.as_dict() for h in self.hits]}


@dataclass(frozen=True)
class BeforeAfter:
    """一次前后对照结果（证据片段的关键输出即由此渲染）。"""

    query: str
    before: TopKTable
    after: TopKTable

    @property
    def entered(self) -> Tuple[str, ...]:
        """后表中新进入 top-k 的 doc_id（保持 after 顺序）。"""
        old = set(self.before.doc_ids)
        return tuple(d for d in self.after.doc_ids if d not in old)

    @property
    def changed(self) -> bool:
        return self.before.doc_ids != self.after.doc_ids

    def render(self) -> str:
        """人类可读对照行（进证据「关键输出」，非推断）。"""
        return ("投毒前 top_k: [%s] | 投毒后 top_k: [%s] | 新进入: [%s]"
                % (", ".join(self.before.doc_ids),
                   ", ".join(self.after.doc_ids),
                   ", ".join(self.entered)))


class RetrievalProbe:
    """以 harness 为观测面，取证投毒前后 top-k 排名变化。"""

    def __init__(self, harness: RagHarness, k: Optional[int] = None):
        self.harness = harness
        self.k = k or harness.k

    def capture(self, query: str, stage: str, k: Optional[int] = None) -> TopKTable:
        hits = self.harness.retrieve(query, k or self.k)
        return TopKTable(stage=stage, hits=tuple(hits))

    def before_after(self, query: str, poison_docs: Optional[Sequence[str]] = None,
                     k: Optional[int] = None) -> BeforeAfter:
        """先取 before；若给定恶意文档则注入；再取 after。"""
        before = self.capture(query, "before", k)
        if poison_docs:
            self.harness.inject(poison_docs)
        after = self.capture(query, "after", k)
        return BeforeAfter(query=query, before=before, after=after)


class EmbeddingCollisionCraft:
    """构造与目标查询高重叠的对抗文本（白盒：依赖已知 embedder）。"""

    def __init__(self, embedder: Embedder, marker: str = MALICIOUS_MARKER):
        if embedder is None:
            raise ValueError("碰撞构造必须提供 embedder")
        self.embedder = embedder
        self.marker = marker

    def rank(self, query: str, answer: str) -> List[Tuple[float, str]]:
        """按与查询的余弦相似度降序返回候选（相似度, 文本）。"""
        qv = self.embedder.embed(query)
        scored = [(cosine(qv, self.embedder.embed(t)), t)
                  for t in self._candidates(query, answer)]
        scored.sort(key=lambda x: -x[0])
        return scored

    def craft(self, query: str, answer: str) -> str:
        """返回相似度最高的对抗文本。"""
        return self.rank(query, answer)[0][1]

    def _candidates(self, query, answer):
        tail = "权威答复：%s\n%s %s" % (answer, self.marker, answer)
        return ["%s\n%s" % (query, tail)] + [
            "%s\n%s" % (" ".join([query] * r), tail) for r in (4, 3, 2, 1)]
