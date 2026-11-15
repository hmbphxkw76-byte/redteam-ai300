#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诱饵机判定：三维度初筛 + ≤30min 时间盒（SKILL 执行体 §3 / §5.3）。"""
from datetime import datetime

from .model import DecoyVerdict, DECOY

TIMEBOX_MINUTES = 30
# 三维度：行为（无 AI 面）/ 漏洞缺失 / 无价值特征
DIMENSION_KEYS = ("behavior", "vuln_absent", "no_value")


def judge_decoy(asset, dims=None, elapsed_minutes=0.0, now=None, reason=""):
    """判定单台资产是否诱饵机。

    - 时间盒硬约束：elapsed > 30min → 判定不确定 + 主动放弃，不在 0 分主机空耗。
    - 时间盒内三维度命中 ≥2 → 诱饵机；否则维持计分目标。
    """
    dims = dims or {}
    now = now if now is not None else datetime.now().astimezone()
    ts = now.isoformat(timespec="seconds") if hasattr(now, "isoformat") else str(now)

    if elapsed_minutes > TIMEBOX_MINUTES:
        return DecoyVerdict(
            asset_id=asset.asset_id,
            verdict="判定不确定",
            dims=dims,
            elapsed_minutes=elapsed_minutes,
            timebox_minutes=TIMEBOX_MINUTES,
            abandoned=True,
            reason=reason or ("时间盒超时（%.0fmin > %dmin），主动放弃，"
                              "不在 0 分主机空耗" % (elapsed_minutes, TIMEBOX_MINUTES)),
            timestamp=ts,
        )

    hit = sum(1 for k in DIMENSION_KEYS if dims.get(k))
    if hit >= 2:
        verdict = DECOY
        abandoned = True
        reason = reason or ("三维度命中 %d/3（行为/漏洞缺失/无价值特征），判定诱饵机" % hit)
    else:
        verdict = "非诱饵"
        abandoned = False
        reason = reason or ("三维度命中不足（%d/3），维持计分目标" % hit)

    return DecoyVerdict(
        asset_id=asset.asset_id,
        verdict=verdict,
        dims=dims,
        elapsed_minutes=elapsed_minutes,
        timebox_minutes=TIMEBOX_MINUTES,
        abandoned=abandoned,
        reason=reason,
        timestamp=ts,
    )
