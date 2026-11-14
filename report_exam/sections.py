"""每台计分主机的五段式成文（枚举 / 漏洞利用 / 提权 / flag 取证 / 证据归属）。

核心约束：对 collect_evidence 片段**逐字 include**（命令/输出/截图/flag 的
**值**原样），并标注证据归属（来源路径）。不转写、不润色。
EN 版正文不得含中文（§5），故仅**标签**按 lang 切换，证据值保持逐字。
"""
from ._types import Fragment, ReportModel

NOT_ATTEMPTED = {"en": "NOT ATTEMPTED", "zh": "未达成"}


def _verbatim(frag: Fragment, lang: str = "en") -> str:
    """嵌入片段证据值（逐字），标签按语言切换。"""
    src = frag.source_path or frag.step_id
    if lang == "zh":
        label, alt, ai_h, flag_h = "证据归属", "截图", "#### AI 交互日志", "#### flag 取证（双通道一致）"
    else:
        label, alt, ai_h, flag_h = ("Evidence attribution", "screenshot",
                                   "#### AI Interaction Log",
                                   "#### Flag Proof (dual-channel)")
    lines = [f"<!-- {label}: {src} -->"]
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


def render_host_section(host: str, frags: list, index: int = 1,
                        lang: str = "en") -> str:
    """产出单主机五段式小节 markdown。空 frags 记 NOT ATTEMPTED / 未达成。"""
    heading = f"### Host {index} - {host} (IP: TBD)"
    na = NOT_ATTEMPTED.get(lang, NOT_ATTEMPTED["en"])

    if not frags:
        if lang == "zh":
            return (
                f"{heading}\n\n"
                "#### Initial Access / Exploitation\n\n"
                f"**{na}（推进中）**：当前无对应证据片段，本小节如实记录，不虚构利用过程。\n\n"
                "#### Privilege Escalation (if applicable)\n\n（不适用）\n\n"
                "#### Proof\n\n（未达成：flag 双通道证据待补录）\n"
            )
        return (
            f"{heading}\n\n"
            "#### Initial Access / Exploitation\n\n"
            f"**{na}**: no evidence fragments are available for this host. "
            "The section is recorded as-is; no exploitation process is fabricated.\n\n"
            "#### Privilege Escalation (if applicable)\n\n(n/a)\n\n"
            "#### Proof\n\n(not captured: flag dual-channel evidence pending)\n"
        )

    enum = "#### Initial Access / Exploitation\n\n"
    priv = "#### Privilege Escalation (if applicable)\n\n"
    proof = "#### Proof\n\n"
    has_priv = False
    has_proof = False

    for f in frags:
        enum += _verbatim(f, lang) + "\n\n"
        if "whoami" in (f.command or "").lower() or "id" in (f.command or "").lower():
            has_priv = True
            priv += _verbatim(f, lang) + "\n\n"
        if f.flag:
            has_proof = True
            proof += _verbatim(f, lang) + "\n\n"

    if not has_priv:
        priv = "#### Privilege Escalation (if applicable)\n\n(n/a)\n\n"
    if not has_proof:
        proof = "#### Proof\n\n(not captured: flag dual-channel evidence pending)\n"

    return f"{heading}\n\n{enum}{priv}{proof}"


def render_all_host_sections(model: ReportModel, lang: str = "en") -> str:
    """按模型主机顺序渲染全部五段式小节。"""
    out = []
    for i, (host, frags) in enumerate(model.hosts.items(), 1):
        out.append(render_host_section(host, frags, index=i, lang=lang))
    return "\n\n".join(out)
