#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-multi-agent：多智能体/A2A 操纵（D4 · P1 · AI向量机）。

公开面只有四项：`run_attack`（唯一入口）、`Runtime`（四缝注入点）、
数据模型（`AttackRequest` / `AttackReport` / `StepVerdict` / `Observation` / `Signals` / `LEVELS`）、
框架缝（`Scanner` / `A2ASecBenchAdapter` / `OBJECT_GRAPH`）。
其余模块为实现细节，可自由重构而不影响调用方（深层模块原则）。
"""
from .grade import LEVELS, derive, grade
from .model import (AttackReport, AttackRequest, Observation, Signals, StepVerdict,
                    before_after_diff, find_flags, find_secrets, message_accepted,
                    parse_topology, redact)
from .runner import OBJECT_GRAPH, Runtime, run_attack
from .scanner import (A2ASecBenchAdapter, AgentCardFinding, BuiltinAnalyzer,
                      Scanner)
from .steps import STEP_BY_ID, STEP_IDS, STEP_SPECS, steps_for_paths

__all__ = [
    "run_attack", "Runtime", "OBJECT_GRAPH",
    "AttackRequest", "AttackReport", "StepVerdict", "Observation", "Signals",
    "LEVELS", "grade", "derive",
    "Scanner", "BuiltinAnalyzer", "A2ASecBenchAdapter", "AgentCardFinding",
    "STEP_IDS", "STEP_SPECS", "STEP_BY_ID", "steps_for_paths",
    "find_secrets", "find_flags", "redact", "parse_topology",
    "message_accepted", "before_after_diff",
]
