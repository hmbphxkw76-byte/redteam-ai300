<!--
OSAI / AI-300 官方英文报告模板（S1 逐字章节）。
用法：复制本文件为 reports/<PROJECT>-Exam-Report-<YYYYMMDD>-EN.md，
按 {{...}} 占位替换为真实值，并按 §3.2 直接 include collect_evidence.py 片段。
所有 (official) 标题须与 S1 逐字一致（含大小写：Offsec AI Red Teamer Report）。
-->

# OffSec AI Red Teamer

# Exam Report

# student@youremailaddress.com

# OSID: {{OSID}}

Copyright © 2026 OffSec Ltd. All rights reserved.

No part of this publication, in whole or in part, may be reproduced, copied, transferred or any other right reserved to its copyright owner, including photocopying and all other copying, any transfer or transmission using any network or other means of communication, any broadcast for distant learning, in any form or by any means such as any information storage, transmission or retrieval system, without prior written permission from OffSec.

---

# Offsec AI Red Teamer Report

## Introduction

{{High-level statement: all efforts conducted to pass the OSAI certification; graded on correctness and completeness.}}

## Objective

{{Perform a hands-on red team engagement against an AI-enabled enterprise environment; identify and exploit AI-focused and traditional attack vectors across two independent attack chains, a standalone host, and a shared Domain Controller; 100 points available, pass ≥75.}}

## Requirements

{{Per S1: document every step, command, code/script, and console output; link or paste any third-party script/exploit with modifications; screenshots per stage; summary/overview of vulnerabilities; copy/paste reproducible; AI tooling documented to same standard.}}

# Executive Summary

## Overview

{{Non-technical, management-audience overview: scope, outcome, most significant vulnerabilities.}}

## High-Level Attack Path

1. Chain 1 — {{externally accessible entry point compromised → pivot → lateral movement → privilege escalation across 2 subsequent hosts}}.
2. Chain 2 — {{second independent external entry point → alternate route → onward hosts}}.
3. Standalone host — {{reached from internal network; compromised via exposed AI vector}}.
4. Domain Controller — {{both chains converge; shared endgame proof retrieved}}.

## Target Inventory & Point Allocation (extension)

| # | Target | Type | Points | Status |
|---|---|---|---|---|
| 1 | {{Host 1 (IP)}} | AI vector | 15 | {{captured / not}} |
| 2 | {{Host 2 (IP)}} | Traditional | 10 | |
| 3 | {{Host 3 (IP)}} | AI vector | 15 | |
| 4 | {{Host 4 (IP)}} | Traditional | 10 | |
| 5 | {{Host 5 (IP)}} | AI vector | 15 | |
| 6 | {{Host 6 (IP)}} | AI vector | 15 | |
| 7 | {{Standalone (IP)}} | Standalone AI | 15 | |
| 8 | {{DC (IP)}} | Domain Controller | 5 | submitted once |

# Attack Walkthrough

## Chain 1

### Host 1 - HOSTNAME (IP: X.X.X.X)

#### Initial Access / Exploitation
<!-- include evidence/.../recon-XX.md then attack step fragments; for AI vectors document prompts/payloads here -->
{{cat evidence/<skill>/<step>.md >> here}}

#### Privilege Escalation (if applicable)
{{before/after whoami}}

#### Proof
```bash
type C:\Users\Administrator\Desktop\ai_vector.txt   # Windows
cat /root/ai_vector.txt                             # Linux
```
{{paste flag value + screenshot}}

### Host 2 - HOSTNAME (IP: X.X.X.X)
### Host 3 - HOSTNAME (IP: X.X.X.X)

### Domain Controller - HOSTNAME (IP: X.X.X.X)
#### Compromise
#### Proof
```bash
type C:\Users\Public\proof.txt
```
{{paste flag value + screenshot — submit only once}}

## Chain 2

### Host 1 - HOSTNAME (IP: X.X.X.X)
### Host 2 - HOSTNAME (IP: X.X.X.X)
### Host 3 - HOSTNAME (IP: X.X.X.X)

### Domain Controller - HOSTNAME (IP: X.X.X.X)
#### Compromise
#### Proof
{{reference Chain 1 submission; do not re-submit proof.txt}}

## Standalone Host - HOSTNAME (IP: X.X.X.X)

#### Initial Access / Exploitation
<!-- AI Vector Evidence nested here: prompts, payloads, model interactions -->
#### Proof

## Intentionally Not Vulnerable Hosts (extension)
{{document enumeration; mark "confirmed not exploitable"}}

## Attack Timeline (extension)
{{timestamped sequence from evidence fragments}}

# Findings & Risk (extension)
<!-- per-finding block: Attribute table (ID/Target/Severity/CVSS/Type/CVE/Detection/Agent) + Description + PoC + Evidence + Remediation -->

# Recommendations (extension)
# Reproducibility (extension)
# Appendix

## A. Scripts & PoC
{{long PoC code, source links, modification notes}}

## D. AI Session / Prompt History
{{full prompts and responses as text — copy from evidence/*/aia-*.md AI 交互日志}}

## E. Screenshot Index
{{additional screenshots}}

## B / C / F / G / H (extension)
