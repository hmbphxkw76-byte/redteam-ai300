---
name: report-exam
priority: P0
domain: D11
scoring_unit: 通用
trigger: 各攻击技能取证完成、loot-manage 登记簿就绪、verify-evidence 提交前校验通过，进入报告撰写与提交窗口（考试结束后 24h 内）
input: loot-manage 登记簿（loot/registry.md）、各技能 collect_evidence.py 证据片段（evidence/<skill>/*.md）、verify-evidence 校验结果、AI 交互日志
output: OSAI-OS-XXXXX-Exam-Report.pdf 及归档 OSAI-OS-XXXXX-Exam-Report.7z（≤100MB、无密码），满足 §7.1 结构、§6.1 可复现、§6.2 双通道、§6.3 AI 记录、§6.4 提交命名
---

# report-exam — OSAI / AI-300 官方规范渗透测试报告

把全部攻击证据组装为**严格对齐 OffSec 官方报告模板（`docs/governance/references/OSAI-Exam-Report.pdf`，下文称 S1）**的考试报告，并完成 PDF 与 `.7z` 打包。本技能是报告生成的**单一实现**：原 `offsec-report` 目录已合并入本技能（其名称弃用），治理登记（§4.4）仅以 `report-exam` 登记，避免双报告技能并存导致编排歧义。

核心约束来自 GOVERNANCE §6 / §7 / §8.2，与 S1 逐节对应；官方考试事实标注 **S1/S3**，本仓库工程约定标注 **工程标准**。

> **权威来源**：官方要求以 S1 为准。本技能所有结构、章节、flag 文件名、证据规则均摘自 S1 原文；S1 未覆盖的计分/时长细节引自 S3（经核实的 OffSec OSAI Exam Guide）。 digest 见 `references/official-requirements.md`。

---

## 0. 官方规范对齐（S1 / S3）

S1 是报告的**唯一强制结构来源**。其允许考生使用自有模板，只要"structured, professional"且满足 Requirements；本技能以 S1 自带模板为基线（更稳妥，避免结构扣分）。S1 明确要求（原文要点）：

1. 每个目标都要写"exploitation process"，覆盖**每一步、每条命令、任何代码/脚本、相关控制台输出**。
2. 使用已有脚本/exploit 时，**必须提供来源链接或代码副本，并记录所做的修改**。
3. 每个攻击阶段**必须有截图**支撑。
4. 报告须包含"summary and overview of the vulnerabilities / attacks / exploitation process"，且**详尽到技术读者可 copy/paste 逐步复现**。
5. **AI 工具（prompt、模型交互、AI 辅助 payload 生成）须以与其它工具同等标准记录**。
6. flag 文件：`trad_vector.txt`（传统向量机，位于被攻陷用户家目录或 `C:\Users\Administrator\Desktop\`(Win)/`/root/`(Lin)）、`ai_vector.txt`（AI 向量机，同位置）、`proof.txt`（域控，位于 `C:\Users\Public\`）。

---

## 1. 报告结构（必备章节，S1）

以下章节**必须**全部存在，且标注 **(official)** 的章节标题与措辞须与 S1 逐字一致（含大小写：`Offsec AI Red Teamer Report` 中 "Offsec" 为小写 f）。标注 **(extension)** 为本仓库在 S1 允许范围内的质量补充，**不得删减任何 (official) 项**。

```text
Cover                                          (official)
  OffSec AI Red Teamer
  Exam Report
  student@youremailaddress.com
  OSID: XXXXX
  Copyright © 2026 OffSec Ltd. All rights reserved.   (official — 逐字，见 references/official-requirements.md)
Table of Contents                              (official，须含 "Offsec AI Red Teamer Report")
# Offsec AI Red Teamer Report                  (official，body 标题)
## Introduction                                (official)
## Objective                                  (official)
## Requirements                               (official)
# Executive Summary
  ## Overview                                 (official — 管理层非技术概述)
  ## High-Level Attack Path                   (official — 4 项：Chain 1 / Chain 2 / Standalone / DC)
  (extension) Target Inventory & Point Allocation   (工程标准：8 计分目标 × 分值总表，源自 §2.2)
  (extension) Key Findings / Results at a Glance    (工程标准：关键漏洞一览)
# Attack Walkthrough                           (official)
  ## Chain 1
    ### Host 1 - HOSTNAME (IP: X.X.X.X)       (official)
      Initial Access / Exploitation (+ Screenshot)  (official；AI 向量 prompt/payload 在此记录)
      Privilege Escalation (if applicable) (+ Screenshot)  (official)
      Proof (+ Screenshot)                            (official)
    ### Host 2 / Host 3                       (same)
    ### Domain Controller - HOSTNAME (IP: X.X.X.X)     (official)
      Compromise (+ Screenshot)
      Proof (+ Screenshot，仅提交一次)
  ## Chain 2  (Host 1 / 2 / 3 + DC，同上)
  ## Standalone Host - HOSTNAME (IP: X.X.X.X) (official；AI Vector Evidence 嵌套于 Initial Access)
  (extension) Intentionally Not Vulnerable Hosts (+ Screenshot)   (工程标准：2 台诱饵机，记为"确认不可利用")
  (extension) Attack Timeline                              (工程标准：时间线，源自时间戳)
# Findings & Risk                              (extension；覆盖 S1 "summary/overview of vulnerabilities")
# Recommendations                              (extension)
# Reproducibility                              (extension；S1 强制 copy/paste 复现的集中说明)
# Appendix                                     (official)
  A. Scripts & PoC                             (official：长 PoC 代码 / 来源链接 / 修改说明)
  D. AI Session / Prompt History               (official：AI 会话与 prompt 全文)
  E. Screenshot Index                          (official：补充截图索引)
  B / C / F / G / H                            (extension)
```

**章节验收（§7.1）**：四章齐全（Introduction/Objective/Requirements → Executive Summary → Attack Walkthrough → Appendix）；Executive Summary 含 High-Level Attack Path；每台计分目标有独立小节；域控在 Chain 1 与 Chain 2 **两处**均有记录；诱饵机记为"确认不可利用"。

---

## 2. 每主机小节五段式（S1 §7.2 / §6.1）

每台计分主机的小节**必须**含以下段落（措辞对齐 S1）：

1. **枚举（Enumeration）** — 暴露攻击面（端口扫描、服务/版本探测、Web/API 发现、暴露的 AI 组件等）；引用对应 `recon-*` 证据片段。
2. **漏洞描述与完整利用（Vulnerability & Full Exploitation）** — copy/paste 可复现细节；对 AI 向量，**记录 prompt、payload、模型交互步骤**；引用/粘贴所用脚本或 exploit 并注明**修改点**。
3. **提权（Privilege Escalation，如适用）** — 含提权前后权限证明（`whoami`/`id`）。
4. **flag 取证（Proof）** — 显示 flag 文件内容 + 访问证明截图；`trad_vector.txt` / `ai_vector.txt` / `proof.txt` 依主机类型。
5. **（证据归属）** — 每段对应 `collect_evidence.py` 片段，截图与正文/面板值双通道一致（§6.2）。

---

## 3. 证据取证与引用方式（§6.1 / §6.2 / §6.3）

### 3.1 证据契约（现状，非重新发明）

本仓库已有统一证据管线，**本技能不重复取证**，仅**无损复用**：

- 原子证据单元 = `tools/collect_evidence.py` 产出的 markdown 片段（`证据片段`），结构固定：
  `### 步骤 <id>` → `> 目标 | 时间戳 | 证据片段（collect_evidence.py）` → `#### 确切命令`(bash) → `#### 关键输出`(text) → `#### 截图（访问证明）`(图/钩子) → （可选）`#### AI 交互日志` / `#### flag 取证（双通道一致）` → `#### 证据校验（五件套 / 三件套）` 表。
- **三件套（§6.1 必需）** = 确切命令 + 关键输出 + 截图。**五件套** = 三件套 + AI 交互日志（§6.3）+ flag 双通道（§6.2）。
- 战利品单一事实源 = `loot-manage` 登记簿 `loot/registry.md`（列：编号/类型/内容/来源主机/证据片段路径/时间戳/状态/双通道）。

### 3.2 引用方式（两种，均无损）

| 方式 | 场景 | 做法 |
|---|---|---|
| **直接 include（推荐）** | 同一主机多步骤连续成文 | 按 `loot/registry.md` 中该主机的证据片段路径，依次 `cat` 片段入对应主机小节 markdown；命令/输出/截图**逐字不变**。 |
| **按路径引用** | 正文叙述 + 长 PoC 分流附录 | 正文中以 `（证据：evidence/attack-ai-agent-real/aia-03.md）` 标注，读者可回溯；长代码块入 Appendix A 并留指引。 |

**禁止**：转写、改写、润色命令或输出（§7 规则 2 verbatim）。AI 辅助成文的内容写入正文前**必须**经人工校验并标注"经人工校验采纳"（§5.5）。

### 3.3 证据充分性判据（提交前置）

- 每个 flag **双通道一致**：控制面板提交值 == 报告正文/截图值（§6.2 / §2.4）；截图须含 `whoami`/`id` + flag 同屏（访问证明）。
- 每个阶段**有截图**；每个命令/输出/脚本/AI 交互均记录（§6.1 / §6.3）。
- 域控 `proof.txt` **仅可提交一次**（§2.2）。

---

## 4. 与现有 evidence 的映射

当前仓库已产出的真实证据位于 `evidence/`：

| 现有 evidence | 来源技能 | 报告落位 | 备注 |
|---|---|---|---|
| `evidence/attack-ai-agent-real/aia-01.md` | `attack-ai-agent` | **Standalone / AI-vector host → Initial Access/Exploitation**（agent I/O 通道、系统提示、护栏基线枚举）+ **Appendix D AI 会话历史** | 真实目标主机 `http://192.168.40.189/api/labs/MM_0x/chat` |
| `evidence/attack-ai-agent-real/aia-02..aia-12.md` | `attack-ai-agent` | 同上，按 step 顺序归入该主机小节的"漏洞描述与完整利用"段落（提示注入 / 记忆滥用 / 工具滥用） | 当前均**未提供 flag 双通道**（`| flag 双通道 | 否 | 未提供 |`），报告须如实记"未达成/推进中"，不虚构 |
| `evidence/attack-ai-agent/aia-*.md` | `attack-ai-agent`（演练/仿真） | 同结构，小节级标注「非 OSAI 正式考试 / 演练」 | 与 `-real` 区分，避免混入正式提交 |

**映射原则**（工程标准，适配自 failed-projects offsec-report 的 FRS→sections 思路，但改用本仓库管线）：

1. **以 `loot/registry.md` 为索引驱动**：每条登记行的"来源主机 + 证据片段路径"决定该片段落入哪台主机的哪个小节；`攻击路径` 小节驱动 Executive Summary 的 High-Level Attack Path。
2. **单主机聚合**：同一主机的全部 `aia-*` / `trad-*` / `recon-*` 片段聚为一节，**一主机一节**（S1 不允许多主机合并为一节）。
3. **AI 向量证据嵌套**：所有 prompt/payload/模型交互写入对应主机的 Initial Access/Exploitation 段，并**全量复制**至 Appendix D。
4. **未取分/未达成**：对应片段缺失属预期，小节记"未达成 + 已推进程度"，**不虚构利用过程**（§失败与豁免）。
5. **目标数量少于 10 台时**：显式标记 out-of-scope 主机小节（如 Chain 2 尚未推进则标注"Not attempted"），绝不捏造主机或 flag。

> 详细映射协议见 `references/evidence-mapping.md`；当前 real 证据仅覆盖 1 个 AI 向量主机，正式考试需补齐 Chain 1/2 各 3 台 + 域控 + 独立机（共 8 计分目标）。

---

## 5. 双版策略（适配补充，源自 failed-projects `offsec-report`）

failed-projects `offsec-report` 采用 **ZH 内部版 + EN 官方版** 双版。本仓库工作语言为中文、提交语言为英文，故适配为：

| 维度 | EN 官方版（**提交候选，强制**） | ZH 内部版（**可选镜像**） |
|---|---|---|
| 用途 | OffSec 阅卷 | 团队内部复核 |
| 语言 | 全英文（含正文） | 中文正文 + 英文章节标题 |
| 文件名 | `OSAI-OS-XXXXX-Exam-Report-<YYYYMMDD>-EN.md/.pdf` | `...-Report-<YYYYMMDD>-ZH.md/.pdf` |
| OSID/邮箱 | 真实值 | 演练可 N/A |
| 证据 ID / flag / 命令 / 输出 | 与 ZH 版**逐字一致** | 同左 |

**约束**：EN 版不得含中文正文（专名/工具名除外）；两版事实、IPv4、端口、版本、时间戳、请求数、结果必须一致；提交**仅** EN 版，命名 `OSAI-OS-XXXXX-Exam-Report.pdf`（§6.4）。ZH 版永不上交。

---

## 6. 执行体

按「素材聚合 → 骨架组装 → 每主机成文 → 附录沉淀 → 打包校验」推进。**AI 辅助成文内容写入前必须经人工校验**（§5.5）。

### rpt-01 证据聚合与素材核对
1. 从 `loot-manage` 登记簿导出素材索引：全部计分目标（6 链式 + 独立 + 域控）× 每主机证据片段路径，核对无遗漏计分目标、每 flag 行双通道占位齐全。
2. 命令模板：`grep -E '^\| L-' loot/registry.md > report-materials-index.md`
3. 缺失项回溯对应技能补录（不虚构）；无 `loot/` 时直接以 `evidence/<skill>/*.md` 为索引，自建主机→片段映射表。

### rpt-02 报告骨架组装（§7.1 四章）
1. 固化四章骨架：Cover（含逐字 Copyright）→ TOC（含 "Offsec AI Red Teamer Report"）→ Introduction/Objective/Requirements → Executive Summary（Overview + High-Level Attack Path，路径复用 `loot/registry.md` 攻击路径）→ Attack Walkthrough（Chain1 → Chain2 → 独立主机 → 域控）→ Appendix。
2. 模板：`templates/osai-report-template-en.md`（官方英文）/ `templates/osai-report-template-zh.md`（中文镜像）。

### rpt-03 每主机小节成文（§7.2 五段式）
1. 每台主机固定五段：枚举 → 漏洞描述与完整利用（copy/paste 可复现，AI 向量记 prompt/payload）→ 提权（如适用，前后权限证明）→ flag 取证（访问证明截图 + 双通道一致）。
2. 证据引用：按 §3.2 **直接 include** 对应 `collect_evidence.py` 片段（`cat evidence/.../aia-0X.md >> report/<host>.md`），长 PoC 分流 Appendix A 并在正文留指引。
3. 第三方脚本/exploit：附来源链接或代码副本 + 修改说明（§6.1 / S1）。

### rpt-04 AI 会话历史入附录（§6.3）
1. 汇总全程 AI 交互（prompt、模型、输出、采纳/修改决策）为 Appendix D「AI 会话/提示历史」，标准不低于其它工具。
2. 命令模板：`cat evidence/attack-ai-agent-real/aia-*.md | sed -n '/AI 交互日志/,/证据校验/p' >> report/appendix-ai-history.md`
3. AI 生成内容入正文段落逐一标注「经人工校验采纳」，未校验不得入稿。

### rpt-05 PDF 与 .7z 打包（§6.4）
1. 渲染：EN 版 `pandoc --toc report/*.md -o OSAI-OS-<OSID>-Exam-Report.pdf`（中文镜像同法生成 `-ZH.pdf`）。**必须带 `--toc`**，否则 S1 要求的目录（须含 `Offsec AI Red Teamer Report` 条目）不会生成。
2. 合规自检：命名 `OSAI-OS-XXXXX-Exam-Report.pdf` / `.7z`；归档**无密码**；≤100MB；域控 `proof.txt` 仅提交一次（§2.2）。
3. 打包后移交 `verify-evidence` 做提交前全量校验（§7.3），**校验通过方可提交**；提交为终态，提交后不可修改。
4. 命令模板：`pandoc --toc report/00-skeleton.md report/<host>*.md report/appendix*.md -o OSAI-OS-<OSID>-Exam-Report.pdf && 7z a -mx=9 OSAI-OS-<OSID>-Exam-Report.7z OSAI-OS-<OSID>-Exam-Report.pdf`

---

## 7. 质量门

以下**必须**全部满足，缺失任一即判定未过门禁，不得提交：

- 报告四章齐全（§7.1），Executive Summary 含 High-Level Attack Path。
- 每主机小节五段式齐全（§7.2），技术读者可 **copy/paste 逐步复现**（§6.1）。
- 每个 flag 均在正文/截图出现且与面板提交值一致（双通道，§6.2）。
- AI 会话历史已入附录（§6.3），AI 生成内容均经人工校验标注（§5.5）。
- 交付物命名合规、`.7z` 无密码且 ≤100MB（§6.4），并已通过 `verify-evidence` 全量校验。
- 域控 `proof.txt` 仅提交一次（§2.2）。

---

## 8. 校验标准

- 报告结构与 S1 官方模板逐节对齐；主机覆盖 = 已取分计分目标全集，无遗漏、无捏造。
- 证据片段引用无损：正文命令/输出与 `collect_evidence.py` 片段逐字一致（§3.2）。
- 与 `verify-evidence` 衔接：其输出（通过/阻断 + 缺失项清单）为提交前置（§7.3）。
- 术语符合 `GLOSSARY.md`（用「攻击链」「独立主机」「域控」「AI向量机」「传统向量机」「诱饵机」，禁用 `_Avoid_` 废弃术语）。
- 双版一致：EN/ZH 两版证据 ID、flag、命令、输出、IPv4、时间戳逐字一致（§5）。

---

## 9. 失败与豁免

- 若某计分目标未取分，Attack Walkthrough 对应小节如实记「未达成」及已推进程度，不虚构利用过程（§4 映射原则 4）。
- 若正文长度失控，长 PoC 与补充截图分流附录，正文保留可复现的最小完整链路（豁免依据：§7.1 附录设计意图）。
- 若截图缺失（取证遗漏），回溯对应技能按证据契约补录后再组装；禁止以文字描述替代访问证明截图（§6.2 **不可豁免**）。
- 若 24h 提交窗口临近而校验仍有非阻断项（如附录格式瑕疵），优先保「双通道一致 + 四章齐全 + 命名合规 + proof.txt 单次」阻断项清零后提交，剩余瑕疵记录在案。

---

## 10. 与 failed-projects `offsec-report` 的差异说明（溯源）

本技能**适配自** `D:/文档/GitHub/failed-projects/redteam-forge/skills/offsec-report/SKILL.md`（v2.0.0），结合本仓库治理框架（GOVERNANCE §4.2/§6/§7/§8.2、GLOSSARY、collect_evidence.py、loot-manage、verify-evidence）做了以下**新增/修改**：

### 10.1 解剖结构对齐治理（关键修改）
- **原版**：自定义 front-matter（`exam_track` / `sasmp_version` / `bonded_agent` 等）+ 自由章节。
- **本版**：改为本仓库强制解剖结构（§4.2）——`name/priority/domain/scoring_unit/trigger/input/output` + `执行体/质量门/校验标准/失败与豁免`，保证 `validate_skill.py` 与 §8.2 一致性校验通过。

### 10.2 证据管线替换（关键修改，非新增 Python 管线）
- **原版**：依赖 `report_data.json` + `merge_findings.py` + `build_report.py` + `validate_report.py` + `md2pdf.py` + `finalize_report_data.py` 一整套 FRS 自动填充流水线（失败项目自带，本仓库**不存在**）。
- **本版**：**弃用该 Python 流水线**，改用本仓库已有且经 CI 验证的管线——`collect_evidence.py` 片段（五件套/三件套）+ `loot-manage` 登记簿 + `verify-evidence` 提交前校验。引用方式改为「直接 include 片段 / 按路径引用」（§3.2），保证证据无损且可机读校验。不引入未经本仓库验证的脚本。

### 10.3 官方事实与工程标准分离（新增，治理要求）
- **原版**：将考试事实与内部约定混写。
- **本版**：凡 S1/S3 官方事实标 **S1/S3**，凡本仓库工程约定标 **工程标准**，与 GOVERNANCE §1.5 一致；新增 `references/official-requirements.md` 作为官方事实 digest 单一来源。

### 10.4 章节映射与现有 evidence 绑定（新增，用户要求）
- **原版**：通用 10 机模板，无本仓库证据绑定。
- **本版**：新增 §4「与现有 evidence 的映射」与 `references/evidence-mapping.md`，把 `evidence/attack-ai-agent-real/aia-*.md` 显式映射到 Standalone/AI-vector 主机小节与 Appendix D，并说明当前仅覆盖 1 个 AI 向量主机、flag 双通道未提供等现状。

### 10.5 双版策略务实化（修改）
- **原版**：默认产出 ZH+EN 双版且 EN 为提交候选。
- **本版**：保留双版概念，但明确 **EN 官方版为强制提交候选**、ZH 为可选内部镜像；强调两版证据 ID/命令/输出逐字一致（§5）。

### 10.6 计分/环境事实以本仓库推导为准（对齐）
- 统一采用本仓库 §2.2/§2.3 推导：8 计分目标 / 100 分 / 及格 75；构成 = 4 AI向量(60)+2 传统(20)+独立(15)+域控(5)；域控 proof.txt 单次（§2.2）。

### 10.7 未照搬项（说明）
- 原版的 `sasmp` 绑定智能体（`07-compliance-audit-specialist`）、`exam_track: core` 等失败项目专属机制不在本仓库体系内，已省略。
- 原版 `examples/report_data.simulated-10host.json` 等仿真数据不在本仓库复用；本版以 `templates/osai-report-template-*.md` 取代其占位结构。

> 治理登记：本技能为报告生成的**唯一实现**，已并入原 `offsec-report` 目录内容；GOVERNANCE §4.4 仅以 `report-exam` 登记（原 `offsec-report` 名称弃用）。
