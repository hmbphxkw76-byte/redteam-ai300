#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 B6：运行时拦截（attack-infra B2）与产物投毒的职责边界声明。

职责：给定一项 Ch9 观察，判定归本技能（产物/工件投毒）还是转交 attack-infra
（运行时 sidecar 拦截），避免两技能越界重复实现。纯判定，不执行攻击。
"""
from typing import Any, Dict

RUNTIME_SIGNALS = ("sidecar", "initcontainer", "request-queue", "共享卷", "exec")
ARTIFACT_SIGNALS = ("model", "artifact", "minio", "ecr", "registry", "dataset", "依赖", "投毒")

ARTIFACT = "attack-supply-chain"
RUNTIME = "attack-infra"


def classify(observation: str) -> Dict[str, Any]:
    """返回 {owner, reason, confidence}；双向信号时产物优先并标记歧义。"""
    text = (observation or "").lower()
    art = [s for s in ARTIFACT_SIGNALS if s in text]
    run = [s for s in RUNTIME_SIGNALS if s in text]
    if art:
        return {"owner": ARTIFACT, "reason": "artifact_signals:%s" % ",".join(art),
                "confidence": "high" if not run else "ambiguous"}
    if run:
        return {"owner": RUNTIME, "reason": "runtime_signals:%s" % ",".join(run),
                "confidence": "high"}
    return {"owner": "", "reason": "no_signal", "confidence": "none"}
