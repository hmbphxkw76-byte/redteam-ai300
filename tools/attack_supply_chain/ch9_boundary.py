#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 B6 边界路由：运行时拦截（attack-infra B2）vs 产物投毒（本技能）。

事实源 `docs/research/attack-supply-chain-ch9-b6-hardening-canonical.md`
B6-1..B6-5；纯判定，不执行任何攻击载荷（P-4）。
保留公开函数名 `classify`，返回 `BoundaryVerdict`（dict 兼容 shim 零回归）。
"""
from typing import Iterable, Tuple

from .ch9_boundary_model import (
    ARTIFACT, RUNTIME, TRANSFER_ARTIFACT, TRANSFER_RUNTIME,
    BoundaryVerdict,
)

# 有序信号词表（轻量版常量提升，显式化歧义判定）。
RUNTIME_SIGNALS: Tuple[str, ...] = (
    "sidecar", "initcontainer", "request-queue", "共享卷", "exec",
)
ARTIFACT_SIGNALS: Tuple[str, ...] = (
    "model", "artifact", "minio", "ecr", "registry", "dataset", "依赖", "投毒",
)


def _hits(text: str, signals: Iterable[str]) -> Tuple[str, ...]:
    return tuple(dict.fromkeys(s for s in signals if s in text))


def classify(observation: str, step_id: str = "sc-b6") -> BoundaryVerdict:
    """路由判定：工件信号优先；双向信号标 ambiguous 供人工复核（B6-3）。"""
    text = (observation or "").lower()
    art = _hits(text, ARTIFACT_SIGNALS)
    run = _hits(text, RUNTIME_SIGNALS)
    command = "grep -iE '<signal>' <observation>   # 边界路由：纯文本判定"
    output = ("artifact=%s runtime=%s" % (list(art), list(run)))[:800] or "（无信号）"
    shot = "screenshot --step %s --kind transcript" % step_id
    if art and run:
        return BoundaryVerdict(
            step_id=step_id, owner=ARTIFACT, reason="ambiguous",
            confidence="ambiguous",
            transfer_to=TRANSFER_ARTIFACT + " | " + TRANSFER_RUNTIME,
            summary="双向信号：本技能优先，人工复核后再转交",
            command=command, output=output, shot_cmd=shot)
    if art:
        return BoundaryVerdict(
            step_id=step_id, owner=ARTIFACT, reason="artifact_signals",
            confidence="high", transfer_to=TRANSFER_ARTIFACT,
            summary="工件/投毒信号 → 本技能既有 Ch8 模块",
            command=command, output=output, shot_cmd=shot)
    if run:
        return BoundaryVerdict(
            step_id=step_id, owner=RUNTIME, reason="runtime_signals",
            confidence="high", transfer_to=TRANSFER_RUNTIME,
            summary="运行时 sidecar 拦截信号 → 转 attack-infra B2",
            command=command, output=output, shot_cmd=shot)
    return BoundaryVerdict(
        step_id=step_id, owner="", reason="no_signal", confidence="none",
        transfer_to="", summary="无边界信号，不转交",
        command=command, output=output, shot_cmd=shot)
