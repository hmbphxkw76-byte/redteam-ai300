#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 C1 类型化结论（唯一事实源，P-1）。

不 import 本项目任何模块；outcome 取五值语义子集，reason 固定枚举。
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

ABSENT = "ABSENT"
AUTH_REQUIRED = "AUTH_REQUIRED"
EXPOSED_NO_AUTH = "EXPOSED_NO_AUTH"
BLOCKED = "BLOCKED"
OUTCOMES = (ABSENT, AUTH_REQUIRED, EXPOSED_NO_AUTH, BLOCKED)

REASONS = frozenset((
    "", "none_found", "private_only", "auth_required", "no_response",
    "invalid_version", "no_public_ip",
))

CVE_ANCHOR = "CVE-2025-23266"


@dataclass(frozen=True)
class C1Verdict:
    """不可变只读观察结论；字段与既有 dict 调用同构 + shim 零回归。"""

    outcome: str
    reason: str = ""
    summary: str = ""
    public_ip: str = ""
    exposed_ports: Tuple[int, ...] = ()
    version: str = ""
    cve_advice: str = ""
    credential_hint: str = ""
    command: str = ""
    output: str = ""
    shot_cmd: str = ""
    extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.outcome not in OUTCOMES:
            raise ValueError("未知 outcome: %r" % self.outcome)
        if self.reason not in REASONS:
            raise ValueError("非既有 reason: %r" % self.reason)
        object.__setattr__(self, "exposed_ports", tuple(self.exposed_ports))

    def __getitem__(self, key: str):
        """dict shim：轻量版 `v["outcome"]` 零回归；整数下标抛 IndexError 以正确终止 `in` 迭代。"""
        if not isinstance(key, str):
            raise IndexError(key)
        return getattr(self, key)

    def get(self, key: str, default=None):
        """dict shim：轻量版 `v.get("version")` 零回归。"""
        return getattr(self, key, default)
