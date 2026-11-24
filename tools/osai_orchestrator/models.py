"""共享值类型：判定、记录、配置。零外部依赖，纯数据。"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Verdict(str, Enum):
    PASS = "PASS"
    BLOCKED = "BLOCKED"


class Decision(str, Enum):
    CONTINUE = "continue"
    PIVOT = "pivot"
    TERMINATE = "terminate"
    ASK = "ask"


@dataclass
class Record:
    """可追溯记录：步骤标识 + 事实 + 来源路径。"""
    step: str
    fact: str
    source: str = ""


@dataclass
class GateResult:
    """G0 判定结果：与主线 §2.2 结论语义一致（PASS / BLOCKED）。"""
    name: str
    verdict: Verdict
    evidence: str = ""
    findings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.verdict is Verdict.PASS


@dataclass
class LimitConfig:
    """运行时上限：对齐 config.go:311-317 的阈值判据。"""
    same_tool_limit: int = 5
    total_tool_limit: int = 10
    general_calls: int = 100
    limited_calls: int = 20
    reflector_after: int = 3

    def __post_init__(self) -> None:
        for name in ("same_tool_limit", "total_tool_limit", "general_calls", "limited_calls", "reflector_after"):
            if getattr(self, name) <= 0:
                raise ValueError("%s must be positive" % name)


@dataclass
class AnonymizeConfig:
    """匿名化占位符：对齐 pentester.tmpl:56-66 的占位符规则。"""
    address: str = "{target_ip}"
    domain: str = "{target_domain}"
    username: str = "{username}"
    secret: str = "{password}"
    token: str = "{token}"

    def as_map(self) -> dict[str, str]:
        return {
            "address": self.address,
            "domain": self.domain,
            "username": self.username,
            "secret": self.secret,
            "token": self.token,
        }


@dataclass
class PromptContext:
    """提示词上下文：交互通道（本地语言）与技术通道（英文）分离。"""
    engagement: str = ""
    technical: str = ""
    summary: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def validate_channels(self) -> list[str]:
        """返回被本地化到技术通道的可疑项（含非 ASCII 即视为污染）。"""
        problems: list[str] = []
        for line in self.technical.splitlines():
            if any(ord(ch) > 0x2E7F for ch in line):
                problems.append(line)
        return problems
