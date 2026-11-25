# OSAI 考试就绪优化：事实基线（阶段 1 research）

> **性质**：主线阶段 1 调研产物；只登记一手/权威来源事实与本仓库可复核实测，不定义流程。
> **基线**：`origin/main` @ `88eb10a` · 日期 2026-11-25 · `pyrit==1.1.0`
> **唯一可信源指针**：考试事实 `docs/governance/references/OSAI-Exam-Guide-snapshot.md`；证据契约 `docs/contracts/collect_evidence.contract.md`；主线 `docs/operations/skill-mainline-workflow.md`

## 1. 已核实（附来源锚点）

| # | 事实 | 来源 |
|---|---|---|
| F-1 | 8 个计分目标合计 100 分；AI 向量 15、传统 10、独立机 15、DC 5（仅提交一次）；75 分及格 | 快照 §3 `L46-56` |
| F-2 | 官方两个取消资格条件：控制面板与截图未同时给出 proof 内容；文档缺失 | 快照 §4 `L58-63` |
| F-3 | 文档须覆盖每步命令、脚本来源/修改、控制台输出、每阶段截图、可 copy/paste 复现 | 快照 §1 `L14-24` |
| F-4 | 24h 考试 + 24h 报告上传；提交后不可补件；PDF + 无密码 `.7z`，命名 `OSAI-OS-XXXXX-Exam-Report.*`，≤100MB，上传后 MD5 比对 | 快照 §5-§7 `L65-115` |
| F-5 | 考试开卷、无工具限制，明确鼓励 AI；禁止从考试环境下载文件（哈希/密钥等本地处理例外） | 快照 §2 `L26-44`；政策 `L148-161` |
| F-6 | `--shot-cmd` 只记录钩子、不执行，**不满足截图必需件**；`shot_status` 三态 `已提供/待补录/缺失` | 契约 v4 §1 `L17`、§2 `L44`、CHANGELOG v3 `L84` |
| F-7 | 片段节标题是 `tools.report_exam.index.parse_fragment` 的下游契约，改动即断链 | 契约 §4 `L61-71`；`tests/cross/test_contract_drift.py:47-100` |
| F-8 | 框架组合为 best-of-breed；AI 向量 75/100 为最高杠杆，报告与证据层 P0 | `docs/research/osai-ai300-framework-decision.md:47-60`；矩阵 `L22-48` |
| F-9 | 当前实现把钩子命令等同截图：`has_shot = bool(screenshot) or bool(shot_cmd)`，`complete` 随之判真 | `tools/collect_evidence.py:168,188` |
| F-10 | 实测片段存在误报：`aia-01.md` 截图节仅钩子命令，校验表却记「已提供」「三件套齐全：是」 | `evidence/attack-ai-agent-real/aia-01.md:461-488` |
| F-11 | `loot/registry.md` 仅 2 行、同一 MCP flag；全仓无 proof 文件、无 PDF/.7z、无 MD5 实现 | 本轮只读清点 + `docs/operations/osai-submission-compliance.md:50-55` |
| F-12 | 编排器只有被动门禁 H1–H6；演练器只校验不执行 | `tools/osai_orchestrator/runner.py:55-108`；`tools/capstone_rehearse/walk.py:25-42` |
| F-13 | 17 份 `SKILL.md` 无一引用 11 阶段唯一可信源；4/17 有完整门禁链；根 `spec-*.md` 24 份孤儿化 | 本轮 Grep/find 实测；`docs/operations/osai-submission-compliance.md:70` |
| F-14 | `attack-jailbreak` / `attack-multimodal` 有 tools+tests 但无 `SKILL.md`；矩阵已列 17/18 项 | 矩阵 `L44-47,149-159`；目录实测 |

## 2. 待核实（须在真实考试窗口取证，不由本仓库代填）

| # | 待核实项 | 取证方式 |
|---|---|---|
| U-1 | 实际 OSID 与提交文件名中的 `OS-XXXXX` | 控制面板个人资料；本仓库不得预填 |
| U-2 | 考试环境 8 个计分目标的真实 IP / 主机名 / 类型 | 考试窗口内 recon 落盘，不由演练目标 `192.168.40.189` 替代 |
| U-3 | 每目标 proof 文件真实内容与面板提交值 | 考试窗口内逐目标取证，必须面板 + 截图同屏 |
| U-4 | 真实截图文件（PNG）及其可复制性 | 考试窗口内截图并核对 PNG `IEND` |
| U-5 | 上传后门户给出的 MD5 与本地 MD5 是否一致 | 提交后比对；本仓库只能提供本地侧工具 |
| U-6 | 独立机达成前置（取得任一链内网立足点）的具体路径 | 考试窗口内实测 |

## 3. 已排除 / 不作为本轮事实

- 二手博客所称「OSAI 禁用 AI」：与 S3-POLICY 一手源冲突，排除（快照 `L148-161`）。
- `trad_vector.txt` / `ai_vector.txt` / `proof.txt` 文件名属 S1，不标为 S3 事实（快照 `L140-146`）。
- 附录 A/D/E 属仓库扩展，不是官方强制章节（同上）。
- 演练主机 `192.168.40.189`（OWASP AIVP）不是 OSAI 正式考试环境，仅作工程验证目标。
- 「4 台 AI 向量 + 2 台传统向量」为 S1/S3 推导，非官方明示；本优化以分值上界而非固定主机数建模。

## 4. 本轮明确假设（信息缺口）

1. **A-1**：真实考试环境、OSID、flag、截图均不可得；本轮只交付**判定与编排能力**，不生成任何伪提交件。
2. **A-2**：现有 `evidence/` 与 `loot/` 内容为演练夹具；所有新增门禁默认以 `--exam` 模式区分演练与正式。
3. **A-3**：共享文件（契约清单、GLOSSARY、CI 配置）存在并发会话；新增校验用独立脚本/独立步骤，不修改共用长行。
4. **A-4**：考试得分优先级按 `GOVERNANCE.md §2.3` 与矩阵 P0 排序：证据/报告关 > AI 向量 75 分 > 传统/DC 25 分。
5. **A-5**：`--shot-cmd` 的既有语义在演练模式保留（兼容既有 17 技能与测试），仅在 `--exam` 下把钩子判为不满足截图必需件。

## 5. 阶段 1 门禁（B7 / B8 / B9）

| 基线 | 判定 | 证据命令 |
|---|---|---|
| B7 | 符合（本阶段不引入 PyRIT 对象图变更） | `grep -R "pyrit.orchestrator" docs/research/osai-exam-readiness-canonical.md` 无命中 |
| B8 | 符合 | 每条 F/U 均附路径锚点；本文件落盘 `docs/research/` |
| B9 | 符合 | F-8 引用决策文档与矩阵，组合未偏离 P0→P2 排序 |

**结论：PASS**。
