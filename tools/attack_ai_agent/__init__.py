#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-ai-agent 的 PyRIT v1.1.0 原生实现（单一公开入口）。

本包是 `skills/attack-ai-agent/SKILL.md` 声明攻击逻辑的运行时落地，覆盖
OWASP ASI01 提示注入 / ASI06 记忆滥用 / ASI02 工具集成滥用三条路径。

设计约束（issue #83 规格 v2 + 设计记录方案 A）：
  - `run_attack` 是唯一外部 seam；对象图构造全部收敛在其后的 paths / backends 层。
  - `pyrit` 只在 RealPyRITBackend 的方法体内延迟导入；本包顶层绝不导入 pyrit，
    使 CI 在未安装 pyrit 的环境仍可导入并运行标准库测试（AC-23 / ADR-0003）。
  - 每个攻击步骤 1:1 对应一次 `collect_evidence.py --step aia-NN --strict`（B4）。
  - 版本锁定 `pyrit==1.1.0`；间接注入按 B7 受控例外使用
    `pyrit.executor.workflow.XPIATestWorkflow`。

公开 API：run_attack、AttackRequest、AttackReport、StepVerdict、FakePyRITBackend。
"""
from .backends import BackendFactory, FakePyRITBackend, RealPyRITBackend
from .runner import AttackReport, AttackRequest, StepVerdict, run_attack
from .steps import STEP_IDS, STEP_SPECS, StepSpec

__all__ = [
    "run_attack",
    "AttackRequest",
    "AttackReport",
    "StepVerdict",
    "StepSpec",
    "STEP_IDS",
    "STEP_SPECS",
    "BackendFactory",
    "FakePyRITBackend",
    "RealPyRITBackend",
]

PYRIT_VERSION = "1.1.0"
