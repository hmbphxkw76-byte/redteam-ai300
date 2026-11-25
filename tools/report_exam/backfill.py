#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报告骨架回填（只从证据片段派生，不虚构考试事实）。

保留 `parse_fragment` 的节标题契约与 flag fenced 原值块；仅替换骨架/附录中的
`{{...}}` 与「pending backfill」文案。`NOT ATTEMPTED` 是诚实状态，不被改写。
"""
from __future__ import annotations

import re
from typing import Iterable, List, Tuple

from ._types import ReportModel, SCORED_HOSTS, STANDALONE_KEY
from .bilingual import render_bilingual

# skeleton 用 f-string，`{{...}}` 在渲染后变成单花括号；按单括号匹配，
# 并只替换命中已知标记的词条，避免误伤正文中的普通花括号。
PLACEHOLDER = re.compile(r"\{([^{}]*)\}")
KNOWN_TOKENS = (
    "Management-audience", "Chain 1", "Chain 2", "Standalone host",
    "Domain Controller", "timestamped sequence", "per-finding blocks",
    "key vulnerabilities", "recommendations", "Appendix A", "Appendix D",
    "Appendix E", "third-party script",
)
SCRIPT_HEADER = "#### 脚本 / PoC（来源与修改说明）"


def _frags(model: ReportModel) -> List:
    return [f for fs in model.hosts.values() for f in fs]


def _status(model: ReportModel, host: str) -> str:
    fs = model.hosts.get(host, [])
    if fs and model.dual_channel.get(host):
        return "flag dual-channel recorded"
    if fs:
        return "fragments present, flag dual-channel pending"
    return "no evidence fragment"


def _chain_line(model: ReportModel, hosts: Iterable[str]) -> str:
    return "; ".join("%s: %s" % (h, _status(model, h)) for h in hosts)


def _overview(model: ReportModel) -> str:
    frags = _frags(model)
    captured = [h for h, fs in model.hosts.items() if fs and model.dual_channel.get(h)]
    return ("Scope: 8 scored targets (100 points, pass 75). Evidence fragments: %d. "
            "Hosts with flag dual-channel evidence: %d/%d. Findings below are derived "
            "verbatim from fragments; no exploitation outcome is asserted beyond "
            "recorded evidence." % (len(frags), len(captured), len(SCORED_HOSTS)))


def _timeline(frags) -> str:
    if not frags:
        return "No evidence fragments were supplied to this assembly."
    return "\n".join("- `%s` — target `%s` — %s (source: `%s`)"
                     % (f.step_id, f.target or "?", f.title or "step",
                        f.source_path or "fragment") for f in frags)


def _findings(frags) -> str:
    if not frags:
        return "No findings can be stated without evidence fragments."
    blocks = []
    for f in frags:
        blocks.append("### %s — %s\n\nCommand:\n\n```bash\n%s\n```\n\nOutput:\n\n```text\n%s\n```"
                      % (f.step_id, f.title or "step", f.command.rstrip("\n"),
                         f.output.rstrip("\n")))
    return "\n\n".join(blocks)


def _glance(frags) -> str:
    if not frags:
        return "No recorded findings."
    return "\n".join("- %s: %s (step `%s`)" % (f.target or "target",
                                               f.title or "see evidence", f.step_id)
                     for f in frags)


def _appendix_a(frags) -> str:
    rows = []
    for f in frags:
        block = ""
        if f.raw:
            idx = f.raw.find(SCRIPT_HEADER)
            if idx >= 0:
                block = f.raw[idx:].split("\n#### ", 1)[0].strip()
        rows.append("### %s\n\n%s" % (f.step_id, block or
                                      "No script/PoC registered in this fragment."))
    return "\n\n".join(rows) if rows else "No script/PoC registered in this assembly."


def _appendix_d(frags) -> str:
    logs = [f.ai_log.strip() for f in frags if f.ai_log.strip()]
    return "\n\n".join(logs) if logs else "No AI interaction log recorded in fragments."


def _appendix_e(frags) -> str:
    lines = ["| Step | Screenshot |", "|---|---|"]
    for f in frags:
        lines.append("| %s | %s |" % (f.step_id, f.screenshot or "not captured in fragment"))
    return "\n".join(lines)


def _derive(model: ReportModel, token: str) -> str:
    frags = _frags(model)
    if "Management-audience" in token:
        return _overview(model)
    if "Chain 1" in token:
        return _chain_line(model, SCORED_HOSTS[:3])
    if "Chain 2" in token:
        return _chain_line(model, SCORED_HOSTS[3:6])
    if "Standalone host" in token:
        return _status(model, STANDALONE_KEY)
    if "Domain Controller" in token:
        return _status(model, SCORED_HOSTS[-1])
    if "timestamped sequence" in token:
        return _timeline(frags)
    if "per-finding blocks" in token:
        return _findings(frags)
    if "key vulnerabilities" in token:
        return _glance(frags)
    if "recommendations" in token:
        return "Remediation is derived per finding in the Findings section; no generic advice is asserted without evidence."
    if "Appendix A" in token:
        return _appendix_a(frags)
    if "Appendix D" in token:
        return _appendix_d(frags)
    if "Appendix E" in token:
        return _appendix_e(frags)
    if "third-party script" in token:
        return "See the Script/PoC section of the evidence fragment for source and modification notes."
    return "See the corresponding evidence fragment."


def backfill_text(text: str, model: ReportModel) -> str:
    """把所有占位文案替换为片段派生文本；诚实状态 NOT ATTEMPTED 保持不变。"""
    # 两条链的路径哨兵需按出现顺序区分，先做定点替换再走通用派生。
    text = text.replace(
        "{planned path: external entry → pivot → lateral movement across 2 hosts; status per Target Inventory}",
        _chain_line(model, SCORED_HOSTS[:3]))
    text = text.replace(
        "{planned path: second independent entry → alternate route; status per Target Inventory}",
        _chain_line(model, SCORED_HOSTS[3:6]))

    def _replace(m):
        token = m.group(0)
        return _derive(model, token) if any(k in token for k in KNOWN_TOKENS) else token

    out = PLACEHOLDER.sub(_replace, text)
    out = re.sub(r"\|\s*pending backfill\s*\|", "| not captured in fragment |", out)
    out = out.replace("enumeration evidence is **pending backfill**",
                      "enumeration evidence is recorded in recon fragments when available")
    out = out.replace("pending backfill", "see evidence fragments")
    return out


def backfill_bilingual(model: ReportModel) -> Tuple[str, str]:
    """返回 (EN, ZH) 双版；两版使用同一派生事实，事实一致性判据不变。"""
    en, zh = render_bilingual(model)
    return backfill_text(en, model), backfill_text(zh, model)
