#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""运行报告渲染：摘要、逐步骤表、复现命令、转技能建议。

约束（规格 #213 v2）：AC-16（ABSENT 须给转技能建议）、AC-18（命令可直接
copy/paste 且无占位符）、AC-09（报告不得出现凭据明文——由上游只喂指纹保证）。
"""
import json
from typing import List

from .model import Outcome, RunReport


def summary(report: RunReport) -> str:
    counts = report.outcome_counts()
    parts = ["%s=%d" % (name.lower(), counts[name]) for name in counts]
    return "attack-infra target=%s steps=%d %s" % (
        report.target or "-", len(report.steps), " ".join(parts))


def _table(report: RunReport) -> List[str]:
    rows = ["| 步骤 | 结论 | 原因 | 摘要 |", "|---|---|---|---|"]
    for step in report.steps:
        rows.append("| %s | %s | %s | %s |" % (
            step.step_id, step.outcome.value, step.reason or "-",
            (step.summary or "-").replace("|", "\\|")))
    return rows


def _reproduce(report: RunReport) -> List[str]:
    rows = ["## 复现命令", "", "```bash"]
    for step in report.steps:
        if step.command:
            rows.append("# %s (%s)" % (step.step_id, step.outcome.value))
            rows.append(step.command)
    rows.append("```")
    return rows


def _before_after(report: RunReport) -> List[str]:
    """利用前后对照（SKILL.md 质量门：部署/权限 before/after）。"""
    baseline = next((s for s in report.steps if s.step_id == "infra-01"), None)
    post = [s for s in report.steps if s.outcome is Outcome.EXPLOITED]
    if baseline is None or not baseline.findings:
        return []
    rows = ["## 利用前后对照", "",
            "| 阶段 | 事实 |", "|---|---|"]
    for finding in baseline.findings:
        rows.append("| 利用前（基线） | `%s` %s → %s |" % (
            finding.endpoint.url, finding.endpoint.kind or "-",
            finding.outcome.value))
    if post:
        for step in post:
            rows.append("| 利用后（%s） | %s |" % (step.step_id,
                                                 (step.summary or "-").replace("|", "\\|")))
    else:
        rows.append("| 利用后 | 未取得利用后状态（如实记录，不作推断） |")
    return rows


def render(report: RunReport) -> str:
    lines = ["# attack-infra 运行报告", "",
             "摘要：`%s`" % summary(report), ""]
    lines += _table(report)
    before_after = _before_after(report)
    if before_after:
        lines += [""] + before_after
    if report.notes:
        lines += ["", "## 运行注记", ""] + ["- %s" % n for n in report.notes]
    suggestions = report.next_skills()
    if suggestions:
        lines += ["", "## 转技能建议", "",
                  "存在 %d 步 `ABSENT` 结局，按 SKILL.md「失败与豁免」评估改走：%s"
                  % (len(report.absent()),
                     "、".join("`%s`" % s for s in suggestions))]
    if any(step.command for step in report.steps):
        lines += [""] + _reproduce(report)
    return "\n".join(lines)


def to_dict(report: RunReport) -> dict:
    return {
        "target": report.target,
        "summary": summary(report),
        "notes": list(report.notes),
        "steps": [
            {
                "step_id": s.step_id,
                "outcome": s.outcome.value,
                "reason": s.reason,
                "summary": s.summary,
                "command": s.command,
                "evidence_path": s.evidence_path,
                "evidence_ok": s.evidence_ok,
                "findings": [
                    {"url": f.endpoint.url, "kind": f.endpoint.kind,
                     "status": f.endpoint.status, "outcome": f.outcome.value,
                     "reason": f.reason}
                    for f in s.findings
                ],
            }
            for s in report.steps
        ],
        "next_skills": report.next_skills(),
    }


def to_json(report: RunReport) -> str:
    return json.dumps(to_dict(report), ensure_ascii=False, indent=2)


def exit_code(report: RunReport) -> int:
    """0 全绿；1 存在阻断项（含证据门失败）。"""
    return 1 if report.blocking() else 0


