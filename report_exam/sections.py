"""每台计分主机的五段式成文（枚举 / 漏洞利用 / 提权 / flag 取证 / 证据归属）。

核心约束（SKILL §3.2 / S1 §6.1）：以 `Fragment.raw` 为**唯一渲染源逐字 include**，
命令/输出/截图/元数据/证据校验表一字不改；仅在其外追加证据归属标注。
`raw` 为空（合成片段 / 测试夹具）时才回退到字段渲染，并在注释中明示。

EN 版叙述正文不得含中文（§5）；证据原文中的中文标签属 S1 逐字要求，
优先级高于本仓库 §5 局部约定，故置于 EVIDENCE-FRAGMENT 边界内，
由 verify-evidence 的 vrf-08 排除该区间。
"""
import re

from ._types import Fragment, ReportModel

EVIDENCE_START = "<!-- EVIDENCE-FRAGMENT-START -->"
EVIDENCE_END = "<!-- EVIDENCE-FRAGMENT-END -->"
_PRIVILEGE_RE = re.compile(r"\b(whoami|id|sudo\s+-l)\b", re.I)

NOT_ATTEMPTED = {"en": "NOT ATTEMPTED", "zh": "未达成"}


def _render_fields(frag: Fragment) -> str:
    """raw 缺失时的回退：按结构化字段渲染（仅用于合成片段，非真实证据）。

    标签固定为语言无关：证据区间须在 EN/ZH 两版逐字一致（AC-10 / SKILL §3.2），
    不得因 lang 而改写。
    """
    alt, ai_h, flag_h = ("screenshot", "#### AI Interaction Log",
                         "#### Flag Proof (dual-channel)")
    lines = ["<!-- Synthetic fragment: raw unavailable; rendered from parsed fields -->"]
    if frag.command:
        lines.append("```bash\n" + frag.command + "\n```")
    if frag.output:
        lines.append("```text\n" + frag.output + "\n```")
    if frag.screenshot:
        lines.append(f"![{frag.step_id} {alt}]({frag.screenshot})")
    if frag.ai_log:
        lines.append(ai_h + "\n```text\n" + frag.ai_log + "\n```")
    if frag.flag:
        lines.append(flag_h + "\n```text\n" + frag.flag + "\n```")
    return "\n".join(lines)


def _verbatim(frag: Fragment, lang: str = "en") -> str:
    """逐字 include 证据片段原文，外加可见的证据归属标注。"""
    src = frag.source_path or frag.step_id
    label = "证据归属" if lang == "zh" else "Evidence attribution"
    body = frag.raw.rstrip("\n") if frag.raw.strip() else _render_fields(frag)
    return "\n".join([
        f"<!-- {label}: {src} -->",
        EVIDENCE_START,
        body,
        EVIDENCE_END,
        f"> {label}: `{src}`",
    ])


def is_privilege_step(frag: Fragment) -> bool:
    """仅整词匹配权限查询命令，避免 `?id=1` / `valid` 等误判（§6.1 不虚构）。"""
    return bool(_PRIVILEGE_RE.search(frag.command or ""))


def render_host_body(host: str, frags: list, lang: str = "en") -> str:
    """五段式正文（不含 H3 主机标题），供骨架注入 official 主机小节。"""
    na = NOT_ATTEMPTED.get(lang, NOT_ATTEMPTED["en"])
    if not frags:
        if lang == "zh":
            return (
                "#### Initial Access / Exploitation\n\n"
                f"**{na}（推进中）**：当前无对应证据片段，本小节如实记录，不虚构利用过程。\n\n"
                "#### Privilege Escalation (if applicable)\n\n（不适用）\n\n"
                "#### Proof\n\n（未达成：flag 双通道证据待补录）\n"
            )
        return (
            "#### Initial Access / Exploitation\n\n"
            f"**{na}**: no evidence fragments are available for this host. "
            "The section is recorded as-is; no exploitation process is fabricated.\n\n"
            "#### Privilege Escalation (if applicable)\n\n(n/a)\n\n"
            "#### Proof\n\n(not captured: flag dual-channel evidence pending)\n"
        )

    enum, priv, proof, attribution = [], [], [], []
    for f in frags:
        enum.append(_verbatim(f, lang))
        if is_privilege_step(f):
            priv.append(_verbatim(f, lang))
        if f.flag:
            proof.append(_verbatim(f, lang))
        attribution.append("- `%s`" % (f.source_path or f.step_id))

    parts = [
        "#### Initial Access / Exploitation\n\n"
        "**Enumeration** — exposed attack surface (ports, services, AI components).\n\n"
        + "\n\n".join(enum) + "\n\n"
        "**Vulnerability & Full Exploitation** — verbatim evidence above; "
        "prompts, payloads and model interactions stay in the included fragments.\n",
        "#### Privilege Escalation (if applicable)\n\n"
        + ("\n\n".join(priv) if priv else "(n/a)") + "\n",
        "#### Proof\n\n"
        + ("\n\n".join(proof) if proof
           else "(not captured: flag dual-channel evidence pending)") + "\n",
        "#### Evidence Attribution\n\n" + "\n".join(attribution) + "\n",
    ]
    return "\n".join(parts)


def render_host_section(host: str, frags: list, index: int = 1,
                        lang: str = "en") -> str:
    """产出单主机五段式小节（含 H3 标题）；保持既有公开接口。"""
    return (f"### Host {index} - {host} (IP: TBD)\n\n"
            + render_host_body(host, frags, lang))


def render_all_host_sections(model: ReportModel, lang: str = "en") -> str:
    """按模型主机顺序渲染全部五段式小节。"""
    return "\n\n".join(
        render_host_section(host, frags, index=i, lang=lang)
        for i, (host, frags) in enumerate(model.hosts.items(), 1)
    )
