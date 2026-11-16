"""S-1 统一编排入口与批量执行（切片 B）。

only invokes & chains shared tools via an injectable CommandRunner；
外部命令执行器可注入替身，使测试无需真实演练目标。
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from typing import Protocol

from .manifest import Manifest, UsageError, parse_step
from .reuse import build_argv


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
            p = subprocess.run(list(argv), capture_output=True, text=True)
        except FileNotFoundError as exc:
            return RunOutcome(127, "", str(exc))
        return RunOutcome(p.returncode, p.stdout or "", p.stderr or "")


@dataclass
class StepResult:
    task: object
    argv: list
    outcome: RunOutcome
    strict_ok: bool


@dataclass
class PlanResult:
    results: list = field(default_factory=list)
    coverage: float = 0.0
    manual: list = field(default_factory=list)
    exit_code: int = 0


def _ordered(tasks):
    def key(t):
        try:
            _, idx = parse_step(t.step)
        except UsageError:
            return 1 << 30
        return idx

    return sorted(tasks, key=key)


def run_plan(manifest, runner=None, strict=True, dry_run=False) -> PlanResult:
    if runner is None:
        runner = SubprocessRunner()
    results: list = []
    manual = list(manifest.manual)
    exit_code = 0
    for task in _ordered(manifest.tasks):
        if task.is_manual:
            continue
        argv = build_argv(task, strict=strict)
        if dry_run:
            results.append(StepResult(task, argv, RunOutcome(0, "", ""), True))
            continue
        outcome = runner.run(argv)
        strict_ok = outcome.returncode == 0
        results.append(StepResult(task, argv, outcome, strict_ok))
        if not strict_ok:
            exit_code = 1  # 门禁失败
    total = len(manifest.scriptable)
    passed = sum(1 for r in results if not r.task.is_manual and r.outcome.returncode == 0)
    coverage = (passed / total) if total else 0.0
    return PlanResult(results=results, coverage=coverage, manual=manual, exit_code=exit_code)
