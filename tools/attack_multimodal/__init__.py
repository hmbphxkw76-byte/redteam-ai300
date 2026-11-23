#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-multimodal：跨模态注入的 PyRIT 1.1.0 原生实现。

规格 issue #433；设计 docs/operations/attack-multimodal-design.md。版本锁定 pyrit==1.1.0。
"""
from .steps import STEP_SPECS, STEP_IDS, steps_for_paths

__all__ = ["STEP_SPECS", "STEP_IDS", "steps_for_paths"]
