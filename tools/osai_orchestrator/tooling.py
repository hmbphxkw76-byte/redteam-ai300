"""工具治理：类型化注册、调用 ID 归一化、错误分类重试、受限检索。

沿用 tools/pyrit_compat 的注册表规则思路，零第三方依赖、零 PyRIT 强依赖。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

from .models import Verdict


class ToolKind(str, Enum):
    ENVIRONMENT = "environment"
    SEARCH_NETWORK = "search_network"
    SEARCH_VECTOR = "search_vector_db"
    AGENT = "agent"
    STORE_RESULT = "store_agent_result"
    STORE_VECTOR = "store_vector_db"
    BARRIER = "barrier"


@dataclass
class ToolSpec:
    name: str
    kind: ToolKind
    roles: frozenset[str] = frozenset()
    description: str = ""


class TypedRegistry:
    """类型化工具注册 + 按角色最小集（B-03）。"""

    def __init__(self, specs: list[ToolSpec] | None = None) -> None:
        self._specs: dict[str, ToolSpec] = {}
        for spec in specs or []:
            self.register(spec)

    def register(self, spec: ToolSpec) -> None:
        if not spec.name.strip():
            raise ValueError("tool name required")
        self._specs[spec.name] = spec

    def for_role(self, role: str) -> list[ToolSpec]:
        return [s for s in self._specs.values() if not s.roles or role in s.roles]

    def check(self, name: str, role: str) -> tuple[Verdict, str]:
        spec = self._specs.get(name)
        if spec is None:
            return Verdict.BLOCKED, "unknown tool %s" % name
        if spec.roles and role not in spec.roles:
            return Verdict.BLOCKED, "tool %s not allowed for role %s" % (name, role)
        return Verdict.PASS, ""


class CallIDNormalizer:
    """跨模型工具调用 ID 归一化（B-05）：与版本无关的纯规则。"""

    _TEMPLATE = re.compile(r"^(?:call|toolu|chatcmpl)[-_]?([A-Za-z0-9]+)$")

    def normalize(self, raw: str) -> str | None:
        text = (raw or "").strip()
        if not text:
            return None
        match = self._TEMPLATE.match(text)
        if match:
            return "call_%s" % match.group(1)
        if re.fullmatch(r"[A-Za-z0-9_-]+", text):
            return "call_%s" % text
        return None

    def repair_arguments(self, raw: str) -> tuple[Verdict, str]:
        text = (raw or "").strip()
        if not text:
            return Verdict.BLOCKED, "empty arguments"
        if text.startswith("{") and not text.endswith("}"):
            return Verdict.PASS, text + "}"
        return Verdict.PASS, text


class ErrorKind(str, Enum):
    DETERMINISTIC = "deterministic"
    TRANSIENT = "transient"


class ErrorClassifier:
    """确定性/瞬时分类（B-06）：确定性错误零重试。"""

    _DETERMINISTIC = (
        "invalid argument", "not found", "permission denied", "syntax error", "unknown tool",
    )
    _TRANSIENT = ("timeout", "rate limit", "connection reset", "temporarily unavailable")

    def classify(self, message: str) -> ErrorKind:
        low = (message or "").lower()
        if any(k in low for k in self._DETERMINISTIC):
            return ErrorKind.DETERMINISTIC
        if any(k in low for k in self._TRANSIENT):
            return ErrorKind.TRANSIENT
        return ErrorKind.DETERMINISTIC


@dataclass
class RetryResult:
    attempts: int
    should_retry: bool
    reason: str


class RetryPolicy:
    """差异化重试：确定性零重试，瞬时有限退避。"""

    def __init__(self, max_attempts: int = 3) -> None:
        if max_attempts < 1:
            raise ValueError("max_attempts must be positive")
        self.max_attempts = max_attempts

    def decide(self, kind: ErrorKind, already: int) -> RetryResult:
        if kind is ErrorKind.DETERMINISTIC:
            return RetryResult(already, False, "deterministic error: no retry")
        if already >= self.max_attempts:
            return RetryResult(already, False, "retry ceiling reached")
        return RetryResult(already + 1, True, "transient error: bounded retry")


@dataclass
class RetrievalHit:
    text: str
    source: str
    allowed: bool = True


class BoundedRetriever:
    """受限检索（B-08）：无外发、无目标标识、结果可离线核验。"""

    _LOCAL_MARKER = "local://"

    def __init__(self, max_hits: int = 5) -> None:
        self.max_hits = max_hits

    def filter(self, hits: list[RetrievalHit]) -> tuple[list[RetrievalHit], list[str]]:
        kept: list[RetrievalHit] = []
        dropped: list[str] = []
        for hit in hits:
            if not hit.allowed or not hit.source.startswith(self._LOCAL_MARKER):
                dropped.append(hit.source)
                continue
            if re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", hit.text):
                dropped.append("%s: contains address" % hit.source)
                continue
            kept.append(hit)
            if len(kept) >= self.max_hits:
                break
        return kept, dropped
