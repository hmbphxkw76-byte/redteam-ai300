---
name: verify-evidence
priority: P0
domain: D11
scoring_unit: 通用
trigger: report-exam 已产出报告与归档，进入提交窗口（考试结束后 24h 内）前，必须先行提交前全量校验
input: report-exam 产出（PDF/.7z 命名与大小）、loot-manage 登记簿、各技能 collect_evidence.py 证据片段、域控 proof.txt 提交记录
output: 校验报告（通过/阻断 + 缺失项清单）、可机读校验结果（供 CI 复用），作为 report-exam 提交前置
---

# verify-evidence — 证据校验与 flag 提交

在 `report-exam` 产出之后、提交之前，按 GOVERNANCE §8.2 八项检查单对所有计分目标的证据与 flag 做**机器可判定**的全量校验。核心防线是 §6.2「flag 双通道一致」（控制面板提交值 == 报告截图/正文值）与 §2.4 失分条款（未同时提供 flag 内容与截图即失分），以及 §2.2 域控 `proof.txt` 仅可提交一次。任一阻断项不符即阻断提交（§7.3），避免提交后才发现、不可逆的失分。计分单元为通用（防失分，属报告/交付阶段，front-matter domain 以 D11 对齐 report-exam）。

## 执行体

按 §8.2 八项检查单逐项校验，复用 `loot-manage` 登记簿与各 `collect_evidence.py` 片段作为判定输入；任一阻断项不符即判定不通过、不得进入 `report-exam` 提交动作。

### vrf-01 五要素与元信息合规（检查单 1，§4.2）

1. 核对全部已纳管技能 SKILL.md 五要素齐全、元信息正确（对齐 §4.2 / §4.4）。
2. 命令模板：`python scripts/validate_skill.py`（CI S1 已覆盖，此处做本地终检）。

### vrf-02 优先级与评分杠杆一致（检查单 2，§4.3 / ADR-0002）

1. 核对技能优先级与计分杠杆一致：AI 向量为最高杠杆（4×AI向量 + 独立机 = 75 分即可及格）。

### vrf-03 每步骤证据三件套齐全（检查单 3，§6.1）

1. 对每个计分目标的每个攻击步骤，核对「确切命令 + 关键输出 + 截图（访问证明）」三件套齐全。
2. 命令模板：`grep -c '#### 确切命令' loot/<host>-*.md` 并与对应「关键输出」「截图」节计数比对，缺节即标记缺失。

### vrf-04 flag 双通道一致（检查单 4，§6.2 / §2.4）

1. 对每个 flag（`trad_vector.txt` / `ai_vector.txt` / `proof.txt`），比对**控制面板提交值**与**报告截图/正文值**，必须一致；任一缺失即触发 §2.4 失分条款。
2. 命令模板：`diff <(printf '%s' "$PANEL_FLAG") <(sed -n '/flag 取证/,/证据校验/p' loot/<host>-flag.md | grep -m1 -oE 'OSAI\{.*\}|OS[A-Z0-9-]+')`
3. 截图须含 `whoami`/`id` + flag 内容同屏（访问证明），面板提交值与截图值逐字一致。

### vrf-05 AI 交互已入附录（检查单 5，§6.3）

1. 核对全程 AI 交互（prompt、模型、输出、采纳/修改决策）已纳入报告附录，标准不低于其它工具；AI 生成内容入正文均经人工校验标注（§5.5）。

### vrf-06 报告结构完整可复现（检查单 6，§7.1 / §6.1）

1. 核对报告四章齐全（Introduction/Objective/Requirements、Executive Summary 含 High-Level Attack Path、Attack Walkthrough、Appendix）。
2. 每台主机小节五段式（枚举 / 漏洞与完整利用 / 提权 / flag 取证）技术读者可 copy/paste 逐步复现。

### vrf-07 提交格式 / 命名 / ≤100MB / 24h（检查单 7，§6.4）

1. 核对命名 `OSAI-OS-XXXXX-Exam-Report.pdf` / `.7z`，归档**无密码**，≤100MB，且在考试结束后 24h 内提交。
2. 命令模板：`7z l -slt OSAI-OS-<OSID>-Exam-Report.7z | grep -iE 'Encrypted|Size'` 与 `ls -l *.7z`。

### vrf-08 术语合规（检查单 8，§1.3）

1. 命令模板：`python scripts/check_glossary.py`；确保无 `_Avoid_` 废弃术语（用「诱饵机」「AI向量机」「独立机」「域控」等规范词）。

### 域控 proof.txt 单次提交约束（§2.2）

1. 显式校验：域控 flag（`proof.txt`）在控制面板**仅可提交一次**，即使两条攻击链均已完成；重复提交视为不合规并阻断。
2. 判定：维护提交记录计数，`proof.txt` 提交次数 == 1 方可通过。

## 质量门

以下**必须**全部满足，缺失任一阻断项即判定未过门禁，不得进入 `report-exam` 提交动作：

- 八项检查单（vrf-01…vrf-08）全部通过（无阻断项）。
- 域控 `proof.txt` 提交次数 == 1（§2.2）。
- 每个 flag 双通道一致（面板值 == 报告值，§6.2）。
- 每个计分目标证据三件套齐全（§6.1）。
- 校验结果以「通过」状态作为 `report-exam` 提交前置（§7.3）。

## 校验标准

- 判定客观、可机读：八项检查单逐项 boolean，缺失项清单明确到具体目标/步骤/检查项。
- 与 `report-exam` / `loot-manage` 衔接：输入为其产物，输出为其提交前置。
- 术语符合 `GLOSSARY.md`（用规范词，禁用 `_Avoid_` 废弃术语）。
- 输出可被 CI 复用：可机读结果（通过/阻断 + 缺失项）供提交 PR 时的自动化判定。

## 失败与豁免

- 若某计分目标未取分，对应证据缺失属预期，不计入阻断项；但报告须如实记「未达成」及已推进程度，不得虚构。
- 若双通道比对发现不一致，必须回溯补正（修正面板或报告其一）后重校，不妥协放行。
- 若 24h 提交窗口临近而仅剩非阻断瑕疵（如附录格式），优先保「双通道一致 + 四章齐全 + 命名合规 + proof.txt 单次」阻断项清零后提交，剩余瑕疵记录在案。
- 本技能为 S1-only：不产生 per-step `collect_evidence.py` 攻击调用，故不新增 S2 证据契约夹具（对齐 `report-exam` / `loot-manage`）；后续可加独立 S2 脚本断言全部证据片段三件套齐全 + 双通道一致（backlog 已标注「可加 S2 校验脚本」）。
