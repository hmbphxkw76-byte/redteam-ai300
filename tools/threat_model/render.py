#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""渲染 markdown 威胁模型：四节 + 质量门（SKILL 第四节）。"""
from .model import DECOY


def _table(headers, rows):
    out = ["| " + " | ".join(headers) + " |",
           "|" + "|".join(["---"] * len(headers)) + "|"]
    for r in rows:
        out.append("| " + " | ".join(str(x) for x in r) + " |")
    return out


def render(tm):
    """把 ThreatModel 渲染为结构化 markdown（四节 + 质量门）。"""
    L = []
    L.append("# 威胁模型（threat-model）— %s" % (tm.target or "（未指定目标）"))
    L.append("")
    L.append("> 规划产出，不含实际攻击利用；所有结论由对应攻击子技能在实战中验证。")
    L.append("> 资产可被下游按 `asset_id` 直接复用（衔接 report-exam / verify-evidence / decoy-detect）。")
    L.append("")

    # 1. 资产计分排序
    L.append("## 1. 资产计分排序（杠杆优先）")
    L.append("")
    L.append("> **计分来源**：GOVERNANCE §2.2/§2.3（AI向量机/独立机 15、传统向量机 10、"
             "域控 5、诱饵机 0）；排序分类依据来自分析师分类层（`score_class`）。")
    L.append("")
    rows = []
    for i, a in enumerate(tm.high_value, 1):
        rows.append([i, "`%s`" % a.asset_id, a.score_class, a.score,
                     a.attack_surface or "—", a.credential_hint or "无",
                     "`%s`" % (a.evidence_step or "—")])
    L += _table(["排名", "资产ID", "计分分类", "分值", "攻击面", "凭证线索", "证据 step"], rows)
    L.append("")

    # 2. 信任边界与最短攻击路径
    L.append("## 2. 信任边界与最短攻击路径")
    L.append("")
    L.append("**信任边界**（可达性分层）：")
    L.append("")
    brows = [[zone, "、".join("`%s`" % x for x in ids)] for zone, ids in tm.boundaries.items()]
    L += _table(["信任域", "资产"], brows)
    L.append("")
    L.append("**最短攻击路径**（起止 / 阶段 / 耗时 / 依赖子技能 / 可达性）：")
    L.append("")
    prows = []
    for p in tm.paths:
        prows.append(["`%s`" % p.target_asset, "`%s`" % p.start_asset,
                      " → ".join(p.stages), "%dmin" % p.est_minutes,
                      "、".join(p.depends_on) or "—", p.status])
    L += _table(["目标资产", "起点", "必经阶段", "耗时", "依赖子技能", "可达性"], prows)
    L.append("")
    L.append("> **路径依据**：阶段模板与子技能映射见 `STAGE_TEMPLATE`/`SUBSKILL`；"
             "依赖资产缺失或不可达时标「待补」，不虚构可达性（SKILL「失败与豁免」）。")
    L.append("")

    # 3. 诱饵判定清单
    L.append("## 3. 诱饵判定清单（时间盒 ≤30min）")
    L.append("")
    if tm.decoys:
        drows = []
        for d in tm.decoys:
            hit = sum(1 for k in ("behavior", "vuln_absent", "no_value") if d.dims.get(k))
            drows.append(["`%s`" % d.asset_id, d.verdict, "%d/3" % hit,
                          "%.0fmin" % d.elapsed_minutes, "是" if d.abandoned else "否",
                          d.reason, d.timestamp])
        L += _table(["资产ID", "判定", "三维度命中", "耗时", "放弃", "依据", "时间戳"], drows)
    else:
        L.append("本次未提供诱饵嫌疑资产（分类层无 `诱饵机` / `decoy` 标注）；诱饵判定节已生成。")
    L.append("")

    # 4. 优先级攻击图
    L.append("## 4. 优先级攻击图（驱动 §4.5 编排）")
    L.append("")
    L.append("- **根节点（最高杠杆）**：%s" % (
        "、".join("`%s`" % r for r in tm.graph.get("roots", [])) or "（无）"))
    L.append("- **节点**：%s" % ("、".join("`%s`" % n for n in tm.graph.get("nodes", [])) or "（无）"))
    if tm.graph.get("excluded_decoys"):
        L.append("- **排除的诱饵机**：%s" % "、".join(
            "`%s`" % x for x in tm.graph["excluded_decoys"]))
    L.append("- **边（最短路径）**：")
    for e in tm.graph.get("edges", []):
        L.append("  - `%s` → `%s`（%s）" % (e["from"], e["to"], e["status"]))
    L.append("- **编排顺序（§4.5）**：%s" % (
        " → ".join("`%s`" % x for x in tm.order) or "（无）"))
    L.append("")

    # 质量门
    L.append("## 质量门")
    L.append("")
    missing = tm.quality_gate()
    if not missing:
        L.append("**四项齐全**：高价值资产清单 / 信任边界+最短攻击路径 / 诱饵判定清单 / 优先级攻击图。")
    else:
        L.append("**未过门禁**（缺：%s）。" % "、".join(missing))
    L.append("")

    # ---- Ch10 增量节（追加在既有四节 + 质量门之后，既有节 ID/表头不变）----
    _render_ch10_sections(L, tm)
    return "\n".join(L) + "\n"


def _render_ch10_sections(L, tm):
    """Ch10 对齐增量节：假设登记册 / 边界五要素 / 皇冠珠宝 / 路径门与矩阵 / RoE 发现。"""
    # 5 假设登记册（六字段）
    regs = getattr(tm, "assumptions", []) or []
    if regs:
        L.append("## 5. 假设登记册（Ch10 · 六字段）")
        L.append("")
        L += _table(["ID", "观察", "假设", "置信度", "来源", "状态"],
                    [a.as_row() for a in regs])
        L.append("")
        low = [a.id for a in regs if a.bucket == "verification_task"]
        L.append("> 置信度=来源可靠性；待验证任务（LOW/缺证，不驱动攻击规划）：%s" %
                 ("、".join(low) or "无"))
        L.append("")

    # 6 信任边界五要素 + 缺口 + 身份塌缩
    tbs = getattr(tm, "trust_boundaries", []) or []
    if tbs:
        L.append("## 6. 信任边界与信任区（Ch10 · 五要素）")
        L.append("")
        L += _table(["ID", "从→到", "信任类型", "强制机制", "验证状态", "进攻含义"],
                    [b.as_row() for b in tbs])
        L.append("")
        gaps = [b.id for b in tbs if b.is_gap]
        collapses = [b.id for b in tbs if b.identity_collapse]
        L.append("> 信任缺口（TRUST_GAP，无强制机制）：%s" % ("、".join(gaps) or "无"))
        L.append("> 身份塌缩（归属丢失）：%s" % ("、".join(collapses) or "无"))
        L.append("")

    # 7 皇冠珠宝（与既有 §1 考试计分排序并存）
    jewels = [a for a in tm.high_value if getattr(a, "offensive_value", "")]
    if jewels:
        L.append("## 7. 皇冠珠宝（Ch10 · 按进攻价值）")
        L.append("")
        L += _table(["资产ID", "进攻价值", "访问状态", "证据 step"],
                    [[a.asset_id, a.offensive_value, a.access_status or "UNVALIDATED",
                      "`%s`" % (a.evidence_step or "—")] for a in jewels])
        L.append("")

    # 8 升级路径 Go/No-Go + 决策矩阵
    if any(getattr(p, "gates", None) for p in tm.paths) or getattr(tm, "decision_matrix", None):
        L.append("## 8. 升级路径 Go/No-Go 与决策矩阵（Ch10）")
        L.append("")
        grows = []
        for p in tm.paths:
            grows.append([p.target_asset, p.gate_decision or p.status,
                          "、".join("%s=%s" % (g.assumption_id, g.decision) for g in p.gates) or "—",
                          p.detection_risk or "—",
                          " → ".join(p.boundary_crossings) or "—"])
        if grows:
            L += _table(["目标资产", "状态", "Go/No-Go 门", "检测风险", "跨越边界"], grows)
            L.append("")
        matrix = getattr(tm, "decision_matrix", {}) or {}
        if matrix.get("rows"):
            L += _table(["决策点", "信息可用", "信息缺失", "验证成本", "决定"],
                        matrix["rows"])
            L.append("")

    # 9 ATLAS 映射
    amap = getattr(tm, "atlas_map", []) or []
    if amap:
        L.append("## 9. MITRE ATLAS 映射（Ch10 Table 6）")
        L.append("")
        L += _table(["组件", "技术", "ID", "适用性", "应用说明"],
                    [m.as_row() for m in amap])
        L.append("")

    # 10 RoE 报告风险发现（双轨）
    findings = getattr(tm, "report_findings", []) or []
    if findings:
        L.append("## 10. RoE 报告风险发现（执行计划外）")
        L.append("")
        for f in findings:
            L.append("- %s" % f)
        L.append("")
