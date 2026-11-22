#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 加固五值结论类型（唯一事实源）。

不 import 本项目任何模块；outcome/reason 语义对齐
`tools/attack_infra/model.py` 既有五值与 reason 集合（C1 指针，不复述）。
"""
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

ABSENT = "ABSENT"
AUTH_REQUIRED = "AUTH_REQUIRED"
EXPOSED_NO_AUTH = "EXPOSED_NO_AUTH"
EXPLOITED = "EXPLOITED"
BLOCKED = "BLOCKED"
OUTCOMES = (ABSENT, AUTH_REQUIRED, EXPOSED_NO_AUTH, EXPLOITED, BLOCKED)

VALID_REASONS = frozenset((
    "spa_fallback", "network", "no_tool", "none_found",
    "evidence_incomplete", "guardrail", "mismatch", "no_difference",
    "", "http_401", "http_403", "forbidden", "no_credential", "local_echo",
))


@dataclass(frozen=True)
class Fingerprint:
    """凭据指纹：键名 + 长度 + 位置（明文不落盘，P-1）。"""

    key: str
    length: int
    location: str

    def as_text(self) -> str:
        return "%s(len=%d)@%s" % (self.key, self.length, self.location)


@dataclass
class TriadVerdict:
    """类型化五值结论；字段与 `collect_evidence.py` 参数同构（H-6）。"""

    step_id: str
    outcome: str
    reason: str = ""
    summary: str = ""
    command: str = ""
    output: str = ""
    shot_cmd: str = ""
    fingerprints: Tuple[Fingerprint, ...] = ()
    wrappers: Tuple[str, ...] = ()
    evidence_path: str = ""
    evidence_ok: bool = True
    evidence_extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.outcome not in OUTCOMES:
            raise ValueError("未知 outcome: %r" % self.outcome)
        if self.reason not in VALID_REASONS:
            raise ValueError("非既有 reason: %r" % self.reason)
        self.fingerprints = tuple(self.fingerprints)
        self.wrappers = tuple(self.wrappers)

    def __getitem__(self, key: str):
        """兼容既有轻量版测试/调用方的字典访问（零回归，不改判据）。"""
        return getattr(self, key)

    def get(self, key: str, default=None):
        """兼容 dict.get 访问（同上）。"""
        return getattr(self, key, default)
