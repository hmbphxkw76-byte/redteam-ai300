#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""计分目标键集的唯一事实源（GOVERNANCE §2.1/§2.2）。

`tools.report_exam` 与 `tools/verify_evidence.py` 都按这 8 个键组织报告与校验；
键集只在此定义一次，两侧引用（AGENTS.md C1）。门禁侧不得反向依赖下游组装器。
"""

SCORED_HOSTS = (
    "chain1-host1", "chain1-host2", "chain1-host3",
    "chain2-host1", "chain2-host2", "chain2-host3",
    "standalone", "domain-controller",
)
STANDALONE_KEY = "standalone"
DOMAIN_CONTROLLER_KEY = "domain-controller"

# 分值多重集（§2.2.1/§2.2.2 推导）：4 台 AI向量机 15 + 独立机 15 + 2 台传统向量机 10 + 域控 5
POINT_PATTERN = {15: 5, 10: 2, 5: 1}
TOTAL_POINTS = sum(points * count for points, count in POINT_PATTERN.items())
