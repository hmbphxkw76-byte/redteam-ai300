#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 C3 类型化身份链结论（唯一事实源，P-1）。

不 import 本项目任何模块；asset_id 规范化稳定可引用（P-2）。
"""
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

IAM = "iam"
K8S_SA = "k8s-sa"
CHAIN_KINDS = (IAM, K8S_SA)

OUTCOMES = ("REACHABLE", "GAP", "ABSENT")
REASONS = frozenset(("", "none_found", "no_secret_read", "no_pod_create", "empty_chain"))

_SAFE_RE = re.compile(r"[^a-z0-9-]+")


def asset_id_for(kind: str, name: str) -> str:
    """稳定 asset_id：`<kind>-<slug>`；同名同 ID，无随机（P-2）。"""
    slug = _SAFE_RE.sub("-", (name or "").strip().lower()).strip("-")
    return "%s-%s" % (kind, slug or "unknown")


@dataclass(frozen=True)
class IdentityChainVerdict:
    """身份链归一结论；fig/table 锚点与 dict 兼容 shim。"""

    outcome: str
    reason: str = ""
    kind: str = IAM
    anchor: str = ""
    summary: str = ""
    asset_ids: Tuple[str, ...] = ()
    path: Tuple[str, ...] = ()
    gap: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.outcome not in OUTCOMES:
            raise ValueError("未知 outcome: %r" % self.outcome)
        if self.reason not in REASONS:
            raise ValueError("非既有 reason: %r" % self.reason)
        object.__setattr__(self, "asset_ids", tuple(self.asset_ids))
        object.__setattr__(self, "path", tuple(self.path))

    def __getitem__(self, key: str):
        """dict shim；整数下标抛 IndexError 以正确终止 `in` 迭代。"""
        if not isinstance(key, str):
            raise IndexError(key)
        return getattr(self, key)

    def get(self, key: str, default=None):
        return getattr(self, key, default)
