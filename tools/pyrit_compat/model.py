"""框架数据模型（全部可 JSON 序列化）。"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

CATEGORIES = ("api", "function", "parameter", "behavior")
STATUSES = ("added", "updated", "deprecated", "removed")
VERIFICATIONS = ("verified", "unverified")
ADAPTATIONS = ("none", "warn", "rewrite", "error")
SEVERITIES = ("info", "warn", "error")


@dataclass(frozen=True)
class ChangeRecord:
    id: str
    category: str
    status: str
    symbol: str
    version_from: str
    version_to: str
    detail: str
    source_url: str
    verified_at: str
    verification: str
    adaptation: str
    adaptation_note: str

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "ChangeRecord":
        return cls(**{k: raw[k] for k in cls.__dataclass_fields__})

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CallSite:
    file: str
    line: int
    module: str
    symbol: str
    function: str
    kind: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Alert:
    severity: str
    code: str
    message: str
    file: str | None = None
    line: int | None = None
    change_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
