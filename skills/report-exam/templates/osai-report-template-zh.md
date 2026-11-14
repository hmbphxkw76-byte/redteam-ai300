<!--
OSAI / AI-300 中文镜像报告模板（S1 逐字章节标题 + 中文正文）。
用法：复制本文件为 reports/<PROJECT>-Exam-Report-<YYYYMMDD>-ZH.md。
约束（见 report-exam §5）：**仅团队内部复核，永不上交**；章节标题须与 S1 逐字一致（含大小写：Offsec AI Red Teamer Report 小写 f），
证据 ID / flag / 命令 / 输出 / IPv4 / 时间戳须与 EN 版逐字一致。按 §3.2 直接 include collect_evidence.py 片段。
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

{{本段陈述：本报告涵盖为通过 OSAI 认证所做的全部努力；评分以正确性与完整性为准。}}

## Objective

{{对 AI 化企业环境执行实战红队；识别并 exploitation 横跨两条独立攻击链、独立主机、共享域控的 AI 焦点与传统攻击向量；总分 100，≥75 通过。}}

## Requirements

{{依 S1：记录每一步、每条命令、任何代码/脚本与相关控制台输出；第三方脚本/exploit 须附来源链接或代码副本及修改说明；每个阶段配截图；含漏洞/攻击/利用过程的总结概述；可被技术读者 copy/paste 逐步复现；AI 工具以同等标准记录。}}

# Executive Summary

## Overview

{{面向管理层的非技术高层概述：范围、结果、最关键漏洞。}}

## High-Level Attack Path

1. Chain 1 — {{公网入口被攻陷 → 横向移动 → 两台后续主机提权}}。
2. Chain 2 — {{第二独立入口 → 替代内网路径 → 后续主机}}。
3. Standalone host — {{自内网抵达；经暴露 AI 向量攻陷}}。
4. Domain Controller — {{两链汇聚；取得共享终局证明}}。

## Target Inventory & Point Allocation (extension)

| # | 目标 | 类型 | 分值 | 状态 |
|---|---|---|---|---|
| 1 | {{Host 1 (IP)}} | AI 向量 | 15 | {{captured / not}} |
| 2 | {{Host 2 (IP)}} | 传统 | 10 | |
| 3 | {{Host 3 (IP)}} | AI 向量 | 15 | |
| 4 | {{Host 4 (IP)}} | 传统 | 10 | |
| 5 | {{Host 5 (IP)}} | AI 向量 | 15 | |
| 6 | {{Host 6 (IP)}} | AI 向量 | 15 | |
| 7 | {{Standalone (IP)}} | 独立 AI | 15 | |
| 8 | {{DC (IP)}} | 域控 | 5 | submitted once |

# Attack Walkthrough

## Chain 1

### Host 1 - HOSTNAME (IP: X.X.X.X)

#### Initial Access / Exploitation
<!-- include evidence/.../recon-XX.md 再接攻击步骤片段；AI 向量在此记录 prompt/payload -->
{{cat evidence/<skill>/<step>.md >> here}}

#### Privilege Escalation (if applicable)
{{before/after whoami}}

#### Proof
```bash
type C:\Users\Administrator\Desktop\ai_vector.txt   # Windows
cat /root/ai_vector.txt                             # Linux
```
{{粘贴 flag 值 + 截图}}

### Host 2 - HOSTNAME (IP: X.X.X.X)
### Host 3 - HOSTNAME (IP: X.X.X.X)

### Domain Controller - HOSTNAME (IP: X.X.X.X)
#### Compromise
#### Proof
```bash
type C:\Users\Public\proof.txt
```
{{粘贴 flag 值 + 截图 — 仅提交一次}}

## Chain 2

### Host 1 - HOSTNAME (IP: X.X.X.X)
### Host 2 - HOSTNAME (IP: X.X.X.X)
### Host 3 - HOSTNAME (IP: X.X.X.X)

### Domain Controller - HOSTNAME (IP: X.X.X.X)
#### Compromise
#### Proof
{{引用 Chain 1 提交；不再重复提交 proof.txt}}

## Standalone Host - HOSTNAME (IP: X.X.X.X)

#### Initial Access / Exploitation
<!-- AI 向量证据嵌套于此：prompts、payloads、模型交互 -->
#### Proof

## Intentionally Not Vulnerable Hosts (extension)
{{记录枚举；标注「确认不可利用」}}

## Attack Timeline (extension)
{{来自证据片段的时间戳序列}}

# Findings & Risk (extension)
<!-- 每个发现块：属性表(ID/目标/严重度/CVSS/类型/CVE/检测/Agent) + 描述 + PoC + 证据 + 修复建议 -->

# Recommendations (extension)
# Reproducibility (extension)
# Appendix

## A. Scripts & PoC
{{长 PoC 代码、来源链接、修改说明}}

## D. AI Session / Prompt History
{{完整 prompt 与响应文本 — 复制自 evidence/*/aia-*.md 的 AI 交互日志}}

## E. Screenshot Index
{{补充截图索引}}

## B / C / F / G / H (extension)
