---
name: report-exam
priority: P0
domain: D11
scoring_unit: 通用
trigger: 各攻击技能取证完成、loot-manage 登记簿就绪，进入报告撰写与提交窗口（考试结束后 24h 内）
input: loot-manage 登记簿与证据片段索引、各技能 collect_evidence.py 证据片段、verify-evidence 校验结果、AI 交互日志
output: OSAI-OS-XXXXX-Exam-Report.pdf 及归档 OSAI-OS-XXXXX-Exam-Report.7z（≤100MB、无密码），满足 §6.4 命名与 §7.1 报告结构
---

# report-exam — 考试报告生成

把全部攻击证据组装为符合 S1 官方模板的考试报告：**Introduction/Objective/Requirements → Executive Summary（含 High-Level Attack Path）→ Attack Walkthrough（Chain1/Chain2 各 3 台主机 + 域控 + 独立主机）→ Appendix（长 PoC / 补充截图 / AI 会话历史）**，并完成 PDF 与 `.7z` 打包。对齐报告要求（S1，跨域能力；front-matter domain 以 D11 全谱系演练交付登记，系校验器单选约束下的就近对齐）。计分单元为通用（及格前提：未提交合规报告 = 全部目标失分，§2.4）。报告为考试结束后 24h 提交窗口内的**终态交付物**。

## 执行体

按「素材聚合 → 骨架组装 → 每主机成文 → 附录沉淀 → 打包校验」顺序推进。核心原则：证据片段**无损复用**（引用 `tools/collect_evidence.py` 产物，禁止转写改写命令与输出）；AI 辅助成文的内容写入前**必须**经人工校验（§5.5「最终报告由考生负责，非 AI」）。

### rpt-01 证据聚合与素材核对

1. 从 `loot-manage` 登记簿导出素材索引：全部计分目标（6 台链式主机 + 独立主机 + 域控）× 每主机的证据片段路径，核对无遗漏计分目标、每 flag 行双通道占位齐全。
2. 命令模板：`grep -E '^\| L-' loot/registry.md > report-materials-index.md`
3. 核对通过后按 §7.1 四章分派素材；缺失项回溯对应技能补录（不虚构）。

### rpt-02 报告骨架组装（§7.1 四章）

1. 固化四章骨架：Introduction/Objective/Requirements（客观陈述）、Executive Summary（管理层非技术概述 + High-Level Attack Path，路径图复用 `loot/attack-path.md`）、Attack Walkthrough（Chain1 → Chain2 → 独立主机 → 域控）、Appendix。
2. 命令模板：`pandoc report/00-skeleton.md -o report/skeleton.html`（或直接 markdown 组装）
3. High-Level Attack Path 必须覆盖已取分的全部计分目标与两条攻击链的汇聚方向。

### rpt-03 每主机小节成文（§7.2 五段式）

1. 每台主机小节固定五段：**枚举**（暴露攻击面，引用 recon/trad-01 类片段）→ **漏洞描述与完整利用**（copy/paste 可复现，引用利用步骤片段）→ **提权**（如适用，前后权限证明）→ **flag 取证**（访问证明截图 + 双通道一致）。
2. 证据引用方式：`include` 证据片段文件或按片段结构原样粘贴（命令/输出/截图三件套不变），长 PoC 分流附录并在正文留指引。
3. 命令模板：`for f in loot/<host>-*.md; do cat "$f"; done >> report/attack-walkthrough-<host>.md`
4. 第三方脚本/exploit 附来源链接或代码副本及修改说明（§6.1）。

### rpt-04 AI 会话历史入附录（§6.3）

1. 汇总全程 AI 交互记录（prompt、模型、输出、采纳/修改决策）为附录「AI 会话/提示历史」小节，标准不低于其它工具。
2. 命令模板：`cat loot/ai-*.md > report/appendix-ai-history.md`
3. AI 生成内容入正文的段落逐一标注「经人工校验采纳」，未校验内容不得入稿。

### rpt-05 PDF 与 .7z 打包（§6.4）

1. 命令模板：`pandoc report/*.md -o OSAI-OS-<OSID>-Exam-Report.pdf && 7z a OSAI-OS-<OSID>-Exam-Report.7z OSAI-OS-<OSID>-Exam-Report.pdf`
2. 合规自检：命名 `OSAI-OS-XXXXX-Exam-Report.pdf` / `.7z`；归档**无密码**；≤100MB；域控 `proof.txt` 仅提交一次（§2.2）。
3. 打包后移交 `verify-evidence` 做提交前全量校验（§7.3），**校验通过方可提交**；提交为终态操作，提交后不可修改。

## 质量门

以下产出**必须**全部满足，缺失任一即判定未过门禁，不得提交：

- 报告四章齐全（§7.1），Executive Summary 含 High-Level Attack Path。
- 每主机小节五段式齐全（§7.2），技术读者可 **copy/paste 逐步复现**（§6.1）。
- 每个 flag 均在正文/截图出现且与面板提交值一致（双通道，§6.2）。
- AI 会话历史已入附录（§6.3），AI 生成内容均经人工校验标注（§5.5）。
- 交付物命名合规、`.7z` 无密码且 ≤100MB（§6.4），并已经 `verify-evidence` 全量校验通过。

## 校验标准

- 报告结构与 S1 官方模板逐节对齐；主机覆盖 = 已取分计分目标全集，无遗漏。
- 证据片段引用无损：正文中的命令/输出与 `collect_evidence.py` 片段逐字一致。
- 与 `verify-evidence` 衔接：其输出（通过/阻断 + 缺失项清单）为提交前置。
- 术语符合 `GLOSSARY.md`（用「攻击链」「独立主机」「域控」「AI向量机」「传统向量机」等规范词，禁用 `_Avoid_` 废弃术语）。

## 失败与豁免

- 若某计分目标未取分，Attack Walkthrough 对应小节如实记「未达成」及已推进程度，不虚构利用过程。
- 若正文长度失控，长 PoC 与补充截图分流附录，正文保留可复现的最小完整链路（豁免依据：§7.1 附录设计意图）。
- 若截图缺失（取证遗漏），回溯对应技能按证据契约补录后再组装；禁止以文字描述替代访问证明截图（§6.2 不可豁免）。
- 若 24h 提交窗口临近而校验仍有非阻断项（如附录格式瑕疵），优先保「双通道一致 + 四章齐全 + 命名合规」阻断项清零后提交，剩余瑕疵记录在案。
