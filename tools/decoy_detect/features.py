#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""三维度特征提取（纯函数，无 IO）。

输入 seam：消费 recon-ai 枚举结果（`present_categories` / `decoy_suspected` /
`decoy_reason`）+ 各主机探测反馈（服务/入口/配置错误/枚举反馈）+ threat-model
诱饵初筛（`threat_model_decoy`）。输出 HostSignals 与命中维度集合。

维度判据（SKILL.md 第 1 节）：
  - 行为特征：无 AI 基础设施面（present_categories 空，或 recon-ai 已判疑似诱饵）；
  - 漏洞缺失：无高价值服务 且 无可达入口 且 无可利用配置错误（无有效攻击面）；
  - 无价值特征：枚举过干净（无 banner/服务）或 信息缺失致无法定位资产 或 与资产清单严重不符。
"""
from .model import Dimension, HostSignals


def extract(record):
    """把一条主机记录映射为 HostSignals（纯函数，缺省按「有面/有价值」保守处理）。"""
    if not isinstance(record, dict):
        record = {}
    present = record.get("present_categories") or []
    decoy_suspected = bool(record.get("decoy_suspected", False))
    # 行为特征信号：present_categories 非空且未被 recon-ai 判疑似诱饵 → 有 AI 面
    ai_surface_present = bool(present) and not decoy_suspected
    try:
        banner_count = int(record.get("banner_service_count", 1))
    except (TypeError, ValueError):
        banner_count = 1
    return HostSignals(
        host_id=str(record.get("host_id") or record.get("target") or "unknown"),
        ai_surface_present=ai_surface_present,
        high_value_service=bool(record.get("high_value_service", True)),
        reachable_entry=bool(record.get("reachable_entry", True)),
        exploitable_misconfig=bool(record.get("exploitable_misconfig", True)),
        banner_service_count=banner_count,
        info_sufficient=bool(record.get("info_sufficient", True)),
        inventory_match=bool(record.get("inventory_match", True)),
        decoy_suspected=decoy_suspected,
        decoy_reason=str(record.get("decoy_reason") or ""),
        notes=str(record.get("notes") or ""),
    )


def classify_dimensions(signals):
    """返回命中的维度列表（顺序固定：行为→漏洞缺失→无价值）。"""
    hits = []
    if not signals.ai_surface_present:
        hits.append(Dimension.BEHAVIOR)
    if (not signals.high_value_service and not signals.reachable_entry
            and not signals.exploitable_misconfig):
        hits.append(Dimension.LEAK_MISSING)
    if (signals.banner_service_count <= 0 or not signals.info_sufficient
            or not signals.inventory_match):
        hits.append(Dimension.NO_VALUE)
    return hits


def explain(signals):
    """为每个命中维度给出可读的具体依据（v2 AC7「具体依据」）。"""
    reasons = {}
    if not signals.ai_surface_present:
        detail = "无 AI 基础设施面（present_categories 为空或 recon-ai 判疑似诱饵）"
        if signals.decoy_reason:
            detail += "；recon-ai 依据：%s" % signals.decoy_reason
        reasons[Dimension.BEHAVIOR.value] = detail
    if (not signals.high_value_service and not signals.reachable_entry
            and not signals.exploitable_misconfig):
        reasons[Dimension.LEAK_MISSING.value] = (
            "枚举后无有效攻击面（无高价值服务 / 无可达入口 / 无可利用配置错误）")
    no_value = []
    if signals.banner_service_count <= 0:
        no_value.append("枚举反馈过干净（0 banner/服务）")
    if not signals.info_sufficient:
        no_value.append("信息缺失致无法定位资产")
    if not signals.inventory_match:
        no_value.append("与资产清单描述严重不符")
    if no_value:
        reasons[Dimension.NO_VALUE.value] = "；".join(no_value)
    return reasons
