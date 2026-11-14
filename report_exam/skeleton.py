"""四章骨架渲染（对齐 S1 官方模板，逐字标题）。"""
from ._types import ReportModel

COPYRIGHT = (
    "Copyright © 2026 OffSec Ltd. All rights reserved.\n\n"
    "No part of this publication, in whole or in part, may be reproduced, copied, "
    "transferred or any other right reserved to its copyright owner, including "
    "photocopying and all other copying, any transfer or transmission using any "
    "network or other means of communication, any broadcast for distant learning, "
    "in any form or by any means such as any information storage, transmission or "
    "retrieval system, without prior written permission from OffSec."
)


def _host_inventory(model: ReportModel) -> str:
    rows = ["| # | Target | Type | Points | Status |", "|---|---|---|---|---|"]
    labels = list(model.hosts.keys())
    for i, h in enumerate(labels, 1):
        frags = model.hosts[h]
        status = "captured" if frags else "not attempted"
        rows.append(f"| {i} | {h} | (see evidence) | - | {status} |")
    return "\n".join(rows)


def render_skeleton(model: ReportModel) -> str:
    """产出四章齐全的骨架 markdown（Cover/TOC/Intro/Obj/Req/Exec/Attack/Appendix）。"""
    inv = _host_inventory(model)
    n_hosts = len(model.hosts)
    chain1 = "\n".join(
        f"### Host {i} - {h} (IP: TBD)" for i, h in enumerate(list(model.hosts.keys())[:3], 1)
    )
    return f"""# OffSec AI Red Teamer

# Exam Report

# {model.email}

# OSID: {model.osid}

{COPYRIGHT}

---

# Offsec AI Red Teamer Report

## Introduction

This report documents all efforts conducted to pass the OSAI certification; graded on correctness and completeness.

## Objective

Perform a hands-on red team engagement against an AI-enabled enterprise environment; identify and exploit AI-focused and traditional attack vectors across two independent attack chains, a standalone host, and a shared Domain Controller; 100 points available, pass ≥75.

## Requirements

Per S1: document every step, command, code/script, and console output; link or paste any third-party script/exploit with modifications; screenshots per stage; summary/overview of vulnerabilities; copy/paste reproducible; AI tooling documented to same standard.

# Executive Summary

## Overview

{{Non-technical management overview: scope, outcome, most significant vulnerabilities.}}

## High-Level Attack Path

1. Chain 1 — {{external entry → pivot → lateral movement across 2 hosts}}
2. Chain 2 — {{second independent entry → alternate route}}
3. Standalone host — {{reached from internal; compromised via AI vector}}
4. Domain Controller — {{both chains converge; shared endgame proof}}

## Target Inventory & Point Allocation (extension)

{inv}

# Attack Walkthrough

## Chain 1

{chain1}

### Domain Controller - HOSTNAME (IP: TBD)
#### Compromise
#### Proof
```bash
type C:\\Users\\Public\\proof.txt
```
{{submit only once}}

## Chain 2

{chain1}

### Domain Controller - HOSTNAME (IP: TBD)
#### Compromise
#### Proof
{{reference Chain 1 submission; do not re-submit proof.txt}}

## Standalone Host - HOSTNAME (IP: TBD)

#### Initial Access / Exploitation
#### Proof

## Intentionally Not Vulnerable Hosts (extension)

The environment contains 2 decoy hosts (0 points, intentionally not vulnerable).
Both were enumerated and are recorded as **confirmed not exploitable**;
no exploitation process is fabricated for them.

| # | Decoy | Status | Note |
|---|---|---|---|
| 1 | {{DECOY-1}} | confirmed not exploitable | enumeration evidence retained |
| 2 | {{DECOY-2}} | confirmed not exploitable | enumeration evidence retained |

## Attack Timeline (extension)
{{timestamped sequence from evidence fragments}}

# Findings & Risk (extension)

# Recommendations (extension)

# Reproducibility (extension)

# Appendix

## A. Scripts & PoC
{{long PoC code, source links, modification notes}}

## D. AI Session / Prompt History
{{full prompts and responses — filled by ai_appendix.collect_ai_logs}}

## E. Screenshot Index
{{additional screenshots}}

## B / C / F / G / H (extension)
"""
