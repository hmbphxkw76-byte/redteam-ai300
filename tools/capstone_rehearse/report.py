#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""演练报告渲染：四件产出 + 明确判定（v2 AC-11）。

按路径引用证据片段，不重复存储证据本体（AC-12）；显式标注演练/仿真，
引用路径不含 `-real` 段（AC-13，对齐 report_exam/index.py#L13）。
"""
from __future__ import annotations

from typing import Iterable

from .model import BLOCKING, GATE_DETAILS, RehearsalResult

DISCLAIMER = "> **演练/仿真，非 OSAI 正式考试**；结论须结合实战环境验证（SKILL「失败与豁免」）。"
SOURCES = (
    "`GOVERNANCE.md#L141-L151`（§4.5 九阶段 / 考前硬门禁）",
    "`GOVERNANCE.md#L165-L171`（§5.3 时间盒 / §5.4 24h「宜」）",
    "`docs/governance/references/OSAI-Exam-Guide-snapshot.md#L68`（官方 24h 原文）",
    "`docs/research/capstone-rehearse-canonical.md` §3（九阶段对象映射）",
)


def render_report(result: RehearsalResult,
                  fragment_paths: Iterable[str] = ()) -> str:
    if result.schema_version != "1.0":
        raise ValueError("不支持的 schema_version：%s" % result.schema_version)
    lines = [
        "# capstone-rehearse 演练报告",
        "", DISCLAIMER, "",
        "## 1. 覆盖度矩阵（§4.5 九阶段）", "",
        "| 阶段 | 名称 | 技能 | 就绪 | 证据链贯通 |", "|---|---|---|---|---|",
    ]
    for row in result.matrix:
        lines.append("| %s | %s | `%s` | %s | %s |" % (
            row.stage_id, _stage_name(row.stage_id), row.skill,
            "就绪" if row.ready else "未就绪",
            "贯通" if row.evidence_chain else "断点"))
    lines += [
        "", "## 2. 24h 节奏时间线（§5.4 建议值，非官方强制）", "",
        "| 时间线片段 | 起(h) | 止(h) | 耗时(h) | 关键节点 | 建议值 | 实测值 |",
        "|---|---|---|---|---|---|---|",
    ]
    for slot in result.timeline:
        lines.append("| %s | %.1f | %.1f | %.1f | %s | %.1f | %s |" % (
            slot.segment, slot.start, slot.end, slot.duration, slot.key_node,
            slot.estimate, "未实测" if slot.measured is None else "%.1f" % slot.measured))
    total = sum(s.duration for s in result.timeline[:-1])
    lines += ["", "累计耗时：%.1fh / 24h；超时：%s" % (
        total, "是" if result.overtime else "否")]
    if result.compression:
        lines += ["", "**压缩/取舍建议**："] + ["- %s" % x for x in result.compression]
    lines += [
        "", "## 3. 缺口与补强清单", "",
        "| 阶段 | 分级 | 缺口 | 补强建议 |", "|---|---|---|---|",
    ]
    if result.gaps:
        for gap in result.gaps:
            lines.append("| %s | %s | %s | %s |" % (
                gap.stage_id,
                "阻断性" if gap.severity == BLOCKING else "非阻断",
                gap.description, gap.suggestion))
    else:
        lines.append("| — | — | 无缺口 | — |")
    lines += [
        "", "## 4. 演练结论", "",
        "**是否具备实战条件：%s**" % ("是" if result.ready_for_exam else "否"),
        "", "- 阻断性缺口：%d 项；非阻断缺口：%d 项" % (
            len(result.blocking), len(result.non_blocking)),
        "- 待取证核实闸：%s" % ("、".join(result.pending) or "无（VG-1 已关闭）"),
        "- 超时风险：%s" % ("已标注，见 §2 压缩建议" if result.overtime else "无"),
        "", "**核实闸清单（VG-1…VG-6，逐条带取证方式）**：", "",
        "| 编号 | 状态 | 取证方式 |", "|---|---|---|",
    ]
    for gate, method in GATE_DETAILS:
        state = "待取证" if gate in result.pending else "已关闭"
        lines.append("| %s | %s | %s |" % (gate, state, method))
    paths = [p for p in fragment_paths if "-real" not in p.replace("\\", "/")]
    if paths:
        lines += ["", "**证据片段（按路径引用，不重复存储证据本体）**："]
        lines += ["- `%s`" % p for p in paths]
    lines += ["", "**一手来源锚点**："] + ["- %s" % s for s in SOURCES]
    lines.append("")
    return "\n".join(lines)


def render_summary(result: RehearsalResult) -> str:
    return ("capstone-rehearse: ready_for_exam=%s | 阻断缺口=%d | 非阻断缺口=%d "
            "| 核实闸=%d | 超时=%s" % (
                result.ready_for_exam, len(result.blocking),
                len(result.non_blocking), len(result.pending), result.overtime))


def _stage_name(stage_id: str) -> str:
    from .inventory import spec_for
    return spec_for(stage_id)[1]
