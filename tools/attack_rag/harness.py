#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合成 RAG 环境（验证主面，核实闸 A）。

纯标准库、不联网、不调用真实 LLM；作为全部攻击路径的本地可复现测试面
（AIVP 演练目标无 RAG 投毒 lab，仅作可选回归闸）。

三条能力对应三段攻击取证：
  - `retrieve()` → 检索层操纵 before/after（路径 A/B）
  - `generate()` → 下游决策影响 baseline/manipulated（路径 C）
  - `inject()`   → 知识库投毒写入面（路径 A）
"""
from dataclasses import dataclass
from typing import List, Optional, Sequence, Tuple

from .embedder import DIM  # noqa: F401  (对外暴露默认维度)
from .embedder import DeterministicEmbedder, Embedder, cosine

# 恶意文档标记：进入生成上下文后，generator 据此判定被操纵（下游决策影响取证）。
MALICIOUS_MARKER = "TARGET_ANSWER:"

# 合成语料模板（中性知识库内容，不含攻击载荷）
_TOPICS = (
    "员工入职流程与账号开通说明",
    "生产环境变更审批与回滚预案",
    "客户数据分级与脱敏规范",
    "季度费用报销与预算冻结规则",
    "系统日志留存与审计追溯要求",
    "供应商准入评估与年度复核",
)


def default_corpus(size: int = 1200) -> List[str]:
    """生成 size 篇中性文档（默认 1.2k，满足白盒 ASR 的 ≥1k 语料前提）。"""
    if size <= 0:
        raise ValueError("size 必须为正整数")
    docs = []
    for i in range(size):
        topic = _TOPICS[i % len(_TOPICS)]
        docs.append("文档 %04d：%s。编号 %d，参考章节 %d.%d，责任部门 D%d。"
                    % (i, topic, i, i % 9 + 1, i % 7 + 1, i % 5 + 1))
    return docs


@dataclass(frozen=True)
class RetrievalHit:
    """一次 top-k 命中：文档标识 + 相似度 + 原文。"""

    doc_id: str
    score: float
    text: str

    def as_dict(self):
        return {"doc_id": self.doc_id, "score": round(self.score, 6),
                "text": self.text}


class RagHarness:
    """合成 RAG：构建语料 → 建立向量索引 → top-k 检索 → 生成回答。"""

    def __init__(self, corpus: Sequence[str], embedder: Optional[Embedder] = None,
                 k: int = 3):
        if not corpus:
            raise ValueError("corpus 不能为空（RagHarness 须有初始语料）")
        if k <= 0:
            raise ValueError("k 必须为正整数")
        self.embedder: Embedder = embedder or DeterministicEmbedder()
        self.k = k
        self._docs: List[Tuple[str, str]] = []
        self._vectors: List[List[float]] = []
        for text in corpus:
            self._add("doc-%04d" % len(self._docs), text)
        self.index()

    # -- 写入面 -----------------------------------------------------------
    def _add(self, doc_id: str, text: str) -> None:
        self._docs.append((doc_id, text))
        self._vectors.append([])

    def index(self) -> int:
        """（重）建向量索引；返回已索引文档数。"""
        self._vectors = [self.embedder.embed(t) for _i, t in self._docs]
        return len(self._vectors)

    def inject(self, texts: Sequence[str], prefix: str = "mal") -> List[str]:
        """注入文档到语料并重建索引；返回新增 doc_id 列表。"""
        added = []
        for text in texts:
            doc_id = "%s-%04d" % (prefix, len(self._docs))
            self._add(doc_id, text)
            added.append(doc_id)
        self.index()
        return added

    # -- 读取面 -----------------------------------------------------------
    def __len__(self) -> int:
        return len(self._docs)

    @property
    def doc_ids(self) -> Tuple[str, ...]:
        return tuple(d for d, _t in self._docs)

    def text_of(self, doc_id: str) -> str:
        for d, t in self._docs:
            if d == doc_id:
                return t
        raise KeyError("未知 doc_id：%s" % doc_id)

    def retrieve(self, query: str, k: Optional[int] = None) -> List[RetrievalHit]:
        """返回与查询余弦相似度最高的 k 篇文档（检索条件取证）。

        并列相似度按 doc_id 升序，保证同一命令重跑结果一致（§6.1）。
        """
        qv = self.embedder.embed(query)
        scored = [(cosine(qv, vec), doc_id, text)
                  for (doc_id, text), vec in zip(self._docs, self._vectors)]
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [RetrievalHit(d, s, t) for s, d, t in scored[:k or self.k]]

    def snapshot(self, query: str, k: Optional[int] = None) -> Tuple[str, ...]:
        """只取 top-k 的 doc_id 序列（before/after 对照的最简判据）。"""
        return tuple(h.doc_id for h in self.retrieve(query, k))

    def generate(self, query: str, ctx_texts: Sequence[str]) -> str:
        """生成回答：上下文含恶意标记则返回被操纵答案，否则基线答案。"""
        for t in ctx_texts or ():
            if MALICIOUS_MARKER in t:
                answer = t.split(MALICIOUS_MARKER, 1)[1].strip()
                return "MANIPULATED: %s" % answer
        return "BASELINE: 正常答案（无投毒上下文）"
