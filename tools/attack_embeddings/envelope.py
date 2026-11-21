#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""环境相关能力标注（AC-C9/C10）：ALGEN / Vec2Text 在无 lab/无 GPU 时的诚实降级。

原则（GOVERNANCE §6 如实记录）：不静默降级、不伪造结果。AIVP 无独立 embedding
反演 lab（C-1，已核实），重型训练（50k canary / 60h GPU）不属本规格交付；
本模块只做「适用性判定 + 依据留痕」，具备环境时才走真实适配。
"""
from __future__ import annotations

from typing import Dict


def assess_env(capability: str, has_lab: bool = False, has_gpu: bool = False,
               has_write: bool = False, prep_hours: float = 0.0,
               c1_evidence: str = "canonical.md §1.6/§4：AIVP 无独立 embedding 反演 lab") -> Dict[str, object]:
    """返回适用/不适用判定与依据（不执行重型训练）。"""
    if capability not in ("ALGEN", "Vec2Text"):
        raise ValueError("未知能力：%s" % capability)
    if capability == "ALGEN":
        applicable = has_lab and has_write and has_gpu
        reason = ("具备 lab + 向量库写权限 + GPU，可走 canary 对齐" if applicable else
                  "不满足 lab/写权限/GPU，标注不适用（不交付 50k canary 注入）")
    else:
        applicable = has_gpu and prep_hours >= 60
        reason = ("具备 GPU 且准备时间充足（>=60h），可走 inverter+corrector" if applicable else
                  "无 GPU 或准备时间不足，标注不适用（不交付 60h 训练）")
    return {"step": "emb-c10" if capability == "Vec2Text" else "emb-c9",
            "capability": capability, "applicable": applicable,
            "status": "applicable" if applicable else "NOT_APPLICABLE",
            "reason": reason, "c1_evidence": c1_evidence,
            "delivered": "capability stub" if applicable else "not-applicable annotation"}
