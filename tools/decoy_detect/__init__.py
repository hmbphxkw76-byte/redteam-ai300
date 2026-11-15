#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""decoy-detect：诱饵机识别与判定（P1 / D2 / 计分单元：通用）。

公开接口（深模块）
  - `run_scan(scan, timebox_limit_seconds=...)` → `RunReport`
  - `cli.main(argv)`                            → 退出码

本技能是环境级诱饵判定，非攻击框架（对齐框架矩阵 ⑭：纯侦察 + 人工 + 许可 AI，
不引入 PyRIT/garak/promptfoo）。行为唯一来源 `skills/decoy-detect/SKILL.md`；
证据格式唯一来源 `tools/collect_evidence.py`（C1 单一事实源）。
"""
from .model import (Dimension, DecoyJudgment, HostSignals, JudgmentConclusion,
                    ScanInput, load_scan)
from .runner import RunReport, run_scan

__all__ = [
    "Dimension", "DecoyJudgment", "HostSignals", "JudgmentConclusion",
    "ScanInput", "RunReport", "load_scan", "run_scan",
]
__version__ = "1.0.0"
