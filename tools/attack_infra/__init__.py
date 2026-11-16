#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-infra：AI 基础设施与部署利用执行器。

公开入口：
  - `run(ctx)` / `run_all(ctx)`：按 `RunContext` 执行 8 步
  - `main(argv)`：命令行入口（`python tools/attack_infra/cli.py`）

设计记录：`docs/operations/attack-infra-design.md`；事实源：
`docs/research/attack-infra-canonical.md`；规格：#213。
"""
from .model import (  # noqa: F401
    ABSENT_REASONS,
    BLOCKED_REASONS,
    STEP_IDS,
    CredentialHint,
    Endpoint,
    Finding,
    Outcome,
    RunContext,
    RunRequest,
    RunReport,
    StepVerdict,
)
from .runner import attach_evidence, run, run_all  # noqa: F401

__all__ = [
    "ABSENT_REASONS", "BLOCKED_REASONS", "STEP_IDS", "CredentialHint",
    "Endpoint", "Finding", "Outcome", "RunContext", "RunRequest", "RunReport",
    "StepVerdict", "attach_evidence", "run", "run_all", "main",
]


def main(argv=None):
    from .cli import main as _main
    return _main(argv)
