"""上下文、记忆与报告治理：摘要标记、压缩、匿名化、白名单、复核、模板覆盖、本体。

全部为纯逻辑；不修改证据片段与 flag 原值块，不引入外部服务。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable

from .models import AnonymizeConfig, PromptContext, Verdict


SUMMARY_PREFIX = "[historical-summary]"


class SummaryMarker:
    """摘要标记协议（A-16）：摘要仅作历史，禁止被当作指令或模仿格式。"""

    @staticmethod
    def is_summary(text: str) -> bool:
        return text.startswith(SUMMARY_PREFIX)

    @staticmethod
    def mark(text: str) -> str:
        return "%s %s" % (SUMMARY_PREFIX, text)

    @staticmethod
    def detect_injection(text: str) -> list[str]:
        """检测检索片段中的指令式内容（D5-01）；只标记不执行。"""
        patterns = (
            r"ignore (all )?previous",
            r"you are now",
            r"call the \w+ tool",
            r"system prompt",
        )
        hits: list[str] = []
        for pat in patterns:
            if re.search(pat, text, re.IGNORECASE):
                hits.append(pat)
        return hits


_IDENTIFIERS = (
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    re.compile(r"\b[\w-]+\.(?:com|net|org|io|local)\b", re.IGNORECASE),
)


class Anonymizer:
    """记忆写入匿名化（A-13）：地址/域名/凭据/令牌换占位符。"""

    def __init__(self, config: AnonymizeConfig | None = None) -> None:
        self.config = config or AnonymizeConfig()

    def anonymize(self, text: str) -> str:
        out = _IDENTIFIERS[0].sub(self.config.address, text)
        out = _IDENTIFIERS[1].sub(self.config.domain, out)
        out = re.sub(r"(?i)(password\s*[:=]\s*)(\S+)", r"\g<1>" + self.config.secret, out)
        out = re.sub(r"(?i)(token\s*[:=]\s*)(\S+)", r"\g<1>" + self.config.token, out)
        return out


class MemoryWhitelist:
    """沉淀白名单（B-11）：只沉淀可复用方法论，默认拒绝原文。"""

    ALLOWED_KINDS = {"methodology", "command_template", "payload_structure", "failure_lesson"}

    def __init__(self, allowed: Iterable[str] | None = None) -> None:
        self.allowed = set(allowed) if allowed is not None else set(self.ALLOWED_KINDS)

    def allows(self, kind: str) -> bool:
        return kind in self.allowed


@dataclass
class CompactResult:
    text: str
    kept: list[str] = field(default_factory=list)
    dropped: list[str] = field(default_factory=list)
    bytes_before: int = 0
    bytes_after: int = 0


class ContextCompactor:
    """长上下文压缩（B-04）：保留关键标识符与证据路径，不产生新建议。"""

    def __init__(self, keeper_patterns: Iterable[str] | None = None) -> None:
        self.keepers = [re.compile(p) for p in (
            keeper_patterns or (r"\b(?:\d{1,3}\.){3}\d{1,3}\b", r"evidence/[^\s]+", r"\bstep[- ]?\d+\b")
        )]

    def compact(self, sections: list[str], max_bytes: int) -> CompactResult:
        kept: list[str] = []
        dropped: list[str] = []
        for section in sections:
            if any(k.search(section) for k in self.keepers):
                kept.append(section)
            else:
                dropped.append(section)
        text = "\n".join(kept)
        before = sum(len(s.encode("utf-8")) for s in sections)
        after = len(text.encode("utf-8"))
        while after > max_bytes and kept:
            dropped.insert(0, kept.pop())
            text = "\n".join(kept)
            after = len(text.encode("utf-8"))
        return CompactResult(text, kept, dropped, before, after)


@dataclass
class ReviewItem:
    requirement: str
    location: str = ""
    met: bool = False
    note: str = ""


class IndependentReviewer:
    """独立复核（A-15）：不引用执行者结论，只认报告位置与证据。"""

    def review(self, items: list[ReviewItem]) -> tuple[Verdict, list[str]]:
        problems = [
            "requirement not located in report: %s" % it.requirement
            for it in items if not it.met or not it.location.strip()
        ]
        return (Verdict.BLOCKED if problems else Verdict.PASS), problems


class TemplateOverlay:
    """提示词模板覆盖（B-10）：语境隔离 + 变量来源可追溯。"""

    def __init__(self, templates: dict[str, str]) -> None:
        self.templates = dict(templates)

    def render(self, context: str, name: str, variables: dict[str, str]) -> tuple[Verdict, str]:
        if context not in self.templates:
            return Verdict.BLOCKED, ""
        text = self.templates[context]
        missing = [k for k in re.findall(r"<([A-Za-z_]+)>", text) if k not in variables]
        if missing:
            return Verdict.BLOCKED, "missing variables: %s" % ", ".join(missing)
        for key, value in variables.items():
            text = text.replace("<%s>" % key, value)
        return Verdict.PASS, text


class Ontology:
    """图谱本体分类法（B-07）：固定标签与关系，禁止自造。"""

    NODE_LABELS = {
        "Host", "Port", "Service", "WebApp", "Endpoint", "Account", "Vulnerability",
        "Misconfiguration", "Credential", "Evidence", "Attempt", "AttackTechnique",
    }
    EDGE_TYPES = {
        "HAS_PORT", "RUNS_SERVICE", "HOSTS_APP", "HAS_ENDPOINT", "DETECTED_VULNERABILITY",
        "CONFIRMED_VULNERABILITY", "HAS_VULNERABILITY", "HAS_MISCONFIGURATION",
        "AUTHENTICATES_TO", "YIELDED_ACCESS", "ATTEMPTED_ON",
    }
    STATES = {"scanner_hit", "verified", "exploited"}

    def validate(self, label: str, edge: str, state: str) -> tuple[Verdict, list[str]]:
        problems: list[str] = []
        if label not in self.NODE_LABELS:
            problems.append("unknown node label %s" % label)
        if edge not in self.EDGE_TYPES:
            problems.append("unknown edge type %s" % edge)
        if state not in self.STATES:
            problems.append("unknown state %s" % state)
        return (Verdict.BLOCKED if problems else Verdict.PASS), problems
