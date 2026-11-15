#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-infra 领域类型（唯一事实源）。

本模块定义判定结论、端点、步骤结论、运行报告与凭据指纹；不 import 本项目任何
模块（设计记录 §3 依赖方向），注入依赖以 `Any` 承载以避免环。

对应规格 #213 v2：AC-03（三元组判据的判定值）、AC-09（凭据指纹）、AC-16（降级
结论）、AC-24（无 PyRIT 旧对象）。
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

STEP_IDS: Tuple[str, ...] = (
    "infra-01", "infra-02", "infra-03", "infra-04",
    "infra-05", "infra-06", "infra-07", "infra-08",
)

ABSENT_REASONS: Tuple[str, ...] = ("spa_fallback", "network", "no_tool", "none_found")
BLOCKED_REASONS: Tuple[str, ...] = (
    "local_echo", "evidence_incomplete", "guardrail", "mismatch", "no_difference",
)
AUTH_REASONS: Tuple[str, ...] = ("", "http_401", "http_403", "forbidden", "no_credential")


class Outcome(str, Enum):
    """降级结论（五值互斥）。见 `docs/operations/attack-infra-terms.md` §2。"""

    ABSENT = "ABSENT"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    EXPOSED_NO_AUTH = "EXPOSED_NO_AUTH"
    EXPLOITED = "EXPLOITED"
    BLOCKED = "BLOCKED"

    @property
    def is_success(self) -> bool:
        return self in (Outcome.EXPOSED_NO_AUTH, Outcome.EXPLOITED)

    @property
    def is_blocking(self) -> bool:
        return self is Outcome.BLOCKED


@dataclass(frozen=True)
class Endpoint:
    """一次端点探测的事实记录。端口是事实，服务类型是判定（canonical P-3）。"""

    url: str
    scheme: str = "http"
    host: str = ""
    port: int = 0
    kind: str = ""
    status: int = 0
    content_type: str = ""
    note: str = ""

    @property
    def label(self) -> str:
        return "%s://%s:%s" % (self.scheme, self.host, self.port)


@dataclass
class Finding:
    """单端点判定：命中/未命中及其依据。"""

    endpoint: Endpoint
    outcome: Outcome
    reason: str = ""
    detail: str = ""


@dataclass
class StepVerdict:
    """单步结论 + 可直接 copy/paste 的命令与输出（AC-18）。"""

    step_id: str
    outcome: Outcome
    reason: str = ""
    summary: str = ""
    command: str = ""
    output: str = ""
    findings: List[Finding] = field(default_factory=list)
    evidence_extra: Dict[str, Any] = field(default_factory=dict)
    evidence_path: str = ""
    evidence_ok: bool = True

    def __post_init__(self):
        if self.step_id not in STEP_IDS:
            raise ValueError("未知步骤 %r" % (self.step_id,))
        if not isinstance(self.outcome, Outcome):
            raise ValueError("outcome 必须是 Outcome，收到 %r" % (self.outcome,))
        self.reason = self.reason or ""
        if self.outcome is Outcome.ABSENT and self.reason not in ABSENT_REASONS:
            raise ValueError("ABSENT 的 reason 必须是 %s，收到 %r"
                             % ("/".join(ABSENT_REASONS), self.reason))
        if self.outcome is Outcome.BLOCKED and self.reason not in BLOCKED_REASONS:
            raise ValueError("BLOCKED 的 reason 必须是 %s，收到 %r"
                             % ("/".join(BLOCKED_REASONS), self.reason))


@dataclass(frozen=True)
class CredentialHint:
    """凭据指纹：只存前缀 + 长度 + 位置，明文不入片段（AC-09）。"""

    prefix: str
    length: int
    location: str

    def as_text(self) -> str:
        return "%s…(len=%d) @ %s" % (self.prefix, self.length, self.location)

    @property
    def key(self) -> str:
        return "%s|%d" % (self.prefix, self.length)


@dataclass
class RunReport:
    """一次运行的全部步骤结论。"""

    target: str = ""
    steps: List[StepVerdict] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    def outcome_counts(self) -> Dict[str, int]:
        counts = {o.value: 0 for o in Outcome}
        for step in self.steps:
            counts[step.outcome.value] += 1
        return counts

    def blocking(self) -> List[StepVerdict]:
        return [s for s in self.steps if s.outcome.is_blocking or not s.evidence_ok]

    def exploited(self) -> List[StepVerdict]:
        return [s for s in self.steps if s.outcome is Outcome.EXPLOITED]

    def absent(self) -> List[StepVerdict]:
        return [s for s in self.steps if s.outcome is Outcome.ABSENT]

    def next_skills(self) -> List[str]:
        """ABSENT 时建议转出的技能（AC-16）。"""
        if not self.absent():
            return []
        return ["attack-mcp-tool", "attack-ai-agent"]


@dataclass
class RunContext:
    """唯一注入点：seam 与策略全部由此组装（设计记录 §4）。"""

    target: str = ""
    transport: Any = None
    command: Any = None
    evidence: Any = None
    shot: Any = None
    out_dir: str = "loot"
    timeout: int = 30
    allow_inference: bool = False
    allow_write: bool = False
    buckets: Tuple[str, ...] = ()
    gateway_configs: Tuple[str, ...] = ()
    exec_argv: Tuple[str, ...] = ()
    inference_prompt: str = "Reply with exactly: PWNED"
    inference_model: str = ""
    inference_endpoint: str = ""
    namespace: str = ""
    inventory_endpoints: Tuple[str, ...] = ()
    secondary_targets: Tuple[str, ...] = ()
    decoy_timebox_minutes: int = 30
    service_account: str = ""
    flag_panel: str = ""
    flag_shot: str = ""
    decoy: bool = False
    step_ids: Tuple[str, ...] = STEP_IDS
    ports: Optional[Tuple[int, ...]] = None
    command_text: str = ""


RunRequest = RunContext
