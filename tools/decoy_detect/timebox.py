#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""≤30min 时间盒追踪（纯类，可注入时钟）。

SKILL.md 第 2 节：单台判定硬性时间盒 ≤30min；超时即记录「不确定-已放弃」。
时间盒值经构造参数注入（默认 1800s），便于测试与合规调整（GOVERNANCE §5.3 建议 ≤30min）。
"""
import time

DEFAULT_LIMIT_SECONDS = 30 * 60


class TimeBoxTracker:
    """按主机记录判定耗时并判定是否超盒。

    - `start/stop` 走真实时钟（可注入 clock=mock），用于运行时计时；
    - `record` 直接写入已知耗时，用于消费上游枚举已测量的 elapsed（夹具场景）。
    """

    def __init__(self, limit_seconds=DEFAULT_LIMIT_SECONDS, clock=None):
        self.limit_seconds = int(limit_seconds)
        self._clock = clock or time.monotonic
        self._starts = {}
        self._elapsed = {}

    def start(self, host_id):
        self._starts[host_id] = self._clock()

    def stop(self, host_id):
        start = self._starts.pop(host_id, None)
        if start is not None:
            self._elapsed[host_id] = self._clock() - start
        return self._elapsed.get(host_id, 0.0)

    def record(self, host_id, elapsed_seconds):
        """直接登记已知耗时（上游枚举测量值）。"""
        try:
            self._elapsed[host_id] = max(0.0, float(elapsed_seconds))
        except (TypeError, ValueError):
            self._elapsed[host_id] = 0.0
        return self._elapsed[host_id]

    def elapsed(self, host_id):
        if host_id in self._elapsed:
            return self._elapsed[host_id]
        if host_id in self._starts:
            return self._clock() - self._starts[host_id]
        return 0.0

    def exceeded(self, host_id, limit_seconds=None):
        limit = self.limit_seconds if limit_seconds is None else int(limit_seconds)
        return self.elapsed(host_id) > limit
