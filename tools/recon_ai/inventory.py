#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""资产清单组装：探测判据 → 七字段契约资产 → 双态输出。

只做「组装 + 契约校验」，不做 IO、不做网络（可被纯单元测试覆盖）。
"""
from urllib.parse import urlparse

from .model import Asset, AssetInventory, Category, Existence
from .probes import STEP_SPECS
from . import policy

SLUGS = {
    Category.LLM_ENGINE: "llm",
    Category.MODEL_SERVICE: "model",
    Category.RAG: "rag",
    Category.VECTOR_DB: "vector",
    Category.AGENT: "agent",
    Category.MCP: "mcp",
    Category.GUARDRAIL: "guardrail",
}
ORDER = (Category.LLM_ENGINE, Category.MODEL_SERVICE, Category.RAG,
         Category.VECTOR_DB, Category.AGENT, Category.MCP, Category.GUARDRAIL)


def host_of(target):
    """从目标 URL 取主机名；无 scheme 时按整体处理。"""
    parsed = urlparse(target if "//" in target else "//" + target)
    return parsed.hostname or target


def build(judgements, target, profile, failed_steps=None, endpoints=None,
          phases=None, hints=None, tried=None, extra_signals=0):
    """按 step 判定结果组装清单。

    `judgements`：{step_id: Judgement}；`endpoints`：{step_id: 首选端点}。
    存在 → 建资产；不可判定/未执行 → 不建资产，写入未决面与缺口台账
    （保留「未发现 ≠ 不存在」，但不把未知伪装成资产）。
    """
    host = host_of(target)
    endpoints = endpoints or {}
    phases = phases or {}
    hints = hints or {}
    tried = tried or {}
    step_of_category = {spec.category: spec.step_id for spec in STEP_SPECS}
    assets, undetermined, gaps = [], [], []
    present_categories = []
    index = 0
    for category in ORDER:
        step_id = step_of_category[category]   # 单一事实源：probes.STEP_SPECS
        judgement = judgements.get(step_id)
        if judgement is None:
            gaps.append({"category": category.value, "step_id": step_id,
                         "basis": "步骤未执行或失败（见失败步骤）",
                         "tried": tried.get(step_id, []),
                         "next": "复跑该步骤或人工确认"})
            continue
        if judgement.existence == Existence.ABSENT:
            continue
        if judgement.existence == Existence.UNDETERMINED:
            undetermined.append(category.value)
            gaps.append({"category": category.value, "step_id": step_id,
                         "basis": judgement.basis or judgement.note or "无",
                         "tried": tried.get(step_id, []),
                         "next": "主动档定向探测或人工确认"})
            continue
        index += 1
        judged_endpoint = (judgement.context or {}).get("endpoint") or ""
        assets.append(Asset(
            asset_id="ai-%s-%s-%02d" % (SLUGS[category], host, index),
            category=category.value,
            product=judgement.product or "不可判定",
            version=judgement.version or "不可判定",
            endpoint=judged_endpoint or endpoints.get(step_id) or "不可判定",
            credential_hint=hints.get(step_id) or "无",
            evidence_step=step_id,
            phase=phases.get(step_id, ""),
        ))
        present_categories.append(category.value)

    decoy, decoy_reason = policy.judge_decoy(present_categories,
                                             extra_signals=extra_signals)
    return AssetInventory.create(
        target=target, profile=profile, assets=assets,
        decoy_suspected=decoy, decoy_reason=decoy_reason,
        timebox_minutes=policy.TIMEOUT_MINUTES,
        failed_steps=list(failed_steps or []),
        undetermined=undetermined, gaps=gaps,
    )
