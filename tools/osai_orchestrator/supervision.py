"""运行时监督：执行监控、反思纠错、调用上限、栅栏终止。

判据取自 PentAGI config.go:311-317 与 performer.go:124-412，
以纯逻辑实现，不引入 Go 服务或外部调用。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .models import Decision, LimitConfig, Verdict


@dataclass
class MonitorVerdict:
    verdict: Verdict
    same_tool_count: int
    total_count: int
    advancing: bool
    advice: str = ""


class ExecutionMonitor:
    """同工具/总调用阈值检测 + 推进判定（A-09）。

    advancing 由调用方基于事实给出，本类不猜测目标是否达成。
    """

    def __init__(self, config: LimitConfig | None = None) -> None:
        self.config = config or LimitConfig()
        self._history: list[str] = []

    def observe(self, tool: str, advancing: bool) -> MonitorVerdict:
        self._history.append(tool)
        same = 0
        for name in reversed(self._history):
            if name != tool:
                break
            same += 1
        total = len(self._history)
        tripped = same >= self.config.same_tool_limit or total >= self.config.total_tool_limit
        if not tripped and advancing:
            return MonitorVerdict(Verdict.PASS, same, total, True)
        if not advancing:
            advice = "no measurable progress; pivot or report completed part"
        elif same >= self.config.same_tool_limit:
            advice = "identical calls repeated; change strategy"
        else:
            advice = "total call ceiling reached; graceful termination"
        return MonitorVerdict(Verdict.BLOCKED, same, total, advancing, advice)

    def reset(self) -> None:
        self._history.clear()


@dataclass
class ReflectVerdict:
    decision: Decision
    reason: str
    ready_to_stop: bool = False


class Reflector:
    """三振纠错：连续失败后给出明确下一步或收口（A-11）。"""

    def __init__(self, after: int = 3) -> None:
        self.after = after

    def reflect(self, failures: int, has_next_action: bool, near_limit: bool) -> ReflectVerdict:
        if near_limit:
            return ReflectVerdict(Decision.TERMINATE, "near call ceiling", True)
        if failures < self.after:
            return ReflectVerdict(Decision.CONTINUE, "below reflector threshold")
        if has_next_action:
            return ReflectVerdict(Decision.CONTINUE, "recovery action available")
        return ReflectVerdict(Decision.TERMINATE, "no recovery action after threshold", True)


class ToolCallBudget:
    """按角色分级硬上限（A-12）。上限优先于任何监督开关。"""

    def __init__(self, config: LimitConfig | None = None) -> None:
        self.config = config or LimitConfig()

    def ceiling(self, role: str) -> int:
        limited = {"searcher", "enricher", "memorist", "generator", "reporter", "adviser", "reflector", "planner"}
        return self.config.limited_calls if role.lower() in limited else self.config.general_calls

    def check(self, role: str, used: int, pending: int) -> tuple[Verdict, list[str]]:
        if used < 0 or pending < 0:
            raise ValueError("used and pending must be non-negative")
        ceiling = self.ceiling(role)
        remaining = ceiling - used
        if remaining < 0:
            raise ValueError("used exceeds ceiling")
        if pending <= remaining:
            return Verdict.PASS, []
        return Verdict.BLOCKED, [
            "pending %d exceeds remaining %d" % (pending, remaining),
            "reprioritize: keep completable steps; report rest as incomplete",
        ]


class BarrierKind(str, Enum):
    DONE = "done"
    ASK = "ask"


@dataclass
class BarrierDecision:
    kind: BarrierKind
    needs_confirmation: bool
    reasons: list[str] = field(default_factory=list)


class Barrier:
    """终止/提问栅栏（A-17）：证据不全不得终止，需人工确认走 ask。"""

    def decide(
        self,
        objective_met: bool,
        evidence_paths: list[str],
        dual_channel_ok: bool,
        needs_scope_confirmation: bool,
    ) -> BarrierDecision:
        reasons: list[str] = []
        if needs_scope_confirmation:
            reasons.append("scope boundary requires human confirmation")
            return BarrierDecision(BarrierKind.ASK, True, reasons)
        if not objective_met:
            reasons.append("objective not met")
            return BarrierDecision(BarrierKind.ASK, True, reasons)
        if not evidence_paths:
            reasons.append("no evidence path")
            return BarrierDecision(BarrierKind.ASK, True, reasons)
        if not dual_channel_ok:
            reasons.append("dual-channel proof not verified")
            return BarrierDecision(BarrierKind.ASK, True, reasons)
        return BarrierDecision(BarrierKind.DONE, False, reasons)
