#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诱饵判定清单生成（markdown，纯函数）。

输出 seam：五字段表（主机标识 / 命中维度 / 具体依据 / 放弃理由 / 时间戳）+ 结论列，
「诱饵」与「不确定-已放弃」两种结论不混淆；并给出与「≈2 台」全局预期的对账（v2 AC9）。
"""
from .model import JudgmentConclusion


def _fmt_dimensions(values):
    return "、".join(values) if values else "（无）"


def _fmt_evidence(evidence):
    if not evidence:
        return "（无）"
    return "；".join("%s：%s" % (dim, reason) for dim, reason in evidence.items())


def render_markdown(judgments, expected_decoys=2):
    """渲染诱饵判定清单。judgments 为 DecoyJudgment 列表。"""
    decoys = [j for j in judgments if j.conclusion == JudgmentConclusion.DECOY]
    uncertain = [j for j in judgments
                 if j.conclusion == JudgmentConclusion.UNCERTAIN_ABANDONED]
    lines = [
        "# 诱饵判定清单（decoy-detect）",
        "",
        "- **判定条目**：%d（诱饵 %d / 不确定-已放弃 %d）"
        % (len(judgments), len(decoys), len(uncertain)),
        "- **预期诱饵数**：≈%d 台" % expected_decoys,
        "",
        "| 主机标识 | 命中维度 | 具体依据 | 放弃理由 | 时间戳 | 结论 |",
        "|---|---|---|---|---|---|",
    ]
    for j in judgments:
        lines.append("| `%s` | %s | %s | %s | `%s` | **%s** |" % (
            j.host_id,
            _fmt_dimensions(j.dimension_values()),
            _fmt_evidence(j.evidence),
            j.abandonment_reason or "（无）",
            j.timestamp or "（未记录）",
            j.conclusion.value,
        ))
    if not judgments:
        lines.append("| （无） | — | — | — | — | — |")

    # 全局对账（v2 AC9）：不凑数，仅告警
    lines += ["", "## 全局对账", ""]
    lines.append("- 判定诱饵 %d 台，预期 ≈%d 台。" % (len(decoys), expected_decoys))
    if len(decoys) != expected_decoys:
        lines.append("- **告警**：诱饵数量（%d）与预期（≈%d）不一致，"
                     "请复核枚举完整性与判定逻辑，不强行凑数（SKILL.md 失败与豁免）。"
                     % (len(decoys), expected_decoys))
    else:
        lines.append("- 数量与预期一致。")

    lines += ["", "> 复现：`python tools/decoy_detect/cli.py run --inventory <输入.json>`"]
    return "\n".join(lines) + "\n"
