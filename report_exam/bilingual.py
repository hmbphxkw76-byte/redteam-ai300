"""双版策略（§5）：EN 官方版（强制提交候选）+ ZH 内部镜像。

两版由**同一 ReportModel** 驱动，证据 ID / flag / 命令 / 输出 / IPv4 / 时间戳
逐字一致（由 render_all_host_sections 共享片段原文保证）。ZH 版永不上交。
"""
from ._types import ReportModel
from .skeleton import render_skeleton
from .sections import render_all_host_sections
from .ai_appendix import collect_ai_logs

LONG_POC_THRESHOLD = 60  # 行；超过者分流 Appendix A


def long_poc_fragments(model: ReportModel):
    """返回输出超过阈值的片段（长 PoC / 长控制台输出）。"""
    return [f for fs in model.hosts.values() for f in fs
            if len(f.output.splitlines()) > LONG_POC_THRESHOLD]


def render_appendix_a(model: ReportModel) -> str:
    """Appendix A：长代码块 / 第三方脚本来源与修改说明位（逐字复制，不转写）。

    正文仍保留完整输出以满足 AC-06 逐字 include；本附录为 §9「正文长度失控」
    时的分流副本，正文由 render_all_host_sections 追加指引。
    """
    lines = ["## A. Scripts & PoC", ""]
    longs = long_poc_fragments(model)
    if not longs:
        lines.append("(No PoC longer than %d lines in this assembly; all commands and "
                     "outputs are retained verbatim in the body.)" % LONG_POC_THRESHOLD)
    for f in longs:
        lines.append("### %s — %s" % (f.step_id, f.source_path or f.target))
        lines.append("")
        lines.append("- Source: `%s`" % (f.source_path or "see body evidence attribution"))
        lines.append("- Modifications: {{third-party script/exploit source link and modifications, per S1}}")
        lines.append("")
        lines.append("```text")
        lines.append(f.output.rstrip("\n"))
        lines.append("```")
        lines.append("")
    return "\n".join(lines)

_ZH_INTRO = {
    "Introduction": "本报告涵盖为通过 OSAI 认证所做的全部努力；评分以正确性与完整性为准。",
    "Objective": "对 AI 化企业环境执行实战红队；识别并 exploitation 横跨两条独立攻击链、独立主机、共享域控的 AI 焦点与传统攻击向量；总分 100，≥75 通过。",
    "Requirements": "依 S1：记录每一步、每条命令、任何代码/脚本与相关控制台输出；第三方脚本/exploit 须附来源链接或代码副本及修改说明；每个阶段配截图；含漏洞/攻击/利用过程总结概述；可被技术读者 copy/paste 逐步复现；AI 工具以同等标准记录。",
}


def _facts_block(model: ReportModel) -> str:
    """从同一模型抽取事实文本，供两版逐字一致比对（AC-10）。"""
    frags = [f for fs in model.hosts.values() for f in fs]
    parts = []
    for f in sorted(frags, key=lambda x: x.step_id):
        parts.append("\n".join([
            f"EVID-ID: {f.step_id}",
            f"TARGET: {f.target}",
            f"COMMAND: {f.command}",
            f"OUTPUT: {f.output}",
            f"FLAG: {f.flag}",
            f"SCREENSHOT: {f.screenshot}",
            f"SOURCE: {f.source_path}",
        ]))
    return "\n---\n".join(parts)


def render_bilingual(model: ReportModel):
    """返回 (en_markdown, zh_markdown)。

    EN 为提交候选；ZH 仅更换叙述段落语言，(official) 章节标题与全部证据事实不变。
    """
    en = _render_en(model)
    zh = _render_zh(model)
    return en, zh


def _appendix_tail(model: ReportModel) -> str:
    return ("\n\n# Appendix A (long PoC offload)\n\n"
            + render_appendix_a(model)
            + "\n\n<!-- Long PoC additionally copied to Appendix A; "
              "verbatim text retained in body per AC-06. -->\n")


def _render_en(model: ReportModel) -> str:
    skeleton = render_skeleton(model)
    sections = render_all_host_sections(model, lang="en")
    ai = collect_ai_logs([f for fs in model.hosts.values() for f in fs], lang="en")
    return (
        skeleton
        + "\n\n# Host Sections (Attack Walkthrough detail)\n\n"
        + "> Long PoC / long console output is additionally copied to Appendix A; "
          "verbatim command/output stays in the body for copy/paste reproduction.\n\n"
        + sections
        + "\n\n# Appendix D (full AI session history)\n\n"
        + ai
        + _appendix_tail(model)
        + "\n<!-- FACTS-BLOCK-START\n"
        + _facts_block(model)
        + "\nFACTS-BLOCK-END -->\n"
    )


def _render_zh(model: ReportModel) -> str:
    skeleton = render_skeleton(model)
    # 仅替换三段叙述文字，其余 (official) 标题与结构保持逐字一致
    for sec, text in _ZH_INTRO.items():
        en_default = {
            "Introduction": "This report documents all efforts conducted to pass the OSAI certification; graded on correctness and completeness.",
            "Objective": "Perform a hands-on red team engagement against an AI-enabled enterprise environment; identify and exploit AI-focused and traditional attack vectors across two independent attack chains, a standalone host, and a shared Domain Controller; 100 points available, pass ≥75.",
            "Requirements": "Per S1: document every step, command, code/script, and console output; link or paste any third-party script/exploit with modifications; screenshots per stage; summary/overview of vulnerabilities; copy/paste reproducible; AI tooling documented to same standard.",
        }[sec]
        skeleton = skeleton.replace(en_default, text)
    sections = render_all_host_sections(model, lang="zh")
    ai = collect_ai_logs([f for fs in model.hosts.values() for f in fs], lang="zh")
    return (
        skeleton
        + "\n\n# 主机小节（攻击链详述 · 内部镜像）\n\n"
        + "> 长 PoC / 长控制台输出另见 Appendix A；正文保留逐字命令与输出以便 copy/paste 复现。\n\n"
        + sections
        + "\n\n# 附录 D（AI 会话历史全文 · 内部镜像）\n\n"
        + ai
        + _appendix_tail(model)
        + "\n<!-- FACTS-BLOCK-START\n"
        + _facts_block(model)
        + "\nFACTS-BLOCK-END -->\n"
    )


def extract_facts(markdown: str) -> str:
    """抽取机读 FACTS-BLOCK 供 AC-10 双版一致性比对。

    事实块整体包在 HTML 注释中：pandoc 不渲染，避免证据值里的中文
    输出进入 EN 版可见正文（§5）；同时保留机读可比对性。
    """
    start = "<!-- FACTS-BLOCK-START\n"
    end = "\nFACTS-BLOCK-END -->"
    if start in markdown and end in markdown:
        return markdown.split(start, 1)[1].split(end, 1)[0]
    return ""
