"""结构化汇总输出（切片 D）。"""
from __future__ import annotations

from pathlib import Path

from .manifest import Manifest
from .runner import PlanResult


def compute_coverage(manifest: Manifest, results) -> float:
    total = len(manifest.scriptable)
    if total == 0:
        return 0.0
    passed = sum(1 for r in results if not r.task.is_manual and r.outcome.returncode == 0)
    return passed / total


def render_markdown(result: PlanResult, out_path: str, manifest: Manifest) -> str:
    lines = ["# tooling-automate 编排汇总", ""]
    lines.append("- 自动化覆盖率：%.2f" % result.coverage)
    lines.append("- 剩余手动任务：%d" % len(result.manual))
    lines.append("")
    lines.append("| step | 类别 | 目标 | 命令 | 退出码 | 复用声明 |")
    lines.append("|---|---|---|---|---|---|")
    for r in result.results:
        t = r.task
        reuse = "复用 collect_evidence/校验脚本（零新增 seam）"
        cmd = " ".join(r.argv)
        lines.append("| %s | %s | %s | %s | %d | %s |" % (
            t.step, t.category, t.target, cmd, r.outcome.returncode, reuse))
    for t in result.manual:
        lines.append("| %s | %s | %s | （手动） | — | 手工判读，未自动判定 |" % (
            t.step, t.category, t.target))
    text = "\n".join(lines) + "\n"
    if out_path and out_path != "-":
        Path(out_path).write_text(text, encoding="utf-8")
    return text
