#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诱饵判定清单质量门校验（纯函数）。

SKILL.md 质量门 / v2 AC8：检出
  1. 缺失五字段中任一字段的条目；
  2. 仅单维度命中却未经交叉验证即排除（判诱饵或静默判计分目标）的条目；
  3. 超时间盒却未按「不确定-已放弃」处置 / 未标记的条目。
返回结构化违规描述列表；空列表 = 过门禁。
"""
from .model import JudgmentConclusion


def validate_quality_gate(judgments, timebox_limit_seconds=1800):
    violations = []
    for j in judgments:
        miss = j.missing_fields()
        if miss:
            violations.append("%s：缺字段 %s" % (j.host_id, "、".join(miss)))

        single = len(j.hit_dimensions or []) == 1
        if single and not j.cross_validated:
            if j.conclusion == JudgmentConclusion.DECOY:
                violations.append(
                    "%s：仅单维度命中即判诱饵但未经交叉验证" % j.host_id)
            elif j.conclusion == JudgmentConclusion.SCORED:
                violations.append(
                    "%s：仅单维度命中却静默判为计分目标（未交叉验证）" % j.host_id)

        over = j.timebox_exceeded or (j.elapsed_seconds > timebox_limit_seconds)
        if over:
            if not j.timebox_exceeded:
                violations.append("%s：耗时超出时间盒但未标记 timebox_exceeded" % j.host_id)
            if j.conclusion != JudgmentConclusion.UNCERTAIN_ABANDONED:
                violations.append(
                    "%s：超时间盒却未按「不确定-已放弃」处置" % j.host_id)
    return violations


def has_decoys(judgments):
    """清单是否至少判定一台诱饵（供摘要/断言复用）。"""
    return any(j.conclusion == JudgmentConclusion.DECOY for j in judgments)
