#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""索引层直接操纵（SKILL.md 路径 A 第 2 步的第三选项）。

原文：构造高重叠文档、embedding 对抗文本，**或（可访问时）直接操纵
向量索引/相关性权重、元数据排序**。前两项由 `poisoned_rag` /
`retrieval_probe` 承担；本模块只在「已取得向量库写权限」时使用，
并把「改了哪几篇、权重多少、排名如何变化」全部落成可观察结论。

不做隐蔽假设：未注入文档时返回空元组，由上层记为未生效。
"""
from typing import Optional, Sequence, Tuple

from .harness import RagHarness

DEFAULT_WEIGHT = 8.0


class IndexTamper:
    """对已注入文档施加权重/优先序，模拟直接改索引的攻击面。"""

    def __init__(self, harness: RagHarness, prefix: str = "mal",
                 weight: float = DEFAULT_WEIGHT):
        self.harness = harness
        self.prefix = prefix
        self.weight = weight

    def injected_ids(self) -> Tuple[str, ...]:
        """当前语料中属于本次注入的文档（按注入前缀识别）。"""
        return tuple(d for d in self.harness.doc_ids
                     if d.startswith(self.prefix + "-"))

    def boost(self, weight: Optional[float] = None) -> Tuple[str, ...]:
        """抬高全部注入文档的相关性权重；返回被改写的 doc_id。"""
        ids = self.injected_ids()
        applied = self.weight if weight is None else weight
        for doc_id in ids:
            self.harness.set_weight(doc_id, applied)
        return ids

    def prioritize(self, doc_ids: Optional[Sequence[str]] = None) -> Tuple[str, ...]:
        """把注入文档提到元数据排序最前；返回被重排的 doc_id 序列。"""
        ordered = tuple(doc_ids) if doc_ids is not None else self.injected_ids()
        return self.harness.set_priority(ordered)

    def reset(self) -> None:
        """撤销操纵（对照/复跑用）。"""
        self.harness.clear_tamper()

    def state(self):
        return self.harness.tamper_state()
