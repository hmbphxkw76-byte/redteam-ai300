# OSAI / AI-300 官方报告要求 digest（S1 / S3）

> **性质**：本文件为官方考试事实的单一 digest 来源，供 `report-exam` 技能引用。
> **来源标注**：**S1** = `docs/governance/references/OSAI-Exam-Report.pdf`（OffSec 官方报告模板，6 页，本验证的唯一权威来源）；**S3** = OffSec OSAI Exam Guide（help.offsec.com，补充评分/时长/提交，**本 digest 中的 S3 引用尚未实际抓取官方 Exam Guide 核验，仅作占位与推导参考**）。凡未标 S1/S3 的为本仓库推导（标「推导」）。
> **时效**：以官方最新发布为准；如与 S1 原文冲突，以 S1 原文为权威。

---

## 1. 考试环境构成（S1 / 推导）

- **8 个计分目标（S1 明确命名）**：2 条攻击链 × 3 台链式主机（6 台）+ 1 台独立主机 + 1 台域控。
- 每条攻击链自单一公网入口起始，内网横向至 3 台主机，并汇聚于域控。
- 独立主机（AI 向量）在取得任一链内网立足点后方可达。
- （推导/假设：典型 OffSec 环境常另含 2 台诱饵机/「确认不可利用」主机，S1 未明列；本仓库以 extension 小节记录，不计入 8 计分目标。）

## 2. 计分模型（S1 明示 + 推导补全）

- **总分 100、及格 75（S1 明示**，见 Objective："A total of 100 points is available … at least 75 points to pass"）。
- **8 个计分目标（S1 明示命名）** = 6 链式 + 1 独立 + 1 域控。
- 分值（**推导，非 S1 明示**）：AI 向量机 15 分/台、传统向量机 10 分/台、独立机 15 分、域控 5 分。*（此拆分依「总分 100 + 8 目标」倒推，未见于 S1 原文；S3 核验后可能调整，正式提交前须复核。）*
- **推导**：由「6 台链式 + 独立 15 + 域控 5 = 100」且 AI 15/传统 10 推得链式构成 = **4 台 AI向量(60) + 2 台传统向量(20)**。
- **及格线 75/100（S1 明示）**。推导达标最小组合（基于上条推导分值）：4 AI向量(60) + 独立(15) = 75，无需传统/域控即可及格 → AI 向量为最高杠杆能力。
- 域控 `proof.txt` **仅可提交一次**（S1：even if both chains are completed）。

## 3. 报告结构（S1，逐字章节）

封面（Cover）：
- `OffSec AI Red Teamer`
- `Exam Report`
- `student@youremailaddress.com`
- `OSID: XXXXX`
- 逐字版权声明（见第 4 节）。

目录（TOC）：须含条目 `Offsec AI Red Teamer Report`。

正文标题（Body title）：`# Offsec AI Red Teamer Report`（注意 "Offsec" 小写 f）。

章节（S1 原文结构）：
- `## Introduction` — 说明报告涵盖为通过认证所做的全部努力，从正确性与完整性评分。
- `## Objective` — 对 AI 化企业环境执行实战红队；识别并 exploitation 横跨两条独立攻击链、独立主机、共享域控的 AI 焦点与传统攻击向量；总分 100，≥75 通过。
- `## Requirements` — 见第 5 节逐字要求。
- `# Executive Summary`
  - `## Overview` — 面向管理层的非技术高层概述。
  - `## High-Level Attack Path` — 4 项：Chain 1 / Chain 2 / Standalone / Domain Controller。
- `# Attack Walkthrough`
  - `## Chain 1` → `### Host 1/2/3 - HOSTNAME (IP: X.X.X.X)`、`### Domain Controller - HOSTNAME (IP: X.X.X.X)`；每段含 `Initial Access / Exploitation`(+截图)、`Privilege Escalation (if applicable)`(+截图)、`Proof`(+截图)。
  - `## Chain 2`（同结构；域控 Proof 注明引用 Chain 1 提交）。
  - `## Standalone Host - HOSTNAME (IP: X.X.X.X)`（AI Vector Evidence 嵌套于 Initial Access）。
  - `# Appendix` — 长 PoC 代码、补充截图、AI 会话/提示历史、所用 prompt。

## 4. 封面版权声明（S1 逐字，必须原样）

```
Copyright © 2026 OffSec Ltd. All rights reserved.

No part of this publication, in whole or in part, may be reproduced, copied, transferred or any other right reserved to its copyright owner, including photocopying and all other copying, any transfer or transmission using any network or other means of communication, any broadcast for distant learning, in any form or by any means such as any information storage, transmission or retrieval system, without prior written permission from OffSec.
```

## 5. Requirements 逐字要求（S1 正文）

> The candidate is required to write a report describing the exploitation process for each target in the environment. The report must document all attacks, including every step taken, all commands issued, any code or scripts written, and the relevant console output. Where an existing script or exploit is used, the candidate must provide a link to its source or a copy of the code, along with documentation of any modifications made to it. Each stage of the attack should be supported by screenshots showing the various steps and stages of the exploitation process.
>
> In addition, the report must include a summary and overview of the vulnerabilities identified, the attacks performed, and the overall exploitation process. The documentation should be thorough enough that the attacks can be replicated step-by-step, via a copy/paste approach, by a technically competent reader.

> Because effective use of AI is a core component of this assessment, any AI tooling used during the engagement — including prompts, model interactions, and AI-assisted payload generation — should be documented to the same standard as any other tool or technique.

## 6. flag 文件与取证（S1）

- `trad_vector.txt` — 传统向量机；位于被攻陷用户家目录或 `C:\Users\Administrator\Desktop\`(Win) / `/root/`(Lin)。
- `ai_vector.txt` — AI 向量机；同位置。
- `proof.txt` — 域控；位于 `C:\Users\Public\`。
- 每个 flag 须在控制面板提交 **且** 报告中含内容与截图。
- 每个目标（含诱饵机与未达成目标）均须记录。
- 每个阶段须有截图；每条命令、输出、脚本、AI 交互均须记录。

## 7. 提交与格式（S3，与 GOVERNANCE §6.4 一致）

- 报告须为 PDF，命名 `OSAI-OS-XXXXX-Exam-Report.pdf`（`XXXXX` = 真实 OSID）。
- 归档为 `.7z`，**无密码**，命名 `OSAI-OS-XXXXX-Exam-Report.7z`，≤100MB。
- 考试 24h + 提交窗口考试结束后 24h；提交后不可修改；无提交后补加。
- AI 工具允许使用，须以同等标准记录。

## 8. 评分/失分要点（S3）

- 文档不完整 → 对应目标扣分或零分；提交后不可补充。
- 未在控制面板与报告同时提供 flag 内容与截图 → 触发失分条款（§2.4）。
- 域控 proof.txt 重复提交 → 不合规。
