#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""六段版本化攻击情报简报（Ch10 §10.2 Listing 8 / A4）。

字段：Classification / Engagement Day / Brief Version + 六段（BRIEF_SECTIONS）。
版本历史=决策日志（决策日志来自 ThreatModel.decision_log）。
纯渲染，无 I/O。
"""
from .model import BRIEF_SECTIONS


def _bullets(items):
    return "\n".join("- %s" % x for x in (items or [])) or "- （无）"


def render_brief(tm):
    """渲染 Listing 8 形态的六段简报。"""
    L = []
    L.append("ATTACK INTELLIGENCE BRIEF — %s" % (tm.target or "（未指定目标）"))
    L.append("Classification: Client Confidential")
    L.append("Engagement Day: %d of 10" % getattr(tm, "engagement_day", 1))
    L.append("Brief Version: %s" % getattr(tm, "brief_version", "1.0"))
    L.append("")

    # 1 TARGET SUMMARY
    L.append("=== %s ===" % BRIEF_SECTIONS[0])
    L.append("Components: %d confirmed services" % len(tm.high_value))
    L.append("Architecture confidence: %s" % (
        "HIGH (all major components VALIDATED)" if tm.high_value else "UNKNOWN"))
    L.append("")

    # 2 CROWN JEWELS
    L.append("=== %s (ranked by offensive value) ===" % BRIEF_SECTIONS[1])
    jewels = [a for a in tm.high_value if getattr(a, "offensive_value", "")]
    if jewels:
        for i, a in enumerate(jewels, 1):
            L.append("#%d %s [%s] [%s]" % (i, a.asset_id,
                     a.offensive_value, a.access_status or "UNVALIDATED"))
    else:
        L.append("- （未提供进攻价值标注）")
    L.append("")

    # 3 ASSUMPTION REGISTER STATUS
    L.append("=== %s ===" % BRIEF_SECTIONS[2])
    regs = getattr(tm, "assumptions", []) or []
    counts = {k: sum(1 for a in regs if a.status == k)
              for k in ("VALIDATED", "UNVALIDATED", "INVALIDATED")}
    L.append("Total: %d | VALIDATED: %d | UNVALIDATED: %d | INVALIDATED: %d" % (
        len(regs), counts["VALIDATED"], counts["UNVALIDATED"], counts["INVALIDATED"]))
    critical = [a for a in regs if a.status == "UNVALIDATED" and a.bucket == "attack_plan"]
    for a in critical:
        L.append("  %s: %s [BLOCKS — untested]" % (a.id, a.hypothesis))
    L.append("")

    # 4 SCOPE CONSTRAINTS
    L.append("=== %s ===" % BRIEF_SECTIONS[3])
    if getattr(tm, "report_findings", None):
        L.append(_bullets(tm.report_findings))
    else:
        L.append("- （未提供 RoE 约束）")
    L.append("")

    # 5 ESCALATION PATHS
    L.append("=== %s ===" % BRIEF_SECTIONS[4])
    for p in tm.paths:
        L.append("PATH %s → %s [%s]" % (p.start_asset, p.target_asset,
                                        p.gate_decision or p.status))
        L.append(" Gates: %s" % (
            "、".join("%s=%s" % (g.assumption_id, g.decision) for g in p.gates) or "—"))
        L.append(" Detection Risk: %s" % (p.detection_risk or "—"))
        L.append(" Boundaries: %s" % (" → ".join(p.boundary_crossings) or "—"))
    if not tm.paths:
        L.append("- （无路径）")
    L.append("")

    # 6 NEXT ACTIONS + 决策日志（版本史）
    L.append("=== %s ===" % BRIEF_SECTIONS[5])
    if getattr(tm, "decision_log", None):
        L.append(_bullets(tm.decision_log))
    else:
        L.append("- （无待决事项）")
    L.append("")
    if getattr(tm, "decision_log", None):
        L.append("=== DECISION LOG (version history) ===")
        for i, entry in enumerate(tm.decision_log, 1):
            L.append("v1.%d: %s" % (i - 1, entry))
    return "\n".join(L) + "\n"
