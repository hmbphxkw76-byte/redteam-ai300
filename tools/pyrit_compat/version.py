"""版本解析与范围判定（纯标准库）。"""
from __future__ import annotations

from functools import total_ordering

BASELINE_VERSION = "1.1.0"
TARGET_VERSION = "1.2.1"
SUPPORTED_VERSIONS = ("1.1.0", "1.2.0", "1.2.1")


@total_ordering
class Version:
    """三段式数字版本；拒绝非数字段，避免把版本漂移静默当作可比较。"""

    __slots__ = ("parts", "raw")

    def __init__(self, raw: str) -> None:
        if not isinstance(raw, str):
            raise TypeError("version must be str")
        text = raw.strip()
        if text.startswith("v"):
            text = text[1:]
        core = text.split("+", 1)[0]
        segments = core.split(".")
        if not 1 <= len(segments) <= 3:
            raise ValueError("unsupported version format: %r" % raw)
        try:
            self.parts = tuple(int(s) for s in segments)
        except ValueError as exc:
            raise ValueError("non-numeric version segment: %r" % raw) from exc
        self.parts += (0,) * (3 - len(self.parts))
        self.raw = raw

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Version):
            return NotImplemented
        return self.parts == other.parts

    def __lt__(self, other: "Version") -> bool:
        return self.parts < other.parts

    def __hash__(self) -> int:
        return hash(self.parts)

    def __str__(self) -> str:
        return ".".join(str(p) for p in self.parts)

    def __repr__(self) -> str:
        return "Version(%r)" % self.raw


def in_range(version: str, version_from: str | None, version_to: str | None) -> bool:
    """闭开区间 [from, to)；端点为空表示无界。"""
    v = Version(version)
    if version_from and v < Version(version_from):
        return False
    if version_to and v >= Version(version_to):
        return False
    return True
