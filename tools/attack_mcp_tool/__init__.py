#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-mcp-tool：MCP 与工具面滥用（P0 · D7 · AI向量机）。

公开面只有三项：`run_attack`（唯一入口）、`Runtime`（三缝注入点）、
数据模型（`AttackRequest` / `AttackReport` / `StepVerdict` / `LEVELS`）。
其余模块为实现细节，可自由重构而不影响调用方（深层模块原则）。
"""
from .grade import LEVELS
from .model import (AttackReport, AttackRequest, Observation, Signals, StepVerdict,
                    ToolDescriptor, ToolSurface, find_secrets)
from .runner import OBJECT_GRAPH, Runtime, run_attack
from .steps import STEP_IDS, STEP_SPECS, steps_for_paths

__all__ = [
    "run_attack", "Runtime", "OBJECT_GRAPH",
    "AttackRequest", "AttackReport", "StepVerdict", "Observation", "Signals",
    "ToolDescriptor", "ToolSurface", "find_secrets",
    "LEVELS", "STEP_IDS", "STEP_SPECS", "steps_for_paths",
]
