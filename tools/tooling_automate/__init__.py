"""tooling-automate：红队演练编排层（S-1 统一编排入口）。

只调用并串联既有共享工具（collect_evidence 与各校验脚本），不重写判据、
不含攻击逻辑、零第三方依赖。设计见 docs/operations/tooling-automate-design.md。
"""
from __future__ import annotations

from .manifest import (
    Manifest,
    ManifestError,
    Task,
    UsageError,
    load_manifest,
    parse_step,
)
from .runner import (
    CommandRunner,
    PlanResult,
    RunOutcome,
    StepResult,
    SubprocessRunner,
    run_plan,
)
from .reuse import build_argv, build_collect_evidence_argv, build_validator_argv
from .summary import compute_coverage, render_markdown
from .cli import main

__all__ = [
    "Manifest", "ManifestError", "Task", "UsageError", "load_manifest", "parse_step",
    "CommandRunner", "PlanResult", "RunOutcome", "StepResult", "SubprocessRunner",
    "run_plan", "build_argv", "build_collect_evidence_argv", "build_validator_argv",
    "compute_coverage", "render_markdown", "main",
]
