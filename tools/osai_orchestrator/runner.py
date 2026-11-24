"""S-1 统一入口：CLI 与库调用共用的薄编排层，runner 可注入。

只把已实现的能力按步骤串联，不含攻击逻辑、不重写判据、不连接真实目标。
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import Callable, Protocol

from .models import GateResult, Verdict, LimitConfig, AnonymizeConfig
from .supervision import ExecutionMonitor, Reflector, ToolCallBudget, Barrier, BarrierKind
from .planning import Planner, Refiner, HumanInLoop, ControlAction
from .governance import (
    SummaryMarker, ContextCompactor, Anonymizer, MemoryWhitelist,
    IndependentReviewer, ReviewItem, TemplateOverlay, Ontology,
)
from .tooling import (
    TypedRegistry, CallIDNormalizer, ErrorClassifier, RetryPolicy, BoundedRetriever,
)


@dataclass
class RunOutcome:
    returncode: int
    stdout: str = ""
    stderr: str = ""


class CommandRunner(Protocol):
    def run(self, argv) -> RunOutcome:
        ...


class SubprocessRunner:
    def run(self, argv) -> RunOutcome:
        try:
            proc = subprocess.run(list(argv), capture_output=True, text=True)
        except FileNotFoundError as exc:
            return RunOutcome(127, "", str(exc))
        return RunOutcome(proc.returncode, proc.stdout or "", proc.stderr or "")


@dataclass
class OrchestrationResult:
    gates: list[GateResult] = field(default_factory=list)
    artifacts: dict[str, object] = field(default_factory=dict)
    exit_code: int = 0

    @property
    def passed(self) -> bool:
        return all(g.ok for g in self.gates) and self.exit_code == 0


class Orchestrator:
    """能力域组合入口：每个方法对应一类可验证能力，全部无副作用。"""

    def __init__(
        self,
        limits: LimitConfig | None = None,
        anon: AnonymizeConfig | None = None,
        registry: TypedRegistry | None = None,
    ) -> None:
        self.limits = limits or LimitConfig()
        self.monitor = ExecutionMonitor(self.limits)
        self.reflector = Reflector(self.limits.reflector_after)
        self.budget = ToolCallBudget(self.limits)
        self.barrier = Barrier()
        self.planner = Planner()
        self.refiner = Refiner()
        self.hil = HumanInLoop()
        self.compactor = ContextCompactor()
        self.anonymizer = Anonymizer(anon)
        self.whitelist = MemoryWhitelist()
        self.reviewer = IndependentReviewer()
        self.overlay = TemplateOverlay({})
        self.ontology = Ontology()
        self.registry = registry or TypedRegistry()
        self.normalizer = CallIDNormalizer()
        self.classifier = ErrorClassifier()
        self.retry = RetryPolicy()
        self.retriever = BoundedRetriever()

    def supervise_step(self, tool: str, advancing: bool) -> GateResult:
        verdict = self.monitor.observe(tool, advancing)
        return GateResult("execution-monitor", verdict.verdict, "%d/%d" % (
            verdict.same_tool_count, verdict.total_count), [verdict.advice] if verdict.advice else [])

    def reflect_step(self, failures: int, has_action: bool, near_limit: bool) -> GateResult:
        result = self.reflector.reflect(failures, has_action, near_limit)
        return GateResult("reflector", Verdict.PASS if result.decision.value != "terminate" else Verdict.BLOCKED,
                          result.decision.value, [result.reason])

    def budget_step(self, role: str, used: int, pending: int) -> GateResult:
        verdict, findings = self.budget.check(role, used, pending)
        return GateResult("tool-budget", verdict, self.budget.ceiling(role), findings)

    def barrier_step(self, met: bool, paths: list[str], dual: bool, confirm: bool) -> GateResult:
        decision = self.barrier.decide(met, paths, dual, confirm)
        return GateResult("barrier", Verdict.PASS if decision.kind is BarrierKind.DONE else Verdict.BLOCKED,
                          decision.kind.value, decision.reasons)

    def anonymize(self, text: str) -> str:
        return self.anonymizer.anonymize(text)

    def review(self, items: list[ReviewItem]) -> GateResult:
        verdict, findings = self.reviewer.review(items)
        return GateResult("independent-review", verdict, "%d items" % len(items), findings)
