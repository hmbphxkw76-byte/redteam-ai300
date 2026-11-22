#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""假设登记册（Ch10 §10.1 Table 1 / A-07 / A-16）。

六字段 + 状态机 + 置信度语义（来源可靠性非正确概率）+ 证伪派生 + 检测规则派生。
纯函数，不读文件、不依赖时钟；外部输入经参数注入（设计 §4 S-4）。
"""
from .model import Assumption, ASSUMPTION_STATUSES, CONFIDENCE_LEVELS

# "absence of evidence" 标记：来源或置信度含此值即归为验证任务
ABSENCE_MARKERS = ("absence of evidence", "缺证", "信息缺失")


def to_register(observations, classification=None):
    """把观察 + 分析师标注合并为假设登记册（六字段完整）。

    observations: [{id, observation, hypothesis, confidence, source, status}, ...]
    classification: 可选 {id: {...}} 覆盖层（置信度/状态可被分析师修正）。
    """
    classification = classification or {}
    register = []
    for i, raw in enumerate(observations or [], 1):
        aid = raw.get("id") or raw.get("id_hint") or "A-%02d" % i
        over = classification.get(aid, {}) if isinstance(classification, dict) else {}
        conf = over.get("confidence", raw.get("confidence", "MEDIUM"))
        if conf not in CONFIDENCE_LEVELS:
            conf = "MEDIUM"
        status = over.get("status", raw.get("status", "UNVALIDATED"))
        if status not in ASSUMPTION_STATUSES:
            status = "UNVALIDATED"
        source = over.get("source", raw.get("source", ""))
        a = Assumption(
            id=aid,
            observation=raw.get("observation", ""),
            hypothesis=raw.get("hypothesis", ""),
            confidence=conf,
            source=source,
            status=status,
        )
        a.bucket = bucket(conf, source)
        register.append(a)
    return register


def bucket(confidence, source):
    """置信度→用途桶（Ch10 L192-200）：LOW 或缺证 → 验证任务，不驱动攻击规划。"""
    text = (source or "").lower()
    if confidence == "LOW" or any(m.lower() in text for m in ABSENCE_MARKERS):
        return "verification_task"
    return "attack_plan"


def transition(assumption, target):
    """状态机迁移（Ch10 Figure 1）：返回 (变更后假设, 派生新假设列表)。

    VALIDATED → INVALIDATED 产生派生新假设（证明路径关闭是信息，不是损失）。
    非法迁移（如 UNVALIDATED → INVALIDATED 无测试依据）被拒绝（原样返回）。
    """
    if target not in ASSUMPTION_STATUSES:
        return assumption, []
    cur = assumption.status
    if cur == target:
        return assumption, []
    # 合法迁移：UNVALIDATED→VALIDATED / UNVALIDATED→INVALIDATED / VALIDATED→INVALIDATED
    if cur == "INVALIDATED":
        return assumption, []  # 终态，拒绝再迁
    derived = []
    updated = Assumption(
        id=assumption.id,
        observation=assumption.observation,
        hypothesis=assumption.hypothesis,
        confidence=assumption.confidence,
        source=assumption.source,
        status=target,
        bucket=assumption.bucket,
    )
    if target == "INVALIDATED":
        derived.append(Assumption(
            id=assumption.id + "-R",
            observation="证伪 %s 后产生的新情报" % assumption.id,
            hypothesis="基于 %s 被否定的替代路径假设" % assumption.id,
            confidence="MEDIUM",
            source="invalidation-feedback",
            status="UNVALIDATED",
            bucket="verification_task",
        ))
    return updated, derived


def derive_from_detections(rules):
    """从检测规则派生假设（Ch10 Listing 7 / A-12..A-15）。

    规则集不完整风险：固定标注 MEDIUM + "规则集可能不完整"（confirmed 仅 5 条时）。
    """
    derived = []
    for i, rule in enumerate(rules or [], 1):
        name = rule.get("name", "") if isinstance(rule, dict) else str(rule)
        derived.append(Assumption(
            id="A-D%02d" % i,
            observation="检测规则 %s" % name,
            hypothesis="利用 %s 未覆盖的行为可能规避检测" % name,
            confidence="MEDIUM",
            source="detection-rules",
            status="VALIDATED",
            bucket="attack_plan",
        ))
    # Ch10 A-15：缺证派生（规则集不完整）
    derived.append(Assumption(
        id="A-D99",
        observation="仅提取到 %d 条规则，Qdrant 外可能有其他检测" % len(rules or []),
        hypothesis="检测规则集不完整，存在未观测到的检测面",
        confidence="MEDIUM",
        source="absence of evidence（规则集可能不完整）",
        status="UNVALIDATED",
        bucket="verification_task",
    ))
    return derived
