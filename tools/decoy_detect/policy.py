#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诱饵判定策略（纯函数）。

SKILL.md 第 2 节：命中三维度中 ≥2 类即判诱饵；仅 1 类命中须结合威胁模型交叉验证，
避免误杀真高价值目标。第 4 节：与 threat-model 初筛冲突时以多维度交叉验证为准。
"""
from .model import JudgmentConclusion

MIN_DECOY_DIMENSIONS = 2


def decide(hit_dimensions, cross_validated=False, threat_model_decoy=False):
    """根据命中维度数与交叉验证状态给出结论。

    - ≥2 维度命中 → 诱饵（DECOY）；
    - 仅 1 维度命中 → 经交叉验证方可判诱饵，否则「不确定-已放弃」（不静默判计分目标）；
    - 0 维度命中 → 计分目标；若 threat-model 标记疑似诱饵且经交叉验证，则降为「不确定-已放弃」。
    """
    hits = len(hit_dimensions or [])
    if hits >= MIN_DECOY_DIMENSIONS:
        return JudgmentConclusion.DECOY
    if hits == 1:
        if cross_validated or threat_model_decoy:
            return JudgmentConclusion.DECOY
        return JudgmentConclusion.UNCERTAIN_ABANDONED
    # hits == 0
    if threat_model_decoy and cross_validated:
        return JudgmentConclusion.UNCERTAIN_ABANDONED
    return JudgmentConclusion.SCORED


def abandonment_reason(conclusion, hit_dimensions, timebox_exceeded):
    """给出放弃理由（v2 AC7 第 4 字段）；计分目标不产出放弃理由。"""
    if conclusion == JudgmentConclusion.SCORED:
        return ""
    hits = len(hit_dimensions or [])
    if timebox_exceeded:
        return "时间盒超时（>%dmin），按 §5.3 记录「不确定-已放弃」，不在 0 分主机空耗" % 30
    if hits >= MIN_DECOY_DIMENSIONS:
        return "命中 %d 个维度（≥2），判为诱饵，主动放弃以避免 0 分空耗" % hits
    if hits == 1:
        return "仅单维度命中且未经交叉验证，主动放弃并待 threat-model 复核"
    return "threat-model 标记疑似诱饵，经交叉验证后放弃"
