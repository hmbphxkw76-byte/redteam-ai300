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
          phases=None, hints=None):
    """按 step 判定结果组装清单。

    `judgements`：{step_id: Judgement}；`endpoints`：{step_id: 首选端点}。
    存在 → 建资产；不可判定 → 也建资产（保留「未发现 ≠ 不存在」）；不存在 → 不建。
    """
    host = host_of(target)
    endpoints = endpoints or {}
    phases = phases or {}
    hints = hints or {}
    step_of_category = {spec.category: spec.step_id for spec in STEP_SPECS}
    assets, undetermined = [], []
    present_categories = []
    index = 0
    for category in ORDER:
        step_id = step_of_category[category]   # 单一事实源：probes.STEP_SPECS
        judgement = judgements.get(step_id)
        if judgement is None or judgement.existence == Existence.ABSENT:
            continue
        index += 1
        asset = Asset(
            asset_id="ai-%s-%s-%02d" % (SLUGS[category], host, index),
            category=category.value,
            product=judgement.product or "不可判定",
            version=judgement.version or "不可判定",
            endpoint=endpoints.get(step_id) or "不可判定",
            credential_hint=hints.get(step_id) or "无",
            evidence_step=step_id,
            phase=phases.get(step_id, ""),
        )
        assets.append(asset)
        if judgement.existence == Existence.PRESENT:
            present_categories.append(category.value)
        else:
            undetermined.append(category.value)

    decoy, decoy_reason = policy.judge_decoy(present_categories)
    return AssetInventory.create(
        target=target, profile=profile, assets=assets,
        decoy_suspected=decoy, decoy_reason=decoy_reason,
        timebox_minutes=policy.TIMEOUT_MINUTES,
        failed_steps=list(failed_steps or []),
        undetermined=undetermined,
    )
