"""双版策略（§5）：EN 官方版（强制提交候选）+ ZH 内部镜像。

两版由**同一 ReportModel** 驱动；证据片段原文按 SKILL §3.2 逐字 include，
故两版证据事实天然一致（由 `extract_facts` 从渲染正文抽取比对，非共享隐藏块）。
EN 版叙述正文全英文；ZH 版仅替换三段引言，(official) 标题逐字保留。
ZH 版永不上交。
"""
import re

from ._types import ReportModel
from .skeleton import (INTRO_EN, OBJECTIVE_EN, REQUIREMENTS_EN, SCORED_KEYS,
                       STANDALONE_KEY, render_skeleton)
from .sections import (EVIDENCE_START, EVIDENCE_END, render_host_body)
from .ai_appendix import collect_ai_logs

LONG_POC_THRESHOLD = 60

_ZH_INTRO = {
    "Introduction": "本报告涵盖为通过 OSAI 认证所做的全部努力；评分以正确性与完整性为准。",
    "Objective": "对 AI 化企业环境执行实战红队；识别并利用横跨两条独立攻击链、独立主机、共享域控的 AI 焦点与传统攻击向量；总分 100，≥75 通过。",
    "Requirements": "依 S1：记录每一步、每条命令、任何代码/脚本与相关控制台输出；第三方脚本/exploit 须附来源链接或代码副本及修改说明；每个阶段配截图；含漏洞/攻击/利用过程总结概述；可被技术读者 copy/paste 逐步复现；AI 工具以同等标准记录。",
}
_EN_TO_ZH = (
    (INTRO_EN, _ZH_INTRO["Introduction"]),
    (OBJECTIVE_EN, _ZH_INTRO["Objective"]),
    (REQUIREMENTS_EN, _ZH_INTRO["Requirements"]),
)


def long_poc_fragments(model: ReportModel):
    """返回输出超过阈值的片段（长 PoC / 长控制台输出）。"""
    return [f for fs in model.hosts.values() for f in fs
            if len(f.output.splitlines()) > LONG_POC_THRESHOLD]


def render_appendix_a(model: ReportModel, include_heading: bool = True) -> str:
    """Appendix A：长代码块 / 第三方脚本来源与修改说明位（逐字复制，不转写）。

    正文仍保留完整输出以满足 AC-06 逐字 include；本附录为 §9「正文长度失控」
    时的分流副本，正文由骨架追加「见 Appendix A」指引。
    """
    lines = (["## A. Scripts & PoC", ""] if include_heading else [])
    longs = long_poc_fragments(model)
    if not longs:
        lines.append("(No PoC longer than %d lines in this assembly; all commands and "
                     "outputs are retained verbatim in the body.)" % LONG_POC_THRESHOLD)
    for f in longs:
        lines += ["### %s - %s" % (f.step_id, f.source_path or f.target), "",
                  "- Source: `%s`" % (f.source_path or "see body evidence attribution"),
                  "- Modifications: {{third-party script/exploit source link and "
                  "modifications, per S1 - pending backfill}}", "",
                  "```text", f.output.rstrip("\n"), "```", ""]
    return "\n".join(lines)


def render_appendix_e(frags) -> str:
    """Appendix E：截图索引（如实列出已有截图，缺失标待补录）。"""
    lines = ["| Step | Screenshot |", "|---|---|"]
    for f in frags:
        lines.append("| %s | %s |" % (f.step_id, f.screenshot or "pending backfill"))
    return "\n".join(lines)


def _build(model: ReportModel, lang: str) -> str:
    frags = [f for fs in model.hosts.values() for f in fs]
    known = set(SCORED_KEYS)
    extra = [f for h, fs in model.hosts.items() if h not in known for f in fs]

    body_by_host = {}
    for h in SCORED_KEYS:
        fs = list(model.hosts.get(h, []))
        if h == STANDALONE_KEY:
            fs += extra  # 真实证据按 MAP §C 归入 Standalone / AI-vector 小节
        body_by_host[h] = render_host_body(h, fs, lang)

    appendix = {
        "A": render_appendix_a(model, include_heading=False),
        "D": collect_ai_logs(frags, lang=lang, include_heading=False),
        "E": render_appendix_e(frags),
    }
    skeleton = render_skeleton(model, body_by_host=body_by_host,
                               appendix_sections=appendix)
    if lang == "zh":
        for en_text, zh_text in _EN_TO_ZH:
            if en_text not in skeleton:
                raise RuntimeError("ZH 版叙述替换失败：骨架措辞已漂移（%s…）" % en_text[:24])
            skeleton = skeleton.replace(en_text, zh_text, 1)
    # AC-11 指引：长 PoC 另见 Appendix A（正文保留逐字证据，不删减）
    marker = ("<!-- Long PoC is additionally copied to Appendix A; "
              "the verbatim evidence stays in the body (AC-06 / SKILL §9). -->")
    return skeleton + "\n" + marker + "\n"


def render_bilingual(model: ReportModel):
    """返回 (en_markdown, zh_markdown)。"""
    return _build(model, "en"), _build(model, "zh")


def extract_facts(markdown: str) -> str:
    """从**渲染正文**的逐字证据区间抽取事实，供 AC-10 双版一致性比对。

    不读取生成时的共享模型，故两版若任一发生证据改写即可被检出。
    """
    pattern = re.escape(EVIDENCE_START) + r"\s*\n(.*?)\n" + re.escape(EVIDENCE_END)
    blocks = re.findall(pattern, markdown, flags=re.S)
    return "\n---\n".join(b.strip() for b in blocks)
