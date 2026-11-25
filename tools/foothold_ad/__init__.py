#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""foothold-ad 实现包：AD 域渗透判据、离线工件解析与证据参数组装。

行为规格见 `skills/foothold-ad/SKILL.md`；设计与实施清单见
`docs/operations/foothold-ad-design.md`。仅标准库，零第三方依赖。
"""
from .model import STEP_IDS, STEP_TITLES, VERDICTS, StepResult  # noqa: F401

__all__ = ["STEP_IDS", "STEP_TITLES", "VERDICTS", "StepResult"]
