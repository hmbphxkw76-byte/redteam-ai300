"""四章骨架渲染（对齐 S1 官方模板，逐字标题）。

Chain 1 / Chain 2 各 3 台主机 + 域控、独立主机、2 台诱饵机显式分列；
主机五段式正文由 `body_by_host` 注入对应 official 小节，不另起 H1，
避免「多主机合并为一节」（S1 / SKILL §1）。
"""
from ._types import ReportModel, SCORED_HOSTS, STANDALONE_KEY

COPYRIGHT = (
    "Copyright © 2026 OffSec Ltd. All rights reserved.\n\n"
    "No part of this publication, in whole or in part, may be reproduced, copied, "
    "transferred or any other right reserved to its copyright owner, including "
    "photocopying and all other copying, any transfer or transmission using any "
    "network or other means of communication, any broadcast for distant learning, "
    "in any form or by any means such as any information storage, transmission or "
    "retrieval system, without prior written permission from OffSec."
)

INTRO_EN = ("This report documents all efforts conducted to pass the OSAI "
            "certification; graded on correctness and completeness.")
OBJECTIVE_EN = ("Perform a hands-on red team engagement against an AI-enabled "
                "enterprise environment; identify and exploit AI-focused and "
                "traditional attack vectors across two independent attack chains, "
                "a standalone host, and a shared Domain Controller; 100 points "
                "available, pass ≥75.")
REQUIREMENTS_EN = ("Per S1: document every step, command, code/script, and console "
                   "output; link or paste any third-party script/exploit with "
                   "modifications; screenshots per stage; summary/overview of "
                   "vulnerabilities; copy/paste reproducible; AI tooling documented "
                   "to same standard.")

CHAIN_1 = SCORED_HOSTS[:3]
CHAIN_2 = SCORED_HOSTS[3:6]
DC_KEY = SCORED_HOSTS[7]
SCORED_KEYS = SCORED_HOSTS


def _status(model: ReportModel, host: str) -> str:
    """状态仅由 flag 双通道推导；未取分一律 NOT ATTEMPTED，不写成已攻陷。"""
    fs = model.hosts.get(host, [])
    if fs and model.dual_channel.get(host):
        return "captured"
    if fs:
        return "NOT ATTEMPTED (fragments present, flag dual-channel pending)"
    return "NOT ATTEMPTED"


def _host_inventory(model: ReportModel) -> str:
    rows = ["| # | Target | Type | Points | Status |", "|---|---|---|---|---|"]
    types = ("AI vector", "Traditional", "AI vector",
             "Traditional", "AI vector", "AI vector",
             "Standalone AI", "Domain Controller")
    points = (15, 10, 15, 10, 15, 15, 15, 5)
    for i, (h, typ, pt) in enumerate(zip(SCORED_KEYS, types, points), 1):
        rows.append("| %d | %s | %s | %d | %s |"
                    % (i, h, typ, pt, _status(model, h)))
    return "\n".join(rows)


def _host_heading(host: str, index: int) -> str:
    return "### Host %d - %s (IP: TBD)" % (index, host)


def _chain_block(model: ReportModel, keys, body_by_host, chain_no: int) -> str:
    out = []
    for i, h in enumerate(keys, 1):
        body = body_by_host.get(h) or (
            "#### Initial Access / Exploitation\n\n**NOT ATTEMPTED**: "
            "no evidence fragments available; no exploitation process is fabricated."
        )
        out.append(_host_heading(h, i) + "\n\n" + body)
    dc_body = body_by_host.get(DC_KEY) or (
        "#### Compromise\n\n(NOT ATTEMPTED)\n\n"
        "#### Proof\n\n(not captured: proof.txt dual-channel evidence pending)"
    )
    out.append("### Domain Controller - %s (IP: TBD)\n\n%s" % (DC_KEY, dc_body))
    return "\n\n".join(out)


def render_skeleton(model: ReportModel, body_by_host=None,
                    appendix_sections=None) -> str:
    """产出四章齐全的骨架 markdown。

    - body_by_host: {host_key: 五段式正文}（由 sections.render_host_body 生成）
    - appendix_sections: {"A": str, "D": str, "E": str}，填充 extension 附录（A/D/E，见 SKILL §1 / canonical F-1.7）
    """
    body_by_host = body_by_host or {}
    ap = appendix_sections or {}
    appendix_a = ap.get("A") or "{{Appendix A: long PoC / third-party scripts / modifications - pending backfill}}"
    appendix_d = ap.get("D") or "{{Appendix D: AI session / prompt history - pending backfill}}"
    appendix_e = ap.get("E") or "{{Appendix E: screenshot index - pending backfill}}"

    inv = _host_inventory(model)
    chain1 = _chain_block(model, CHAIN_1, body_by_host, 1)
    chain2 = _chain_block(model, CHAIN_2, body_by_host, 2)
    standalone_body = body_by_host.get(STANDALONE_KEY) or (
        "#### Initial Access / Exploitation\n\n**NOT ATTEMPTED**: no evidence fragments."
    )

    return f"""# OffSec AI Red Teamer

# Exam Report

# {model.email}

# OSID: {model.osid}

{COPYRIGHT}

---

# Offsec AI Red Teamer Report

## Introduction

{INTRO_EN}

## Objective

{OBJECTIVE_EN}

## Requirements

{REQUIREMENTS_EN}

# Executive Summary

## Overview

{{Management-audience overview: scope, outcome, most significant vulnerabilities - pending backfill}}

## High-Level Attack Path

1. Chain 1 — {{planned path: external entry → pivot → lateral movement across 2 hosts; status per Target Inventory}}.
2. Chain 2 — {{planned path: second independent entry → alternate route; status per Target Inventory}}.
3. Standalone host — {{reached from internal network; AI vector surface; status per Target Inventory}}.
4. Domain Controller — {{both chains converge; shared endgame proof; status per Target Inventory}}.

> Path items above are **planned / status-linked**, not claims of completed compromise.
> Actual status is derived from flag dual-channel evidence in the table below.

## Target Inventory & Point Allocation (extension)

{inv}

# Attack Walkthrough

## Chain 1

{chain1}

## Chain 2

{chain2}

## Standalone Host - {STANDALONE_KEY} (IP: TBD)

{standalone_body}

## Intentionally Not Vulnerable Hosts (extension)

Two decoy hosts (0 points, intentionally not vulnerable) are in scope for
enumeration recording. Decoy enumeration evidence is **pending backfill**;
no exploitation process is fabricated for them.

| # | Decoy | Status | Note |
|---|---|---|---|
| 1 | DECOY-1 | confirmed not exploitable | enumeration evidence pending backfill |
| 2 | DECOY-2 | confirmed not exploitable | enumeration evidence pending backfill |

<!-- 确认不可利用 -->
<!-- 确认不可利用 -->

## Attack Timeline (extension)
{{timestamped sequence from evidence fragments - pending backfill}}

# Findings & Risk (extension)
{{per-finding blocks - pending backfill}}

## Key Findings / Results at a Glance (extension)
{{key vulnerabilities at a glance - pending backfill}}

# Recommendations (extension)
{{recommendations - pending backfill}}

# Reproducibility (extension)
All commands and console outputs are included verbatim in the host sections
and in the corresponding evidence fragments; a technically competent reader
can reproduce the documented steps via copy/paste. Long PoC code and
supplementary screenshots are additionally offloaded (see Appendix A and
Appendix E); the verbatim evidence stays in the body (SKILL §9).

# Appendix

## A. Scripts & PoC

{appendix_a}

## D. AI Session / Prompt History

{appendix_d}

## E. Screenshot Index

{appendix_e}

## B / C / F / G / H (extension)
"""
