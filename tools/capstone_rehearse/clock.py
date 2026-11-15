#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S-2 seam：演练时钟（设计 §4）。

默认耗时取 `GOVERNANCE.md#L171`（§5.4「宜」，非官方强制）的建议值，
实测耗时由演练取证输入；二者分字段，缺省时标「未实测」（AC-08）。
"""
from __future__ import annotations

import datetime
from typing import Dict, Optional

# (键, 时间线段标签, 关键节点)
SEGMENTS = (
    ("recon_foothold", "0–4h 侦察/立足点", "第 0h 起 threat-model → recon-ai → foothold"),
    ("chain_ai", "4–16h 链式推进与 AI 向量利用", "第 4h 起链式横向 + 七个子技能"),
    ("converge", "16–20h 收敛与证据补录", "第 16h 起 loot / 域控 / 边打边写"),
    ("buffer", "≥4h 缓冲", "证据补录与报告初稿必须在此窗口内（§4.5/§5.4）"),
)
DECOY_TIMEBOX = "decoy_timebox"
EXAM_HOURS = 24.0
DEFAULT_DURATIONS = {
    "recon_foothold": 4.0,
    "chain_ai": 12.0,
    "converge": 4.0,
    "buffer": 4.0,
    DECOY_TIMEBOX: 0.5,  # §5.3 建议 ≤30min
}


class Clock:
    """S-2 seam 接口：durations() / measured() / now()。"""

    def durations(self) -> Dict[str, float]:
        raise NotImplementedError

    def measured(self) -> Dict[str, Optional[float]]:
        return {}

    def now(self) -> datetime.datetime:
        raise NotImplementedError


class FixedClock(Clock):
    """测试 adapter：固定时间点 + 注入耗时，保证 AC-18 确定性。"""

    def __init__(self, durations: Optional[Dict[str, float]] = None,
                 measured: Optional[Dict[str, float]] = None,
                 now: Optional[datetime.datetime] = None):
        self._durations = dict(DEFAULT_DURATIONS)
        if durations:
            for key, value in durations.items():
                self._durations[key] = float(value)
        self._measured = dict(measured or {})
        self._now = now or datetime.datetime(2026, 11, 15, 9, 0, 0)

    def durations(self) -> Dict[str, float]:
        return dict(self._durations)

    def measured(self) -> Dict[str, Optional[float]]:
        return dict(self._measured)

    def now(self) -> datetime.datetime:
        return self._now


class SystemClock(FixedClock):
    """生产 adapter：当前时间 + §5.4 建议值（实测值需显式注入）。"""

    def now(self) -> datetime.datetime:
        return datetime.datetime.now().astimezone()
