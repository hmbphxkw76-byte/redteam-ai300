"""AI 会话历史 → Appendix D（§6.3）。

标准不低于其它工具：所有含 AI 交互日志的片段全量复制入 Appendix D，
正文对应段仍由 sections.render_host_section 保留。
"""
from typing import Iterable

from ._types import Fragment


def collect_ai_logs(fragments: Iterable[Fragment], lang: str = "en") -> str:
    """汇总全部片段的 AI 交互日志为 Appendix D 正文。

    返回 markdown；无 AI 日志时返回明确占位说明（不虚构对话）。
    AI 日志**内容逐字复制**；仅说明性标签按 lang 切换（§5 EN 版无中文正文）。
    """
    lines = ["## D. AI Session / Prompt History", ""]
    found = 0
    for f in fragments:
        if not f.ai_log.strip():
            continue
        found += 1
        lines.append(f"### {f.step_id} — {f.source_path or f.target}")
        lines.append("")
        lines.append("```text")
        lines.append(f.ai_log.rstrip("\n"))
        lines.append("```")
        lines.append("")
        if lang == "zh":
            lines.append("> 人工校验：AI 生成内容入正文前须标注「经人工校验采纳」（§5.5）。")
        else:
            lines.append("> Human validation: AI-generated prose must be marked "
                         "'reviewed and adopted by human' before entering the body (§5.5).")
        lines.append("")
    if found == 0:
        if lang == "zh":
            lines.append("（本组装输入未提供 AI 交互日志；须回溯对应技能按 §6.3 补录。）")
        else:
            lines.append("(No AI interaction logs in this assembly input; backfill "
                         "from the corresponding skill per §6.3.)")
        lines.append("")
    return "\n".join(lines)
