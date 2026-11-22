#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""B6 类型化边界结论（唯一事实源，P-1）。

不 import 本项目任何模块；owner/reason 取固定枚举，transfer_to 为字面
`路径#锚点` 指针（C1，不跨技能 import）。
"""
from dataclasses import dataclass, field
from typing import Any, Dict

ARTIFACT = "attack-supply-chain"
RUNTIME = "attack-infra"
OWNERS = (ARTIFACT, RUNTIME, "")

REASONS = frozenset((
    "artifact_signals", "runtime_signals", "ambiguous", "no_signal",
))

# 转交目标字面指针（B6-1/B6-2）；非 import，避免跨技能耦合。
TRANSFER_RUNTIME = (
    "tools/attack_infra/ch9_container.py#writable_shared_volume; "
    "tools/attack_infra/ch9_container.py#intercept_verdict")
TRANSFER_ARTIFACT = "tools/attack_supply_chain/poison_engine.py#poison_model"


@dataclass(frozen=True)
class BoundaryVerdict:
    """不可变边界判定；字段与 `collect_evidence.py` 参数同构。"""

    step_id: str
    owner: str
    reason: str
    confidence: str
    transfer_to: str = ""
    summary: str = ""
    command: str = ""
    output: str = ""
    shot_cmd: str = ""
    evidence_path: str = ""
    evidence_ok: bool = True
    evidence_extra: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if self.owner not in OWNERS:
            raise ValueError("未知 owner: %r" % self.owner)
        if self.reason not in REASONS:
            raise ValueError("非既有 reason: %r" % self.reason)

    def __getitem__(self, key: str):
        """dict 兼容 shim：轻量版 `v['owner']` 零回归。"""
        return getattr(self, key)

    def get(self, key: str, default=None):
        """dict 兼容 shim：轻量版 `v.get('transfer_to')` 零回归。"""
        return getattr(self, key, default)
