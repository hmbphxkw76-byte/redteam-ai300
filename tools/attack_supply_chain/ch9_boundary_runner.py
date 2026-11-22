#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B6 判定 + 证据附着编排（阶段 6 设计 §2）。"""
from typing import Any, Callable, List

from . import ch9_boundary, ch9_boundary_evidence
from .ch9_boundary_model import BoundaryVerdict


def run_boundary(observations: List[str], ctx: Any,
                 attach: Callable = ch9_boundary_evidence.emit_strict_evidence,
                 step_prefix: str = "sc-b6") -> List[BoundaryVerdict]:
    """逐观察分类并附着证据；空列表返回空。"""
    verdicts: List[BoundaryVerdict] = []
    for i, obs in enumerate(observations):
        verdict = ch9_boundary.classify(obs, step_id="%s-%d" % (step_prefix, i + 1))
        if attach is not None:
            verdict = attach(ctx, verdict)
        verdicts.append(verdict)
    return verdicts
