#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""RoE 硬过滤器（Ch10 §10.1 L286-305 / A3）。

RoE 是硬约束：被禁止路径从执行计划移除（BLOCKED），但作为风险发现保留在报告侧。
禁止"if client approves"式条件保留——本模块不含任何条件放行逻辑。
纯函数；规则经参数注入（设计 §4 S-4）。
"""
from .model import AttackPath


def is_prohibited(path, roe):
    """判定单条路径是否被 RoE 禁止。

    roe 契约（dict）：
      prohibited_tags: [str]       路径 status/detection_risk/标签命中即禁
      prohibited_targets: [str]    目标资产 ID 命中即禁
      allowed_zones: [str]         可选：路径跨越的边界不在允许区集即禁
      required_reports: [dict]     可选：报告要求（不阻断计划，仅记账）
    """
    roe = roe or {}
    tags = [str(x) for x in roe.get("prohibited_tags", [])]
    targets = [str(x) for x in roe.get("prohibited_targets", [])]
    allowed = roe.get("allowed_zones")
    if path.target_asset in targets:
        return True
    haystack = " ".join([path.status, path.detection_risk] + list(path.boundary_crossings)).lower()
    if any(t.lower() in haystack for t in tags):
        return True
    if allowed is not None:
        crossings = set(path.boundary_crossings)
        if crossings and not crossings.issubset(set(allowed)):
            return True
    return False


def apply_roe(model, roe):
    """双轨输出：(执行用 model, 报告风险发现 findings)。

    - 被禁路径：从 model.paths 移除、图上对应边移除，写入 findings（带理由）。
    - 合法路径不变（status 保持 GO/HOLD/可达/待补）。
    - 报告要求（required_reports）原样保留到 findings，不阻断执行。
    """
    findings = list(getattr(model, "report_findings", []) or [])
    if not roe:
        return model, findings

    kept, blocked = [], []
    for p in model.paths:
        if is_prohibited(p, roe):
            blocked.append(p)
        else:
            kept.append(p)

    for p in blocked:
        findings.append("RoE 禁止（从执行计划排除，保留为风险发现）：%s → %s" %
                        (p.start_asset, p.target_asset))

    for rep in roe.get("required_reports", []) or []:
        findings.append("RoE 报告要求：%s" % (
            rep if isinstance(rep, str) else rep.get("text", str(rep))))

    model.paths = kept
    blocked_targets = {p.target_asset for p in blocked}
    if isinstance(model.graph, dict) and "edges" in model.graph:
        model.graph["edges"] = [e for e in model.graph["edges"]
                                if e.get("to") not in blocked_targets]
    model.report_findings = findings
    return model, findings
