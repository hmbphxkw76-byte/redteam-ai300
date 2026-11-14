# OSAI AI 工具政策决策记录（T03）

> **性质**：合规决策留痕，非规范正文；事实依据为两份官方一手源。
> **日期**：2026-11-14（GMT+8） · **状态**：生效
> **书面回执**：**未发送**（可选、非阻断；决策不依赖回执）
> **关联**：`docs/governance/references/OSAI-Exam-Guide-snapshot.md` §2 / §11；`docs/governance/GOVERNANCE.md` §1.5 / §2.4 / §5.5；`report-exam-T02-firsthand-source.md`

---

## 1. 一手源清单

| 简称 | 官方页面 | 抓取日期 | 页面时间元数据 |
|---|---|---|---|
| S3 Exam Guide | https://help.offsec.com/hc/en-us/articles/46593096734612-OSAI-Exam-Guide | 2026-11-14 | "1 month ago" |
| AI Usage Policy | https://help.offsec.com/hc/en-us/articles/35549468971156-AI-Usage-Policy-in-OffSec-Exams | 2026-11-14 | "4 months ago" |

两页均经 WebFetch 定向读取原文；搜索结果摘要仅用于定位 URL，不用于证明事实。完整逐字段落见 `OSAI-Exam-Guide-snapshot.md` §2（Exam Restrictions）、§11（AI Usage Policy）。

## 2. 逐字引文（短引；全文见快照）

```text
The exam is entirely open book.
```

```text
Above all, this exam is designed with the active use of AI in mind, and we strongly encourage you to leverage it throughout every stage of your attack
```

```text
Learners who choose not to make use of AI will likely find the exam extremely challenging.
```

```text
there are restrictions on the use of AI chatbots and Large Language Models (LLMs), except in the case of the OSEE and OSAI exams which the use of AI chatbots and LLMs are allowed.
```

通用政策 `Prohibited AI Usage` 段的完整逐字原文见快照 §11，其例外限定为 `except for OSEE and OSAI which the usage is allowed`；`Allowed AI Usage` 段限定非交互式 AI 功能。本记录不转抄该段全文（C1）。

## 3. 事实判定

1. **两份官方文件一致，无冲突**：通用《AI Usage Policy in OffSec Exams》把 **OSAI 与 OSEE 并列**列为「允许使用 AI chatbot / LLM」的例外；OSAI Exam Guide 的 Exam Restrictions 明示 open book、无工具限制，并 `strongly encourage` 在攻击全阶段使用 AI。
2. **撤销过时结论**：15:21 会话记录的「AI 政策冲突（通用政策仅 OSEE 例外允许）」源于不完整/过时读取，本记录予以撤销；该风险不再列为高优先阻断项。
3. **适用边界**：允许使用 ChatGPT / Claude 类 LLM 及 PyRIT 等 AI 红队工具贯穿侦察、分析、利用、排错与报告辅助；仍**必须**遵守 `GOVERNANCE.md` §5.5（人工/自动化校验、最终报告由考生负责）与 §6.3（AI 交互全量留痕）。
4. **同页其他约束**：禁止从考试环境向本机下载应用/文件/源码（Kali VM 本地离线处理哈希等例外）；Discord 仅可用于检索信息，禁止寻求或接受他人协助。

## 4. 二手来源排除

- `lazyhackers.com`、`cybercertreviews.com` 等聚合/博客页面所称「ChatGPT 禁用 / Instant fail」与官方原文冲突，不进入本决策。
- 单一来源或转述不得作为政策判据；官方页面若更新，须重新抓取两页并更新本记录与快照。

## 5. 决策与执行

| 项 | 决策 |
|---|---|
| OSAI 考试全程使用 LLM | **允许**（官方鼓励），按 §5.5 / §6.3 留痕校验 |
| 向 `challenges@offsec.com` 发书面问询 | **不发送**；一手源已明确且互相印证，回执非阻断。如考前官方条款变更，重新核实并留痕 |
| T03 阻断级别 | 由「高优先风险闸门」降级为「合规留痕」 |
| T04 落点 | §1.5 增 S3-POLICY 指针；§5.5 改「政策一致性留痕」并引用本记录；§2.4 第 4 项「允许使用」由两份官方源共同支持 |
| T18 演练 runbook | 按「AI 全程可用」编写，仍须全量记录 prompt / 模型 / 输出 / 采纳决策 |

## 6. 完成判据自检

| 判据 | 结果 |
|---|---|
| 决策记录含两条一手源逐字引文与 URL | 是（§1 URL、§2 共 4 段官方原文短引 + 1 处全文指针） |
| §5.5 引用快照 §11 / 本记录 | 由 T04 落地 |
| 二手博客「ChatGPT 禁用」不进入决策 | 是（§4 明确排除） |
| 对外邮件须单独确认 | 未发送，符合「可选且非阻断」 |
