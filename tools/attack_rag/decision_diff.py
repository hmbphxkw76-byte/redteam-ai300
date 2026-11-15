#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""下游决策影响取证（路径 C）：baseline vs manipulated 双次捕获。

判据必须是**同一查询、同一模型、仅上下文不同**的两次响应差异（闸 C）；
单次「看起来被操纵」的响应不构成因果证据。上下文获取异常一律收敛为
「未生效」，不抛给编排层。
"""
import re
from dataclasses import dataclass
from typing import Callable, Sequence

_WS = re.compile(r"\s+")


def _norm(text: str) -> str:
    """归一化：折叠空白与首尾空白，避免格式噪声被误判为决策变化。"""
    return _WS.sub(" ", (text or "")).strip()


@dataclass(frozen=True)
class DiffResult:
    """一次双次捕获的差异结论。"""

    query: str
    before: str
    after: str
    changed: bool
    reason: str

    def render(self) -> str:
        """证据「关键输出」用：两次响应并列 + 判定。"""
        return ("baseline: %s\nmanipulated: %s\nchanged: %s（%s）"
                % (self.before, self.after, self.changed, self.reason))

    def as_dict(self):
        return {"query": self.query, "before": self.before, "after": self.after,
                "changed": self.changed, "reason": self.reason}


class DecisionDiff:
    """双次捕获器：responder(query, context_texts) → 响应文本。"""

    def __init__(self, responder: Callable[[str, Sequence[str]], str]):
        if not callable(responder):
            raise ValueError("DecisionDiff 需要可调用的 responder(query, context)")
        self.responder = responder

    def capture(self, query: str, ctx_baseline: Sequence[str],
                ctx_manipulated: Sequence[str]) -> DiffResult:
        try:
            before = self.responder(query, list(ctx_baseline))
        except Exception as exc:  # 上下文/后端异常收敛为未生效
            return DiffResult(query, "", "", False, "基线上下文调用失败：%s" % exc)
        try:
            after = self.responder(query, list(ctx_manipulated))
        except Exception as exc:
            return DiffResult(query, before, "", False, "被操纵上下文调用失败：%s" % exc)
        changed = _norm(before) != _norm(after)
        reason = "响应文本差异" if changed else "两次响应一致（未生效）"
        return DiffResult(query, before, after, changed, reason)
