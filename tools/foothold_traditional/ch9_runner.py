#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 两步编排 + 证据附着（阶段 6 设计 §2）。"""
from typing import Any, Callable, List

from . import ch9_entry, ch9_evidence
from .ch9_model import TriadVerdict

STEPS: dict = {
    "trad-09": ch9_entry.ssrf_credential_entry,
    "trad-10": ch9_entry.gpu_foothold_entry,
}


def run_ch9(ctx: Any, step_ids=("trad-09", "trad-10"),
            attach: Callable = ch9_evidence.emit_strict_evidence) -> List[TriadVerdict]:
    """按 step_ids 顺序执行并附着证据；未知 step 直接报错。"""
    unknown = [s for s in step_ids if s not in STEPS]
    if unknown:
        raise ValueError("未知 Ch9 步骤: %s" % ", ".join(unknown))
    verdicts: List[TriadVerdict] = []
    for sid in step_ids:
        verdict = STEPS[sid](ctx)
        if attach is not None:
            verdict = attach(ctx, verdict)
        verdicts.append(verdict)
    return verdicts
