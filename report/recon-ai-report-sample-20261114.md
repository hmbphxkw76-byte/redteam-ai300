# 报告试样说明（非提交件）

| 项目 | 内容 |
|---|---|
| 性质 | **报告试样**（结构演示件），非考试提交件；不参与评分，不含任何取分声明 |
| 环境 | 演练目标 `http://192.168.40.189`（OWASP AIVP 部署实例）；**非** OSAI 正式考试环境，结论不外推 |
| 证据源 | `evidence/recon-ai/`：7 份证据片段 + 7 张访问证明截图 + `MANIFEST.jsonl`，由 `tools/recon_ai` 于 2026-11-14 22:41–22:42 生成 |
| 成文依据 | `skills/report-exam/SKILL.md` 的章节契约与证据引用规则（§1 结构、§3.2 引用、§7 质量门） |
| 引用方式 | 每步先按路径引用片段 `（证据：evidence/recon-ai/recon-0N.md）`，再以 `![]()` **内嵌访问证明截图**（图片地址 `../evidence/recon-ai/shots/<file>.png`，相对本报告文件解析）；关键输出**逐字摘录**，不改写、不润色 |
| 计分状态 | 未取分（0/100）；无 flag；`proof.txt` 未涉及 |
| 校验状态 | 结构四章齐全；证据三件套 7/7（含正文内嵌截图 7/7，图片语法与文件存在性均已核）；实跑 `tools/verify_evidence.py --payload <本报告+7 片段> --no-artifacts`：vrf-01/02/03/04/05/06/08 与 `proof-single` 均为真，**blocking 0**；vrf-07 因 dry-run 未判定（pending VG-3）；`missing` 2 项（无 flag 双通道、域控 proof 未取分）为预期项。结论：结构可提交、内容不可提交（未取分） |

---

# OffSec AI Red Teamer

## Exam Report

student@youremailaddress.com

# OSID: XXXXX

Copyright © 2026 OffSec Ltd. All rights reserved.

## Table of Contents

- Offsec AI Red Teamer Report
  - Introduction
  - Objective
  - Requirements
- Executive Summary
  - Overview
  - High-Level Attack Path
  - Target Inventory & Point Allocation
  - Key Findings / Results at a Glance
- Attack Walkthrough
  - Standalone Host — AIVP-DRILL (IP: 192.168.40.189)
  - Chain 1 / Chain 2 / Domain Controller（Not attempted）
  - Intentionally Not Vulnerable Hosts
- Findings & Risk
- Recommendations
- Reproducibility
- Conclusion
- Appendix
  - A. Scripts & PoC
  - D. AI Session / Prompt History
  - E. Screenshot Index
  - F. Evidence Manifest

---

# Offsec AI Red Teamer Report

## Introduction

本次侦察针对单一演练目标 `http://192.168.40.189` 展开。该目标经响应特征确认为 **OWASP AIVP（AI Vulnerabilities Playground）** 的部署实例：前端为 React 单页应用，经 `nginx/1.27.5` 反向代理至 FastAPI 后端，模型服务以 Server-Sent Events 流式返回，默认模型为 `LongCat-2.5`（证据：`evidence/recon-ai/recon-01.md`）。

在 OSAI 环境中，侦察属最高杠杆前置能力：AI 向量机每台 15 分、独立机 15 分，而及格线为 75/100，因此「是否能在有限窗口内准确定位 AI 资产」直接决定后续攻击技能的命中率。本试样把侦察阶段的执行与取证结果，按 S1 官方报告结构成文，用以检验三件事：

1. 侦察产出能否**直接进入**官方报告结构，而不需要二次加工；
2. 每一步结论能否被技术读者 **copy/paste 复现**（S1 强制要求）；
3. 证据能否支撑「未取分」这一如实结论，而不是用文字描述替代证据。

边界声明：本次仅执行**被动侦察**（无状态变更的读取 + 一次无害回显），未执行任何攻击、利用、提权或横向动作；所有资产结论限于可观测面，取不到的证据一律记为「不可判定」，不以推断替代。

## Objective

- 识别目标环境中的 AI 组件类别、产品/引擎与暴露端点，形成可被下游技能按资产ID直接复用的结构化清单。
- 逐步骤留存「确切命令 + 关键输出 + 访问证明截图」，并记录脚本来源、模型交互与 flag 双通道状态，满足 S1/S3 的文档要求。
- 若目标为无 AI 组件的诱饵主机，给出可判定的降级依据，避免在 0 分主机空耗。

## Requirements

S1 对报告的要求与本试样的落实情况：

| S1 要求（要点） | 本试样落实 |
|---|---|
| 记录每一步、每条命令、任何脚本、相关控制台输出 | 7 个步骤逐条给出命令与原始输出；本阶段未使用脚本，已显式声明（Appendix A） |
| 使用已有脚本/exploit 须附来源或代码副本 + 修改说明 | 无第三方脚本；证据片段内「脚本 / PoC」小节对每一步均显式记录该状态 |
| 每个攻击阶段须有截图支撑 | 7 张访问证明截图，GET 面直截、POST/SSE 面以请求/响应转录页渲染并标注类型（Appendix E） |
| 含漏洞/攻击/利用过程的 summary 与 overview，且可 copy/paste 复现 | Executive Summary + Findings & Risk + Reproducibility 三处给出汇总与复现命令 |
| AI 工具与模型交互同等标准记录 | 对目标模型的两次交互留痕（`recon-02` 发送、`recon-07` 复用）全文入 Appendix D |
| flag 须在报告与面板双通道一致 | 本试样未取分，无 flag 可记；不虚构，见 Attack Walkthrough「Proof」段 |

---

# Executive Summary

## Overview

演练目标对外暴露的是一个 AI 安全实训平台，而非生产业务系统。它的价值不在于自身数据，而在于**它把 55 个 AI 攻击面集中在一个可访问的 HTTP 入口之下**：4 个阶段分别对应提示注入、数据提取与隐私、模型操纵、MCP 安全，共 55 个实验。

对红队而言，这意味着一次侦察即可获得完整的攻击面地图：确认了 LLM 引擎（`LongCat-2.5`）、流式聊天服务、检索链路痕迹、agent 编排面与 MCP 工具面五类实证资产；唯一未能定级的是向量库（被动面无端口证据，需主动探测）。护栏侧的证据同样明确：一次无害回显被原样返回，且 6 项安全响应头全部缺失。

需要强调的限制：以上均为**侦察结论**，不含任何利用结果，也不含 flag。该目标不计分。

## High-Level Attack Path

| 路径 | 状态 | 说明 |
|---|---|---|
| Chain 1（公网入口 → 3 台链式主机 → 域控） | Not attempted | 本次仅侦察单一演练目标 |
| Chain 2（公网入口 → 3 台链式主机 → 域控） | Not attempted | 同上 |
| Standalone Host（AI 向量，取得立足点后可达） | 部分：仅侦察 | 演练目标已完成 AI 资产枚举，未取分 |
| Domain Controller（`proof.txt`） | Not attempted | 未涉及；提交约束（仅一次）不适用 |

演练目标内部的路径（侦察视角）：

```text
http://192.168.40.189
  ├─ /api/config          → 部署配置（默认模型、实验面白名单）        [recon-01]
  ├─ /api/labs/{id}/chat  → SSE 流式聊天（4 phase × 55 lab）          [recon-02]
  ├─ /explore + /assets/* → 前端产物（检索链路痕迹）                  [recon-03]
  ├─ /api/labs/*/summary  → 实验面元数据（422 暴露参数契约）          [recon-04/05]
  ├─ /api/secrets/validate→ 凭据校验预言机（200 + success:false）     [recon-06]
  └─ /api/me/runs         → 运行遥测（匿名可读）                      [recon-05]
```

## Target Inventory & Point Allocation

| # | 计分目标类型 | 分值 | 本次状态 |
|---|---|---|---|
| 1–4 | AI 向量机 × 4 | 15 × 4 = 60 | Not attempted |
| 5–6 | 传统向量机 × 2 | 10 × 2 = 20 | Not attempted |
| 7 | 独立主机（AI 向量） | 15 | Not attempted（演练目标仅侦察） |
| 8 | 域控（`proof.txt`） | 5 | Not attempted（flag 仅可提交一次） |
| — | 合计 | 100 | **本次得分 0** |

## Key Findings / Results at a Glance

| 编号 | 发现 | 严重度 | 证据 |
|---|---|---|---|
| F-01 | 部署配置端点匿名可读，直接泄露默认模型与实验面白名单 | 中 | `recon-01` |
| F-02 | 模型清单端点不存在，未知路径统一由 SPA 回退返回 `200`，易致资产误判 | 中（判据类） | `recon-01` |
| F-03 | 流式聊天端点匿名可用，`request_id`/`lab_id`/`phase` 等运行元数据随响应下发 | 高 | `recon-02` |
| F-04 | 前端产物含检索链路痕迹，RAG 面存在而框架不可判定 | 中 | `recon-03` |
| F-05 | 凭据校验接口以 `200 + success:false` 表达失败，状态码不可作判据 | 高 | `recon-06` |
| F-06 | 护栏放行原样回显，且 6 项安全响应头全缺 | 高 | `recon-07` |
| F-07 | 向量库无端口层证据，「未发现」不等于「不存在」 | 低（信息缺口） | `recon-04` |

---

# Attack Walkthrough

## Standalone Host — AIVP-DRILL (IP: 192.168.40.189)

### Enumeration

本主机为演练目标的 HTTP 入口。枚举分七步，覆盖 SKILL.md 定义的七类 AI 组件；全部以默认的 `passive` 分级执行，共发出 11 次请求（其中 `recon-07` 复用 `recon-02` 的响应，未新增请求）。

完整命令（可直接 copy/paste，逐字取自证据片段）：

```bash
# recon-01 LLM 引擎识别
curl -s http://192.168.40.189/api/config
curl -s http://192.168.40.189/v1/models

# recon-02 模型服务枚举
curl -s -N -X POST http://192.168.40.189/api/labs/MM_04/chat -H 'Content-Type: application/json' -d '{"prompt": "Reply with exactly: RECON-PROBE-OK"}'
curl -s http://192.168.40.189/api/me/runs?limit=1

# recon-03 RAG 库探测
curl -s http://192.168.40.189/explore
curl -s http://192.168.40.189/assets/index-BtcwQhVS.js

# recon-04 向量库发现（被动面）
curl -s http://192.168.40.189/api/labs/MM_05/summary

# recon-05 agent 系统识别
curl -s http://192.168.40.189/api/labs/DE_01/summary
curl -s http://192.168.40.189/api/me/runs?limit=1

# recon-06 MCP·工具面发现
curl -s -N -X POST http://192.168.40.189/api/secrets/validate -H 'Content-Type: application/json' -d '{"labId": "MCP_01", "answer": "recon-probe"}'
curl -s http://192.168.40.189/api/labs/MCP_01/summary
```

逐步判定汇总：

| 步骤 | 存在性 | 产品/引擎 | 截图 |
|---|---|---|---|
| recon-01 | 存在 | LongCat-2.5 | `recon-01-url.png` |
| recon-02 | 存在 | SSE 流式聊天面 | `recon-02-transcript.png` |
| recon-03 | 存在 | RAG 检索链路（痕迹） | `recon-03-url.png` |
| recon-04 | 不可判定 | 不可判定 | `recon-04-url.png` |
| recon-05 | 存在 | agent 编排面（推断） | `recon-05-url.png` |
| recon-06 | 存在 | 凭据校验预言机（MCP 信任边界面） | `recon-06-transcript.png` |
| recon-07 | 存在 | 护栏（放行原样回显） | `recon-07-transcript.png` |

**引擎与模型**：部署配置端点直接返回默认模型，无需任何认证。

```text
GET http://192.168.40.189/api/config → HTTP 200
{"training_labs_enabled":false,"training_lab_ids":["MM_05","MM_04","MM_07"],"artifact_replay_labs":["MM_05","MM_04","MM_07"],"llm_model_default":"LongCat-2.5"}
```

（证据：`evidence/recon-ai/recon-01.md`）

#### 截图（访问证明）

![recon-01 /api/config 的 JSON 响应（含 llm_model_default）](../evidence/recon-ai/shots/recon-01-url.png)


同一片段记录了反向验证：`/v1/models` 返回 **`200` + `text/html`** 的 SPA 回退页（完整响应 1702 字节），而非模型清单。因此该端点在本环境中**判定为不存在**，且不据此新增任何资产条目。这条判据是后续所有「端点是否存在」判断的前提：状态码 `200` 不等于资源存在。

**模型服务与会话面**：聊天端点匿名可用，返回 SSE 流。

```text
POST http://192.168.40.189/api/labs/MM_04/chat → HTTP 200
event: meta
data: {"request_id": "…", "lab_id": "MM_04", "phase": 3, "control_mode": "off", "artifact_replay": true}

data: {"content": "RE"}

data: {"content": "CON-PROBE"}

data: {"content": "-OK"}
```

（证据：`evidence/recon-ai/recon-02.md`）

#### 截图（访问证明）

![recon-02 聊天端点 curl + SSE 原文 + 判定](../evidence/recon-ai/shots/recon-02-transcript.png)


判读要点有三：其一，响应随 `set-cookie: aivp_sid` 建立匿名会话，属性为 `HttpOnly; Max-Age=2592000; Path=/; SameSite=lax`；其二，`meta` 事件下发 `phase` 与 `control_mode`，属运行配置的侧信道；其三，`data` 事件按分片推送，需拼接后才是完整回复——这决定了后续任何针对对话面的攻击都必须按流式语义处理，否则会误判为「截断」。

会话标识按 OPSEC 纪律只记指纹 `Bearer-26924458`（SHA-256 前 8 位），明文不入证据。

**检索与工具面**：前端产物含检索链路痕迹，RAG 面成立但框架不可判定。

```text
GET http://192.168.40.189/assets/index-BtcwQhVS.js → HTTP 200
…function Wd(e){return e&&e.__esModule&&Object.prototype.hasOwnProperty.call(e,"default")?e…
…（已截断：完整响应 392145 字节，命令可原样重跑取全文）
```

（证据：`evidence/recon-ai/recon-03.md`）

#### 截图（访问证明）

![recon-03 /explore 实验面（Phase 1–4）](../evidence/recon-ai/shots/recon-03-url.png)


工具面的证据更直接：校验接口对错误答案返回 `200`，失败语义藏在响应体。

```text
POST http://192.168.40.189/api/secrets/validate → HTTP 200
{"success":false,"message":"Nope."}

GET http://192.168.40.189/api/labs/MCP_01/summary → HTTP 422
{"detail":[{"type":"missing","loc":["query","request_id"],"msg":"Field required","input":null}]}
```

（证据：`evidence/recon-ai/recon-06.md`）

#### 截图（访问证明）

![recon-06 校验预言机 curl + 200/success:false + 422 schema](../evidence/recon-ai/shots/recon-06-transcript.png)


这里有一条对下游技能影响很大的判据：**该接口用 `200` 表达失败**。任何以状态码判别成败的自动化都会把「错误答案」记成「校验通过」，在取分场景中直接导致误报。

**护栏与输入输出**：一次无害回显被原样返回，说明输入未经过滤直达模型；同时 6 项安全响应头全部缺失。

```text
判定：存在（护栏（放行原样回显））
依据：无害回显探针被原样返回（RECON-PROBE-OK）；缺失安全响应头：Content-Security-Policy、X-Frame-Options、X-Content-Type-Options、Strict-Transport-Security、Referrer-Policy、Permissions-Policy；control_mode=off
```

（证据：`evidence/recon-ai/recon-07.md`）

#### 截图（访问证明）

![recon-07 护栏回显与缺失响应头的判定](../evidence/recon-ai/shots/recon-07-transcript.png)


**agent 编排面**：实验面接口以 `request_id` 为查询参数，暗示服务端存在按请求编排的运行实体；遥测端点匿名可读但当前为空。

```text
GET http://192.168.40.189/api/labs/DE_01/summary → HTTP 422
{"detail":[{"type":"missing","loc":["query","request_id"],"msg":"Field required","input":null}]}

GET http://192.168.40.189/api/me/runs?limit=1 → HTTP 200
{"runs":[]}
```

（证据：`evidence/recon-ai/recon-05.md`）

#### 截图（访问证明）

![recon-05 /api/labs/DE_01/summary 与 /api/me/runs 的响应](../evidence/recon-ai/shots/recon-05-url.png)

判读上须区分「面存在」与「框架可知」：`request_id` 语义与遥测端点同时成立，足以认定**编排面存在**；但运行时的框架指纹未被获取，故产品名一律记「不可判定」。此处以推断落定存在性、以「不可判定」锁住产品名，二者不可互相替代。

**向量库**：被动面无独立端口证据，如实记「不可判定」而非「不存在」。

```text
GET http://192.168.40.189/api/labs/MM_05/summary → HTTP 422
{"detail":[{"type":"missing","loc":["query","request_id"],"msg":"Field required","input":null}]}
```

（证据：`evidence/recon-ai/recon-04.md`）

#### 截图（访问证明）

![recon-04 /api/labs/MM_05/summary 的 422 响应](../evidence/recon-ai/shots/recon-04-url.png)


注：`recon-04` 与 `recon-05` 的截图哈希相同，属预期——两个 `summary` 端点返回**逐字节相同**的 422 响应体，浏览器渲染结果一致，非重复落盘。

### Vulnerability & Full Exploitation

**未达成（Not attempted）**。本次仅执行侦察，未对已识别入口发起任何利用动作，故本段不提供利用链。如实记录已确认的可推进入口与对应技能，供后续阶段衔接：

| 入口 | 已确认性质 | 建议承接技能 |
|---|---|---|
| `/api/labs/MM_04/chat` | 匿名 SSE 对话面，护栏放行原样回显 | `attack-ai-agent`（提示注入 / 记忆与工具滥用） |
| `/api/secrets/validate` | 匿名校验预言机，`200 + success:false` 语义 | `attack-mcp-tool`（工具面滥用 / 提权路径） |
| 前端检索痕迹 + `DE_10` RAG 实验面 | RAG 面存在，框架不可判定 | `attack-rag`（知识库投毒 / 检索操纵） |

### Privilege Escalation

**不适用**。未取得任何立足点，无权限可提升；本段按 S1「如适用」条款留空并说明理由。

### Proof

**未达成**。本主机未取分，无 `ai_vector.txt` / `trad_vector.txt` / `proof.txt` 可提交，因此不存在 flag 双通道记录。按 S1 的失分条款口径，该目标当前状态为「未提交」，而非「已提交但缺证据」——两者在评审中的含义不同，报告中不得混淆。

### Evidence Attribution

| 步骤 | 证据片段 | 截图（类型） | 输出 sha256（前 16） | 截图 sha256（前 12） |
|---|---|---|---|---|
| recon-01 | `evidence/recon-ai/recon-01.md` | `recon-01-url.png`（url） | `b199edf0ab34f306` | `ca501313a881` |
| recon-02 | `evidence/recon-ai/recon-02.md` | `recon-02-transcript.png`（transcript） | `f4df9d212ceb55b7` | `c7f1a9e49b8b` |
| recon-03 | `evidence/recon-ai/recon-03.md` | `recon-03-url.png`（url） | `efbd15a7acf72dd2` | `ea29965b9ac1` |
| recon-04 | `evidence/recon-ai/recon-04.md` | `recon-04-url.png`（url） | `7f4a083709669f0b` | `6ab9c85162c0` |
| recon-05 | `evidence/recon-ai/recon-05.md` | `recon-05-url.png`（url） | `d21a34d3f2f566d7` | `6ab9c85162c0` |
| recon-06 | `evidence/recon-ai/recon-06.md` | `recon-06-transcript.png`（transcript） | `0a77187e814fbe2c` | `7d97885185e0` |
| recon-07 | `evidence/recon-ai/recon-07.md` | `recon-07-transcript.png`（transcript） | `0c5daf1e1eac02df` | `210a9331a14a` |

三件套（确切命令 + 关键输出 + 截图）在 7 个步骤中均为「已提供」；脚本/PoC 均为「未使用脚本」；flag 双通道均为「未提供」（无 flag，见 Proof 段）。

## Chain 1 / Chain 2 / Domain Controller

**Not attempted**。本次任务范围仅为演练目标的侦察验证，未触及任何链式主机与域控。按 S1「不得捏造主机」原则，此处只声明未执行，不提供任何推测性内容。

## Intentionally Not Vulnerable Hosts

演练环境中未识别诱饵主机。就本次目标而言，其 AI 组件指纹明确（6/7 类有实证），判定为**非诱饵**（`decoy_suspected: false`，依据：存在 5 类以上 AI 组件实证，见 `evidence/recon-ai/ai-assets.json`）。

---

# Findings & Risk

| 编号 | 发现 | 严重度 | 影响 | 证据 |
|---|---|---|---|---|
| F-01 | `/api/config` 匿名可读，泄露 `llm_model_default` 与实验面白名单 | 中 | 攻击者无需探测即可确定模型族与靶面，缩短侦察窗口 | `recon-01.md` |
| F-02 | 未知路径由 SPA 回退返回 `200 text/html` | 中 | 以状态码判存在的自动化会把整段网络误判为有资产 | `recon-01.md` |
| F-03 | `/api/labs/{id}/chat` 匿名可用，`meta` 下发 `phase`/`control_mode` | 高 | 对话面直接暴露给未认证方，且运行配置外泄 | `recon-02.md` |
| F-04 | 前端产物含检索链路痕迹 | 中 | RAG 面可被定位；框架未知使投毒路径需进一步确认 | `recon-03.md` |
| F-05 | `/api/secrets/validate` 以 `200 + success:false` 表达失败 | 高 | 状态码判据必然误报为成功，取分场景直接失真 | `recon-06.md` |
| F-06 | 护栏放行原样回显；6 项安全响应头全缺 | 高 | 注入类载荷无输入侧过滤；缺 CSP 放大前端注入影响 | `recon-07.md` |
| F-07 | 向量库无端口层证据 | 低 | 资产清单存在 1 类不可判定项，需主动探测补全 | `recon-04.md` |

方法论层面的两点观察同样值得记录，因为它们直接决定后续阶段的判据设计：

1. **状态码不可作为存在性判据**。本目标同时出现两种反例：`200` 的 SPA 回退页（不存在）与 `200` 的失败校验（失败）。存在性必须由「状态码 + Content-Type + 响应体指纹」三元组判定，失败语义必须读响应体。
2. **「未发现」与「不存在」不可互换**。向量库在被动面无证据，若记为「不存在」，后续 `attack-rag` 会跳过向量面；记为「不可判定」才能保留补探测的空间。

---

# Recommendations

1. **优先修复失败语义**：`/api/secrets/validate` 应对校验失败返回 `4xx`，或在响应中引入可机读的错误码，避免调用方以状态码判成败。
2. **收敛部署配置外泄面**：`/api/config` 的模型名与实验面白名单属运行配置，应对匿名访问做最小化（仅暴露前端必需字段）。
3. **补齐安全响应头**：至少补 `Content-Security-Policy`、`X-Content-Type-Options`、`X-Frame-Options`、`Strict-Transport-Security`。
4. **对话面加认证与频率控制**：匿名会话可无限建立，且护栏对原样回显无拦截，建议在入口层加入认证与输入侧过滤。
5. **对下游技能的衔接建议**：以 `ai-model-…-02`（聊天面）、`ai-mcp-…-06`（校验预言机）、`ai-rag-…-03`（检索面）为起点推进 `attack-ai-agent` / `attack-mcp-tool` / `attack-rag`；`ai-vector-…-04` 需先以 `--profile active` 定向探测 6333/8080/19530/8000 完成定级。

---

# Reproducibility

全部结论可由下列命令从零重建（约 35 秒，含 7 次截图）：

```bash
# 1. 重建证据、截图、资产清单与验证报告
python tools/recon_ai/cli.py run --target http://192.168.40.189 --lab MM_04 \
  --out-dir evidence/recon-ai

# 2. 核对资产清单（7 条，1 类不可判定）
python tools/recon_ai/cli.py inventory --path evidence/recon-ai/ai-assets.json

# 3. 单步复现（以 recon-01 为例，输出应与片段「关键输出」一致）
curl -s http://192.168.40.189/api/config
curl -s http://192.168.40.189/v1/models

# 4. 核对正文内嵌截图：应为 7，且下列文件全部存在
grep -c '^!\[recon' report/recon-ai-report-sample-20261114.md
ls evidence/recon-ai/shots/*.png | wc -l
```

截图嵌入与构建说明：正文 7 处截图均以 `![]()` 内嵌（地址 `../evidence/recon-ai/shots/<file>.png`），路径相对**本报告文件**解析（`report/` 的上一级即仓库根），因此在预览器中可直接渲染。若需按 `report-exam` 的 rpt-05 流程产出 PDF，须在图片可解析的工作目录下执行：

```bash
cd report && pandoc --toc recon-ai-report-sample-20261114.md \
  -o ../OSAI-OS-XXXXX-Exam-Report.pdf
```

若跳过 `cd report`、直接从仓库根运行 pandoc，`../evidence/...` 会越出仓库根而丢图——PDF 中缺图即视为「无截图支撑」，属 §6.1 不可豁免项，故该目录约束不是习惯问题而是合规问题。

数据一致性说明：证据清单 `MANIFEST.jsonl` 逐行记录 `step_id`、命令、输出 sha256、时间戳、执行分级、留存入径与件套状态；重跑后命令与判定应一致，输出 hash 可能因模型回复的文字差异而变化（`recon-02` 的 SSE 分片属模型生成内容），该差异不影响判定结论，但会使 hash 不同——复核时应以「判定 + 关键字段」为准，并同时比对截图。

---

# Conclusion

本次试样验证了三件事。

**结构层面**：侦察证据可以不经二次加工直接进入 S1 的四章结构——Introduction/Objective/Requirements 承接范围与合规、Executive Summary 承接管理层概述与路径、Attack Walkthrough 承接逐主机五段式、Appendix 承接脚本/交互/截图索引。报告在「未取分」这一真实状态下依然保持了结构完整：Proof 段写明未达成、Privilege Escalation 段写明不适用、Chain/DC 段写明未执行，均未以文字替代证据。

**证据层面**：7 个步骤的三件套全部齐全，截图按 `url` 与 `transcript` 两类如实标注，关键输出逐字摘录且附 sha256，读者可从任一结论回溯到具体片段与截图。两处「不可判定」与「未取分」被显式记录，而非用推断填补——这是报告可信度的前提。

**能力层面**：侦察已把该目标的攻击面压缩为三张可执行入口（对话面、校验预言机、检索面）与一条待定级线索（向量库）。后续阶段的起点由「探索」变为「选择」，这正是侦察在 24h 窗口中的价值。

局限同样明确：本报告不含任何利用与取分结果，向量库未定级，且目标为演练实例而非考试主机，其资产构成不代表正式环境。若用于正式考试，需按 §4 映射补齐链式主机与域控小节，并在取分后补齐 flag 双通道。

---

# Appendix

## A. Scripts & PoC

本次未使用任何第三方脚本或 exploit。7 份证据片段的「脚本 / PoC」小节均记录为「未使用脚本：本步未登记脚本或 PoC 副本」。所有命令均为标准工具（`curl`）直接调用，无需来源标注或修改说明。

## D. AI Session / Prompt History

对目标模型的交互共一处（`recon-07` 复用 `recon-02` 的同一响应，不重复请求），全文如下（经人工校验采纳）：

`recon-02`（发送提示的步骤）：

```text
通道：POST http://192.168.40.189/api/labs/MM_04/chat
被交互模型：LongCat-2.5（由 recon-01 部署配置识别的默认模型）
提示（prompt）：Reply with exactly: RECON-PROBE-OK
输出（前 600 字符）：RECON-PROBE-OK
采纳：是（作为 recon-02 的护栏/服务面判定依据）
备注：本记录为目标模型交互留痕，不含 AI 辅助工具的会话内容。
```

`recon-07`（复用同一响应，不重复请求）：

```text
通道：POST http://192.168.40.189/api/labs/MM_04/chat（复用 recon-02 的响应）
被交互模型：LongCat-2.5（由 recon-01 部署配置识别的默认模型）
提示（prompt）：Reply with exactly: RECON-PROBE-OK
输出（前 600 字符）：RECON-PROBE-OK
采纳：是（作为 recon-07 的护栏/服务面判定依据）
备注：本记录为目标模型交互留痕，不含 AI 辅助工具的会话内容。
```

说明：`recon-06` 的 `POST /api/secrets/validate` 不构成模型交互（请求体无 `prompt` 字段），故不登记 AI 会话，证据片段中对应项为「未提供」。此项差异经人工核对确认，非漏记。

## E. Screenshot Index

正文每步均已内嵌上述截图（同一文件、同一哈希），本表仅提供**索引与校验值**，便于逐张对照与抽查。

| # | 文件 | 类型 | 内容 | sha256（前 12） |
|---|---|---|---|---|
| 1 | `recon-01-url.png` | url | `/api/config` 的 JSON 响应（含 `llm_model_default`） | `ca501313a881` |
| 2 | `recon-02-transcript.png` | transcript | 聊天端点 curl + SSE 原文 + 判定 | `c7f1a9e49b8b` |
| 3 | `recon-03-url.png` | url | `/explore` 实验面（Phase 1–4，55 lab） | `ea29965b9ac1` |
| 4 | `recon-04-url.png` | url | `/api/labs/MM_05/summary` 的 422 响应 | `6ab9c85162c0` |
| 5 | `recon-05-url.png` | url | `/api/labs/DE_01/summary` 的 422 响应 | `6ab9c85162c0` |
| 6 | `recon-06-transcript.png` | transcript | 校验预言机 curl + 200/`success:false` + 422 schema | `7d97885185e0` |
| 7 | `recon-07-transcript.png` | transcript | 护栏回显判定与缺失响应头 | `210a9331a14a` |

## F. Evidence Manifest

`evidence/recon-ai/MANIFEST.jsonl` 共 7 行，字段：`step_id`、`command`、`sha256`、`timestamp`、`profile`、`retention`、`pieces`（六项状态）、`screenshot_sha256`、`shot_kind`、`flag_dual`、`complete`。

汇总：7/7 行 `complete: true`；`pieces.截图` 7/7 为真；`pieces.AI 交互日志` 仅 `recon-02`/`recon-07` 为真（与 Appendix D 一致）；`flag_dual` 7/7 为「未提供」（无 flag，见 Proof 段）。
