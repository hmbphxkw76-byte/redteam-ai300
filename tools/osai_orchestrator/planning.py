"""计划与人在环：3–7 步规划、增量精化、人在环控制。

判据取自 performers.go:96-189、flow_manager.go:43-829，
以纯数据操作实现，不触碰任何既有技能。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .models import Verdict


@dataclass
class PlanStep:
    step_id: str
    action: str
    verify: str
    pitfalls: str = ""
    role: str = "executor"


class Planner:
    """生成 3–7 步清单并包裹任务上下文（A-10）。"""

    MIN_STEPS = 3
    MAX_STEPS = 7

    def build(self, request: str, steps: list[PlanStep]) -> tuple[Verdict, list[str]]:
        problems: list[str] = []
        if not request.strip():
            problems.append("empty request")
        if not (self.MIN_STEPS <= len(steps) <= self.MAX_STEPS):
            problems.append("step count outside %d-%d" % (self.MIN_STEPS, self.MAX_STEPS))
        ids = [s.step_id for s in steps]
        if len(ids) != len(set(ids)):
            problems.append("duplicate step_id")
        for s in steps:
            if not s.verify.strip():
                problems.append("step %s has no verification point" % s.step_id)
        return (Verdict.BLOCKED if problems else Verdict.PASS), problems

    def wrap(self, request: str, steps: list[PlanStep]) -> str:
        lines = ["<task_assignment>", "<request>%s</request>" % request, "<plan>"]
        for s in steps:
            lines.append(
                "<step id='%s' role='%s'>%s | verify: %s</step>"
                % (s.step_id, s.role, s.action, s.verify)
            )
        lines.append("</plan></task_assignment>")
        return "\n".join(lines)


@dataclass
class RefineOps:
    add: list[PlanStep] = field(default_factory=list)
    remove: list[str] = field(default_factory=list)
    modify: dict[str, PlanStep] = field(default_factory=dict)
    reorder: list[str] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.add or self.remove or self.modify or self.reorder)


class Refiner:
    """增量精化：已完成步骤不可变，四类操作受控（B-01）。"""

    def apply(
        self,
        completed: list[PlanStep],
        remaining: list[PlanStep],
        ops: RefineOps,
        max_steps: int = 7,
    ) -> tuple[Verdict, list[PlanStep], list[str]]:
        problems: list[str] = []
        completed_ids = {s.step_id for s in completed}
        for sid in ops.remove:
            if sid in completed_ids:
                problems.append("cannot remove completed step %s" % sid)
        for sid in ops.modify:
            if sid in completed_ids:
                problems.append("cannot modify completed step %s" % sid)
        if problems:
            return Verdict.BLOCKED, list(remaining), problems

        by_id = {s.step_id: s for s in remaining}
        for sid in ops.remove:
            by_id.pop(sid, None)
        for step in ops.add:
            if step.step_id in by_id or step.step_id in completed_ids:
                problems.append("duplicate step_id %s" % step.step_id)
            else:
                by_id[step.step_id] = step
        for sid, step in ops.modify.items():
            if sid in by_id:
                by_id[sid] = step
            else:
                problems.append("unknown step %s" % sid)

        result = list(by_id.values())
        if ops.reorder:
            order = {sid: i for i, sid in enumerate(ops.reorder)}
            unknown = [sid for sid in order if sid not in by_id]
            problems.extend("unknown reorder step %s" % sid for sid in unknown)
            result.sort(key=lambda s: order.get(s.step_id, 1 << 30))
        if len(result) > max_steps:
            problems.append("modified step count exceeds %d" % max_steps)
        return (Verdict.BLOCKED if problems else Verdict.PASS), result, problems


class ControlAction(str, Enum):
    STATUS = "get_status"
    STOP = "stop"
    SUBMIT_INPUT = "submit_input"
    PATCH_STEPS = "patch_steps"
    WAIT = "wait"


@dataclass
class ControlResult:
    action: ControlAction
    state: str
    effect: str
    accepted: bool


class HumanInLoop:
    """人在环五类控制：状态先于变更、一次一动作、指令绑定范围（B-02）。"""

    def __init__(self) -> None:
        self._state = "idle"
        self._notes: list[str] = []

    def apply(self, action: ControlAction, scope: str, payload: str = "") -> ControlResult:
        if action is ControlAction.STATUS:
            return ControlResult(action, self._state, "read only", True)
        if action is ControlAction.STOP:
            self._state = "stopped"
            self._notes.append("completed items and unwritten evidence must be listed")
            return ControlResult(action, self._state, "stopped current task", True)
        if action is ControlAction.SUBMIT_INPUT:
            if not scope.strip():
                return ControlResult(action, self._state, "scope required", False)
            self._notes.append("input bound to scope: %s" % scope)
            return ControlResult(action, self._state, "instruction queued for next step", True)
        if action is ControlAction.PATCH_STEPS:
            self._notes.append("steps patched: %s" % (payload or "no payload"))
            return ControlResult(action, self._state, "effective at next execution point", True)
        self._state = "waiting"
        return ControlResult(action, self._state, "waiting for completion", True)

    @property
    def notes(self) -> list[str]:
        return list(self._notes)
