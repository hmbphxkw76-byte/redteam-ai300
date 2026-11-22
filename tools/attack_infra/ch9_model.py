#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 扩展领域类型（唯一事实源）。

不 import 本项目任何模块；依赖以 Any 承载。结论值与既有 Outcome 对齐复用
（通过字符串值，避免反向 import model.py 造成环）。
"""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

# 与既有 Outcome 值一致的字符串（B7/五值结论语义不变，AC-19）
ABSENT = "ABSENT"
AUTH_REQUIRED = "AUTH_REQUIRED"
EXPOSED_NO_AUTH = "EXPOSED_NO_AUTH"
EXPLOITED = "EXPLOITED"
BLOCKED = "BLOCKED"

VALID_OUTCOMES = (ABSENT, AUTH_REQUIRED, EXPOSED_NO_AUTH, EXPLOITED, BLOCKED)

# ABSENT/BLOCKED 合法 reason（严格沿用既有 model.py 的 ABSENT_REASONS ∪
# BLOCKED_REASONS ∪ AUTH_REASONS，AC-19：不引入新 reason）。
# Ch9 特有情形映射到语义最近的既有价值，映射依据见各模块 docstring：
#   scope_expansion_required → forbidden；version_safe/no_hook_surface → none_found；
#   no_gpu_toolkit → no_tool。
VALID_REASONS = frozenset((
    "spa_fallback", "network", "no_tool", "none_found",        # 既有 ABSENT_REASONS
    "evidence_incomplete", "guardrail", "mismatch", "no_difference",  # 既有 BLOCKED_REASONS
    "", "http_401", "http_403", "forbidden", "no_credential",  # 既有 AUTH_REASONS
    "local_echo",                                             # path_c 使用的既有值
))


@dataclass(frozen=True)
class CredFingerprint:
    """凭据指纹：前缀 + 长度 + 位置（AC-03/09，明文不落盘）。"""

    prefix: str
    length: int
    location: str

    def as_text(self) -> str:
        return "%s…(len=%d) @ %s" % (self.prefix, self.length, self.location)

    @property
    def key(self) -> str:
        return "%s|%d|%s" % (self.prefix, self.length, self.location)


@dataclass(frozen=True)
class Capability:
    """单一身份的一项能力。"""

    resource: str
    verb: str


@dataclass
class CapabilityMatrix:
    """双身份能力对比；completes 表示读写互补可接管。"""

    identity_a: str
    identity_b: str
    a_caps: Tuple[Capability, ...] = ()
    b_caps: Tuple[Capability, ...] = ()
    completes: bool = False
    gap: str = ""

    @staticmethod
    def can_read(caps: Tuple[Capability, ...]) -> bool:
        return any(c.resource == "secrets" and c.verb in ("list", "get", "watch")
                   for c in caps)

    @staticmethod
    def can_write(caps: Tuple[Capability, ...]) -> bool:
        return any(c.resource == "pods" and c.verb in ("create", "patch", "delete")
                   for c in caps)

    def evaluate(self) -> None:
        read_ok = self.can_read(self.a_caps) or self.can_read(self.b_caps)
        write_ok = self.can_write(self.a_caps) or self.can_write(self.b_caps)
        self.completes = read_ok and write_ok
        if not read_ok:
            self.gap = "no_secret_read"
        elif not write_ok:
            self.gap = "no_pod_create"
        else:
            self.gap = ""


@dataclass
class Ch9Verdict:
    """Ch9 步骤结论，字段与既有 StepVerdict 同构（runner 可消费）。"""

    step_id: str
    outcome: str
    reason: str = ""
    summary: str = ""
    command: str = ""
    output: str = ""
    evidence_extra: Dict[str, Any] = field(default_factory=dict)
    screenshot: str = ""
    evidence_path: str = ""
    evidence_ok: bool = True

    def __post_init__(self):
        if self.outcome not in VALID_OUTCOMES:
            raise ValueError("未知 outcome: %r" % self.outcome)
        self.reason = self.reason or ""
        if self.outcome in (ABSENT, BLOCKED) and self.reason not in VALID_REASONS:
            raise ValueError("%s 的 reason 必须属于 VALID_REASONS，收到 %r"
                             % (self.outcome, self.reason))
