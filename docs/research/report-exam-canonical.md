# report-exam 权威事实索引（research 阶段产物）

> **版本** v1.0 · **状态** 生效（阶段 1 收口）· **性质** 唯一事实来源（仅管 API / 官方事实 / 仓库现状）
> **适用技能** `skills/report-exam/`（把全套攻击证据组装为对齐 S1 官方模板的考试报告 PDF/`.7z`）
> **冲突优先级**（依 `skill-mainline-workflow.md` 文首）：官方考试事实（S1/S3）> GOVERNANCE「必须」条款 > CI-CD 门禁 > 本规范 > 技能局部约定
> **B7 适用性声明**：本技能**不依赖 PyRIT**（报告组装器，非攻击执行），故基线 B7（PyRIT==1.1.0 对象图）**不适用**；凡涉及 PyRIT 的旧名（`pyrit.orchestrator` / `*Orchestrator` / `AzureOpenAIChatTarget`）在本技能中均**不应出现**，出现即不符合项。

---

## 0. 来源清单（一手源）

| 简称 | 路径 / URL | 版本 | 类型 |
|---|---|---|---|
| **S1** | `docs/governance/references/OSAI-Exam-Report.pdf` | OffSec 官方报告模板（6 页，文件 213253 字节，mtime Jul 24 14:06） | 官方事实（权威） |
| **S1-digest** | `skills/report-exam/references/official-requirements.md` | 本仓库 S1 事实单一 digest | 派生（引用 S1） |
| **S3** | OffSec OSAI Exam Guide（help.offsec.com） | **未实际抓取核验**，仅占位/推导（见官方 requirements.md 头注） | 待核实 |
| **Gov** | `docs/governance/GOVERNANCE.md` | v1.0 | 治理（宪法级） |
| **CI** | `docs/standards/CI-CD.md` | v1.0 | 工程标准 |
| **GLOS** | `GLOSSARY.md` | 现行 | 术语基准 |
| **EVID-TOOL** | `tools/collect_evidence.py` | 现行（CI S1 校验一致） | 代码（已读源码） |
| **VERIFY** | `skills/verify-evidence/SKILL.md` | 现行 | 技能（已读） |
| **TPL-EN / TPL-ZH** | `skills/report-exam/templates/osai-report-template-{en,zh}.md` | 现行 | 模板（已读） |
| **MAP** | `skills/report-exam/references/evidence-mapping.md` | 现行 | 映射协议（已读） |
| **ATK-AI-EVID** | `evidence/attack-ai-agent-real/*.md` | 现行 7 个片段 | 真实证据（已列目录） |

> **S1 PDF 抽取说明**：沙箱内无 `pdftotext` / `pypdf` / `PyPDF2`，无法机读抽取 PDF 正文；其结构以 **S1-digest** 为已核实载体（digest 逐字摘自 PDF 且为仓库引用的事实单一来源）。结论以 S1-digest 为准，与 GOVERNANCE §7 交叉核对一致。

---

## 1. 报告结构事实（S1 / S1-digest / Gov §7.1）

**F-1.1（已核实·S1）** 报告四章**必须**齐全：
1. `Introduction / Objective / Requirements`
2. `Executive Summary`（管理层非技术概述 + `High-Level Attack Path`）
3. `Attack Walkthrough`（Chain 1、Chain 2 各 3 主机 + 域控、独立主机）
4. `Appendix`（长 PoC、补充截图、AI 会话/提示历史）

**F-1.2（已核实·S1）** 封面与标题逐字要求：
- Cover：`OffSec AI Red Teamer` / `Exam Report` / `student@youremailaddress.com` / `OSID: XXXXX` / 逐字版权声明（`Copyright © 2026 OffSec Ltd. All rights reserved.` + 禁止复制长句）。
- TOC **须含**条目 `Offsec AI Red Teamer Report`（注意 "Offsec" 小写 f）。
- 正文标题 `# Offsec AI Red Teamer Report`（小写 f）。

**F-1.3（已核实·S1）** `Executive Summary` 含 `## Overview` 与 `## High-Level Attack Path` 两项；High-Level Attack Path 为 **4 项**：Chain 1 / Chain 2 / Standalone / Domain Controller。

**F-1.4（已核实·S1 / Gov §7.2）** 每台计分主机小节**五段式**：枚举 → 漏洞描述与完整利用（含 prompt/payload）→ 提权（如适用，前后 `whoami`/`id`）→ flag 取证（Proof）→ 证据归属（引用 collect_evidence 片段、双通道一致）。

**F-1.5（已核实·S1）** flag 文件：
- `trad_vector.txt`（传统向量机，被攻陷用户家目录或 `C:\Users\Administrator\Desktop\`(Win)/`/root/`(Lin)）
- `ai_vector.txt`（AI 向量机，同位置）
- `proof.txt`（域控，位于 `C:\Users\Public\`）

**F-1.6（已核实·S1 / Gov §2.2）** 域控 `proof.txt` **仅可提交一次**（即使两条链均完成）。

**F-1.7（已核实·S1）** Appendix 至少含 A（Scripts & PoC）、D（AI Session / Prompt History）、E（Screenshot Index）。

**F-1.8（已核实·S1-digest §3）** 章节标题 `(official)` 须与 S1 逐字一致（含大小写）；`(extension)` 为本仓库质量补充（Target Inventory、Key Findings、Intentionally Not Vulnerable Hosts、Attack Timeline、Findings & Risk、Recommendations、Reproducibility），**不得删减任何 (official) 项**。

---

## 2. 证据契约事实（EVID-TOOL 源码 / Gov §6）

**F-2.1（已核实·源码）** `collect_evidence.py` 渲染原子证据片段，结构固定：
`### 步骤 <id>` → `> 目标 | 时间戳 | 证据片段（collect_evidence.py）` → `#### 确切命令`(bash) → `#### 关键输出`(text) → `#### 截图（访问证明）`(图/钩子) → （可选）`#### AI 交互日志` / `#### flag 取证（双通道一致）` → `#### 证据校验（五件套 / 三件套）` 表。

**F-2.2（已核实·源码/Gov §6.1）** 三件套（必需，§6.1）= 确切命令 + 关键输出 + 截图；五件套 = 三件套 + AI 交互日志（§6.3）+ flag 双通道（§6.2）。`--strict` 模式三件套不全退出码 1。

**F-2.3（已核实·源码）** 片段内 `#### 证据校验（五件套 / 三件套）` 表逐行给出"已提供/缺失/未提供"状态，供 verify-evidence 机读断言。

**F-2.4（已核实·MAP）** 证据复用两种无损方式：① 直接 include（`cat` 片段入对应主机小节，命令/输出/截图逐字不变）；② 按路径引用（正文标注 `（证据：evidence/.../aia-0X.md）`，长 PoC 入 Appendix A）。**禁止转写/改写/润色命令或输出**。

**F-2.5（已核实·MAP §E）** 报告内 IPv4、端口、版本、时间戳、请求数、结果须与片段逐字一致；双版亦同；域控 `proof.txt` 在报告中仅出现一次提交记录。

---

## 3. verify-evidence 门禁事实（VERIFY / Gov §8.2）

**F-3.1（已核实）** 八项检查单（vrf-01…vrf-08）对应 Gov §8.2：① 五要素齐+元信息；② 优先级与评分杠杆一致；③ 每步骤三件套齐；④ flag 双通道一致（面板值==报告截图/正文值）；⑤ AI 交互入附录；⑥ 报告结构完整可复现；⑦ 提交格式/命名/≤100MB/24h；⑧ 术语合规。

**F-3.2（已核实）** `verify-evidence` 是 `report-exam` 提交前置（§7.3）：八项全过 + `proof.txt` 提交次数==1 + 每个 flag 双通道一致 + 每计分目标三件套齐，方可通过。

**F-3.3（已核实·Gov §2.4）** 失分条款：未在控制面板**与**报告中同时提供 flag 内容与截图，或文档缺失，即对应目标失分。

---

## 4. 提交与格式事实（Gov §6.4 / S1-digest §7）

**F-4.1（已核实）** 报告 PDF 命名 `OSAI-OS-XXXXX-Exam-Report.pdf`（`XXXXX`=OSID）。
**F-4.2（已核实）** 归档 `.7z` 命名 `OSAI-OS-XXXXX-Exam-Report.7z`，**无密码**，≤100MB。
**F-4.3（已核实·S3占位/推导）** 提交窗口 = 考试结束后 24h；提交后不可修改、不可补加。**（S3 未实际抓取，待核实）**
**F-4.4（已核实·SKILL §6 rpt-05）** 渲染须带 `--toc`：`pandoc --toc report/*.md -o OSAI-OS-<OSID>-Exam-Report.pdf`，否则 TOC 不生成（违反 F-1.2）。

---

## 5. 双版策略事实（SKILL §5）

**F-5.1（已核实）** EN 官方版为**强制提交候选**（全英文正文）；ZH 内部版为可选镜像（永不上交）。
**F-5.2（已核实）** 两版事实、IPv4、端口、版本、时间戳、请求数、结果**逐字一致**；EN 版不得含中文正文（专名/工具名除外）。

---

## 6. 计分模型事实（Gov §2 / S1-digest §2）

**F-6.1（已核实·S1明示）** 8 计分目标 = 6 链式 + 1 独立 + 1 域控；总分 100、及格 75。
**F-6.2（推导）** 分值拆分（非 S1 原文，倒推）：AI 向量机 15/台、传统向量机 10/台、独立机 15、域控 5；链式构成 = 4 AI向量(60) + 2 传统(20)。推导达标最小组合：4 AI向量+独立=75 → AI 向量最高杠杆。
**F-6.3（已核实·Gov §2.1）** 环境 10 台：2×3 链式 + 独立 + 域控 + 2 诱饵机；诱饵机记为"确认不可利用"，不计分。

---

## 7. 现有 evidence 现状（仓库实查）

**F-7.1（已核实·目录实查 2026-11-14）** `evidence/attack-ai-agent-real/` 存在 7 个片段：`aia-01/02/03/04/08/09/10.md`（真实目标 `http://192.168.40.189/api/labs/MM_0x/chat`）。
**F-7.2（已核实·grep）** 全部 7 个 real 片段 `flag 双通道` 均为"否/未提供" → **当前无任何取分 flag 双通道证据**。报告须如实记"未达成/推进中"，不虚构。
**F-7.3（已核实）** `evidence/attack-ai-agent/*.md` 为演练/仿真，须与 `-real` 区分，避免混入正式提交。
**F-7.4（已核实）** `loot/registry.md` **尚未生成**（须实战流水线产生）；`report-exam` 组装以 `evidence/<skill>/*.md` 为索引自建主机→片段映射表（MAP §D）。

---

## 8. 术语基准（GLOS，已读）

**F-8.1（已核实）** 强制规范词：攻击链、独立主机、域控、AI 向量、传统向量、诱饵机、计分目标、flag、及格线、证据片段、质量基线、证据、TTP。
**F-8.2（已核实）** 废弃术语（`_Avoid_`，禁用）以 GLOSSARY.md 为准；本仓库强制规范词含 攻击链/独立主机/域控/AI 向量/传统向量/诱饵机/计分目标/证据片段/报告组装器/双版/证据归属/五段式。`check_glossary.py` 对 `skills/report-exam` 扫描 **PASS**（22 个废弃术语无命中）。

---

## 9. 校验器现状（实跑）

**F-9.1（已核实·实跑）** `python scripts/validate_skill.py` → `PASS：共校验 16 个技能，全部合规。`（`report-exam` 五要素齐全）。
**F-9.2（已核实·实跑）** `python scripts/check_glossary.py --scan skills/report-exam` → `PASS：术语一致性校验通过（检查 18 个废弃术语）。`

---

## 10. 已核实 / 待核实 / 已排除 三清单

### 已核实（可直接用于 to-spec）
- S1 四章结构、封面/TOC/标题逐字要求、五段式、flag 文件名、Appendix 必备项（F-1.*）
- collect_evidence 证据契约三/五件套结构（F-2.*）
- verify-evidence 八项检查单 + proof.txt 单次 + 提交前置（F-3.*）
- 提交命名/无密码/≤100MB、pandoc `--toc`（F-4.*）
- 双版策略与一致性（F-5.*）
- 计分模型 8 目标/100/75、诱饵机（F-6.*）
- 现有 evidence 现状与 flag 双通道缺口（F-7.*）
- 术语基准与校验器实跑 PASS（F-8/F-9）

### 待核实（实现/取证前必须取证闸）
- **VG-S3-1**：S3（OSAI Exam Guide）24h 提交窗口、≤100MB、评分细则 **未实际抓取官方源**，当前为占位/推导；正式提交前须复核（SKILL 与 official-requirements.md 均自注此缺口）。
- **VG-S3-2**：S1 PDF 正文未能机读抽取，结构以 digest 为准；若后续要逐字比对，需补 pdftotext 环境或人工核对 PDF。
- **VG-LOOT-1**：`loot/registry.md` 格式（列：编号/类型/内容/来源主机/证据片段路径/时间戳/状态/双通道）以 `MAP §A` 描述为暂定，实战产生后须与 `loot-manage` 实际格式对齐。
- **VG-PANDOC-1**：报告渲染依赖 `pandoc` 与 `7z`，沙箱/CI 是否预装需实测（影响 rpt-05 可机读性）。

### 已排除（明确不在本技能范围）
- **PyRIT 对象图（B7）**：report-exam 是报告组装器，不调用 PyRIT；任何 `pyrit.orchestrator`/`*Orchestrator`/`AzureOpenAIChatTarget` 均不出现。
- **offsec-report 旧 Python 流水线**（`report_data.json`/`merge_findings.py`/`build_report.py` 等）：本仓库不存在，已弃用；改用 collect_evidence + loot-manage + verify-evidence（SKILL §10.2）。
- **仿真数据 / 演练证据混入正式提交**：`-real` 与演练目录严格区分（F-7.3）。

---

## 11. 对象映射（SKILL 攻击路径 → 实现要素）

| SKILL 声明要素 | 本仓库对应实现 |
|---|---|
| 证据原子单元 | `tools/collect_evidence.py` 片段（三/五件套） |
| 战利品单一事实源 | `loot-manage` 登记簿 `loot/registry.md`（生成后） |
| 报告骨架 | `templates/osai-report-template-en.md` / `-zh.md` |
| 官方事实 digest | `references/official-requirements.md` |
| 证据→章节映射 | `references/evidence-mapping.md` |
| 提交前校验 | `skills/verify-evidence`（八项检查单） |
| 渲染/打包 | `pandoc --toc` + `7z a -mx=9`（rpt-05） |

---

## 12. 阶段 1 收尾：G0 门禁自核（B7 / B8）

| 编号 | 检查项 | 依据 | 实测结果 | 判定 | 结论 |
|---|---|---|---|---|---|
| B7 | PyRIT 版本与对象图 | pyrit==1.1.0 | 本技能不涉及 PyRIT；无 PyRIT 旧名；见§0 声明 | 符合（N/A） | — |
| B8-1 | 每条结论附一手来源 | 本文 §0–§11 | 每条 F-x 均标 S1/Gov/EVID-TOOL/MAP/源码/目录实查 | 符合 | — |
| B8-2 | issue/PR/commit 互链 | 后续阶段 | 阶段 2 起建 issue 并互链 | 待后续 | 待后续 |
| B8-3 | 推送双通道各试一次即停 | 推送约定 | 阶段 11 执行 | 待后续 | 待后续 |
| G0-§2.2 | 门禁记录表字段齐全 | 本节表格 | 字段齐全 | 符合 | — |
| 验收① | 每条结论可定位官方 URL/源码 | §0 来源表 | 是 | 符合 | — |
| 验收② | 版本号明确 | pyrit N/A；S1/Gov/CI 均标 v1.0 | 是 | 符合 | — |
| 验收③ | 每条攻击路径有对象映射 | §11 | 是 | 符合 | — |
| 验收④ | 待核实项逐条命名+取证方式 | §10 待核实清单 | 是（VG-S3-1/2、VG-LOOT-1、VG-PANDOC-1） | 符合 | — |
| 验收⑤ | 文档落盘 docs/research/ | 本文件 | `docs/research/report-exam-canonical.md` | 符合 | — |

**阶段 1 结论：PASS**（B7 N/A 已声明；B8 持续项于后续阶段闭合；无「缺来源/版本含糊/攻击路径未映射」类不符合项）。
