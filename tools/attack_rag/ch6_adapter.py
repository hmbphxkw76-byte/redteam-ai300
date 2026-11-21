#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch6 probing 复用适配层（AC-A1..A3）。

把 attack-rag 已有的 `RagHarness.retrieve` + `RagBackend.respond` 封装成单参数
`query_iface(prompt) -> text`，供 attack-embeddings 的 inference probing 直接注入消费
（课程 Ch6 §6.2 Listing 8）。

边界：只做接口适配，**不实现 probing 评分/top5_avg/pairs 落盘**（归 attack-embeddings
PR #309），**不新增投毒语义**（非 Ch6 差距）。标准库、无副作用。
"""
from __future__ import annotations

from typing import Callable, Optional


def build_query_iface(harness, backend, k: Optional[int] = None) -> Callable[[str], str]:
    """返回 ``query_iface(prompt) -> str``：检索上下文 → backend 响应文本。

    - ``backend=None`` 时返回恒为空串的接口（下游按「无响应」处理，不伪造内容）。
    - backend 自身异常如实传播（不静默降级）；不写文件、不改 harness 状态。
    """
    def query_iface(prompt: str) -> str:
        if backend is None:
            return ""
        hits = harness.retrieve(prompt, k) if harness is not None else []
        contexts = [getattr(h, "text", "") for h in hits]
        text = backend.respond(prompt, contexts)  # 后端异常如实传播，不静默吞掉
        return text if isinstance(text, str) else str(text or "")

    return query_iface
