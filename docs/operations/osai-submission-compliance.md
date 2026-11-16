# OSAI AI-300 提交合规与材料归属决策记录

> **版本** v1.0 · **日期** 2026-11-15 · **状态** 生效（决策留痕）
> **输入**：`docs/governance/references/OSAI-Exam-Guide-snapshot.md` §6–§8、`docs/governance/GOVERNANCE.md` §2.4/§5.2/§6、`skills/report-exam/SKILL.md`、attack-infra 主线落地与闭环验证
> **性质**：决策依据 + 方案对比 + 择优结论 + 材料合规核查，固化目录归属约定

## 1. 决策依据来源（三重对齐）

| 来源 | 关键条款 |
|---|---|
| OSAI 考试规范（S3 快照 §6–§8） | §6 每步命令/输出/脚本/修改说明/截图，copy-paste 可复现；§2.4 失分条款（flag 须控制面板**与**报告双通道，缺失即失分）；§6 提交命名 `OSAI-OS-XXXXX-Exam-Report.pdf`、`.7z` 无密码、≤100MB、仅 PDF 入档、MD5 上传校验 |
| 最佳实践 | 含目标 IP/flag 的演练证据不入公共 git；正式交付物（报告/登记簿）入版本库；单一事实源防散落 |
| 项目约定 | `evidence/` gitignore（含时间戳不入库）；`loot/registry.md` 入库；`report/` 入库；`docs/specs|research|operations` 入库 |

## 2. 决策点与择优结论

### 决策 1：证据片段（含目标 IP + flag）入库策略

- **依据**：§6.1 要求 copy/paste 可复现，故证据不能脱敏；含内网 IP 属敏感信息。
- **方案对比**：A 入库（可版本控制但泄漏 IP）｜B 落盘 repo 内 + gitignore（可复现且不泄漏）｜C 入库 + 脱敏（可版本控制但违反 §6.1 可复现）。
- **采用 B**：证据落盘 `loot/attack-infra/`（8 份）+ `evidence/`，gitignore 不入库。理由：同时满足「可复现」与「敏感不入库」，符合项目既有 `evidence/` 约定。

### 决策 2：登记簿 `loot/registry.md`（含 flag 索引）入库

- **依据**：§5.2 战利品必须可被报告生成阶段无损回溯；registry.md 是单一事实源。
- **方案对比**：A 入库（可回溯、有先例）｜B 不入库（登记簿断裂，报告生成缺索引）。
- **采用 A**：已 commit（`5871d2c`）。理由：登记簿只存 flag 的索引（值 + 路径），证据本体在 gitignore 目录；入库是实现「无损回溯」的前提。

### 决策 3：报告 `report/` 入库

- **依据**：报告是正式交付物；`report/` 已有 `evidence-review-*.md` 入库先例。
- **方案对比**：A 入库（可追溯）｜B 不入库（报告散失）。
- **采用 A**：已 commit 两份 attack-multi-agent 验证报告（`5871d2c`）。正式考试终态 `OSAI-OS-XXXXX-Exam-Report.pdf/.7z` 由 `report-exam` 在考试窗口生成、本地提交（含全部 flag，不入 git）。

### 决策 4：`.gitignore` loot 规则处理

- **依据**：规则已随 `feat/attack-infra` 提交（`a558f2e`，PR #256）。
- **方案对比**：A 主 repo 也 commit（污染 framework 分支）｜B 不 commit 保留本地（临时对齐，rebase main 后自然同步）。
- **采用 B**：主 repo 本地保留规则（立即生效，防误 `git add -A` 带入 loot 产物），不 commit。

### 决策 5：主 repo 分支归属

- **依据**：主 repo 当前在 `feat/framework-docs-recovery`，attack-infra 代码/文档在 `feat/attack-infra`（PR #256）+ `origin/main`（PR #230 已合并）。
- **采用**：不切分支。framework 分支有未提交的 `contract-drift-prevention.md`（非本次范围）；attack-infra 资料在版本库内，PR #256 合并后 `main` 即可见。

## 3. 证据材料合规核查（对照考试条款）

| 检查项 | 考试条款 | 当前状态 | 结论 |
|---|---|---|---|
| 证据三件套（命令+输出+截图） | §6.1 | 命令✓ 输出✓ 截图=钩子占位 | 演练可接受；正式考试须真实截图 |
| flag 双通道 | §2.4 | 面板 `success=True`✓，访问证明 whoami/id 缺失 | vrf-04 阻断（诚实判定，防失分） |
| 战利品可回溯 | §5.2 | L-1/L-2 已登记 registry.md ✓ | 合规 |
| 证据清单组织 | §6.1 | `loot/attack-infra/` + `evidence/` 落盘 repo 内 ✓ | 合规 |
| 报告四章结构 | §7.1 | 由 `report-exam` 生成 | 待正式考试 |
| 提交命名/打包 | §6 | PDF + `.7z` 考试窗口生成 | 待正式考试 |

## 4. 已执行整改汇总

- 证据片段归位 `loot/attack-infra/`（gitignore，含目标 IP 不入库）
- 规格归位 `docs/specs/attack-infra-spec-{v1,v2}.md` 入库（`a558f2e`，PR #256）
- 登记簿 L-1/L-2 + 两份验证报告入库（`5871d2c`）
- `.gitignore` 扩展 `loot/*` + `!loot/registry.md`（feat/attack-infra 已提交，主 repo 本地同步）
- 临时文件全清（Temp 5 个 attack-infra 文件 + 测试夹具 + `/tmp/loop-verify/`）

## 5. 固化后的目录约定

| 资料类型 | 指定目录 | 入库 |
|---|---|---|
| 代码 | `tools/` | ✅ |
| 规格 v1/v2 | `docs/specs/` | ✅ |
| 事实索引/调研 | `docs/research/` | ✅ |
| 设计/验证/术语/审查/决策 | `docs/operations/` | ✅ |
| 战利品登记簿 | `loot/registry.md` | ✅ |
| 证据片段/侦察 | `loot/*`（除 registry.md）、`evidence/` | ❌（含目标 IP） |
| 报告 | `report/` | ✅ |
| 临时草稿 | 系统 Temp / repo 外临时目录 | ❌ |
