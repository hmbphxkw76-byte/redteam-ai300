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
    rows = []
    for i, a in enumerate(tm.high_value, 1):
        rows.append([i, "`%s`" % a.asset_id, a.score_class, a.score,
                     a.attack_surface or "—", "`%s`" % (a.evidence_step or "—")])
    L += _table(["排名", "资产ID", "计分分类", "分值", "攻击面", "证据 step"], rows)
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
    return "\n".join(L) + "\n"
