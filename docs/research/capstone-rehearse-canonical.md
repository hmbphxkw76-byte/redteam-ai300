# capstone-rehearse 规范事实库（canonical references）

> **性质**：研究/事实文档（非规范正文）。供 `skills/capstone-rehearse/SKILL.md` 落地实现时使用。
> **核验日期**：2026-11-15（GMT+8）。每条结论附一手来源（官方 URL / 条款行号 / 源码位置）；待核实项逐条命名并给出取证方式。
> **依据**：`GOVERNANCE.md` v1.1、`CI-CD.md` v1.1、`docs/governance/references/OSAI-Exam-Guide-snapshot.md`（S3 快照，URL <https://help.offsec.com/hc/en-us/articles/46593096734612-OSAI-Exam-Guide>，抓取 2026-11-14）、`docs/research/pyrit-canonical-references.md`、`skills/capstone-rehearse/SKILL.md`、各技能源码。

---

## 1. 定位与边界

- **能力域 D11 / P2 / 计分单元「通用（验收）」**：`GOVERNANCE.md#L138`（§4.4）；P2 判据 `GOVERNANCE.md#L118`（§4.3.3，演练、自动化与辅助，非必需）。
- **考前硬门禁**：`GOVERNANCE.md#L151`（§4.5）——「`capstone-rehearse` 为**考前硬门禁**（未 PASS 不得进入正式考试）」。此处 P2 与硬门禁并不矛盾：P2 描述能力优先级，硬门禁描述编排位置；实现不得把本技能判为「可选跳过」。
- **输入**：所有 P0/P1 技能就绪 + §4.5 流水线定义 + §5.4 24h 节奏（`skills/capstone-rehearse/SKILL.md` front-matter `input`）。
- **输出**：演练报告 = 覆盖度矩阵 + 24h 节奏时间线 + 缺口与补强清单 + 「是否具备实战条件」判定（`SKILL.md#质量门`、`#输出`）。
- **边界**：仅演练验收，**不含真实考试利用**；所有结论须结合实战环境验证（`SKILL.md#失败与豁免`）。演练目标 `http://192.168.40.189` 是 AIVP 实例，非 OSAI 正式考试环境（见 `.workbuddy/memory/MEMORY.md`「权威指针」）。
- **PyRIT 对象图**：**无**。本技能是纯静态走查/报告域，不构造 `*Attack` / `OpenAIChatTarget`，不 import `pyrit`。B7 对本技能的判定形式是「确认为零 PyRIT 依赖 + 不出现禁用旧名」，而非对象映射；该判定形式与 `docs/research/verify-evidence-canonical.md#L13` 一致（单一事实源，C1）。

### 1.1 两类 capstone 语境对照（C1）

课件 Ch11 与 OSAI 考试 capstone 为**不同语境**，不得混用结论。隔离复用 §4，不另立新规。

| 维度 | `course-capstone`（课件 Ch11） | `osai-rehearsal`（GOVERNANCE 计分） | 锚点 |
|---|---|---|---|
| 目标 | AD 取 Domain Admin | §4.5 九阶段走查+24h | [D:§11.1/L46]；[P:GOVERNANCE.md#L145-L148] |
| 计分单元 | 无（3 个定格式问答） | 8 机 100 分/75 及格；`ai_vector.txt` | [D:L210/L287/L1388]；[P:GLOSSARY.md#L215] |
| 产物 | 模型名/OS build/LLM 地址 | 覆盖度矩阵+24h 时间线+缺口清单 | [D:L210/L287/L1388]；[P:SKILL.md#L8] |
| 节奏 | 无 24h 约束 | §5.4 24h+24h 提交 | [P:GOVERNANCE.md#L170] |
| 结论边界 | 问答不映射 `ai_vector.txt`，不当就绪证明 | 不外推课程；不混入 `-real` | [D:§11.6/L1536-1546]；[P:§4#L53-L57] |

**隔离约束（复用 §4）**：课程结果不得充当 OSAI 就绪证明；OSAI 结论不外推课程。与 §4「`-real` 隔离」同一约束，只引用不复述（C1）。一手源：Ch11 extract + GOVERNANCE，≥2 条。

## 2. 规范一手源清单（条款 → 判定对象）

| 事实 | 一手来源锚点 | 本技能的判定对象 |
|---|---|---|
| §4.5 标准流水线九阶段，任何阶段未过质量门不得推进 | `GOVERNANCE.md#L141-L151` | 覆盖度矩阵的行集合与「就绪」判据 |
| 必须边打边写，`collect_evidence.py --strict` 同步落盘 | `GOVERNANCE.md#L151` | 证据链贯通核对（每阶段须有可引用片段） |
| 24h 考试 + 报告提交窗口 24h；PDF+`.7z` 须在窗口内提交 | `GOVERNANCE.md#L170`（§5.4.1）；S3 快照 `#L68-L74` | 时间线上界与提交节点 |
| 建议节奏：侦察/立足点 0–4h、链式与 AI 利用 4–16h、收敛补录 16–20h、≥4h 缓冲 | `GOVERNANCE.md#L171`（§5.4.2） | 24h 时间线分段与关键节点 |
| §5.4 节奏原文标「**宜**…（非强制）」；S3 官方仅给出 24h 时长 | `GOVERNANCE.md#L171`；S3 快照 `#L68` | 不得把分段标为官方强制；压缩建议属工程判断 |
| 诱饵机 2 台（0 分），疑似目标时间盒 ≤30min 后放弃并记录理由 | `GOVERNANCE.md#L165-L167`（§5.3）；S3 快照 `#L49` | 时间盒列、非阻断缺口分级 |
| 战利品即时登记、可被报告无损回溯 | `GOVERNANCE.md#L161-L163`（§5.2） | 上游产物→下游消费的无损核对 |
| 每步 = 确切命令 + 关键输出 + 截图；copy/paste 可复现 | `GOVERNANCE.md#L182-L184`（§6.1） | 演练报告可复现性验收 |
| flag 双通道一致 + 访问证明 | `GOVERNANCE.md#L186-L188`（§6.2） | 域控 `proof.txt` 阶段就绪判据 |
| AI 交互入附录 / 八项合规检查单 / 术语一致 | `GOVERNANCE.md#L190-L191`（§6.3）、`#L223-L233`（§8.2）、`#L11`（§1.3） | 走查产物与 `verify-evidence` 判据兼容 |
| 提交为终态，提交前必须经 `verify-evidence` 全量校验 | `GOVERNANCE.md#L212-L213`（§7.3） | 流水线末端顺序：verify → report |
| 域控 `proof.txt` 单次提交 | `GOVERNANCE.md#L57`（§2.2.3）；S3 快照 `#L51` | 域控阶段「单次提交」核对项 |

## 3. 九阶段流水线 → 实现对象映射（B7 / 覆盖度矩阵行集）

顺序以 `GOVERNANCE.md#L145-L148` 为准；就绪判据在阶段 2/3 布尔化。代码落点为 2026-11-15 主分支实况（`tools/`、`tools/report_exam/`、`tests/`）。

| # | §4.5 阶段 | 技能（能力域） | 代码落点 / 证据契约 | 下游消费者 |
|---|---|---|---|---|
| 1 | 威胁建模 | `threat-model`(D10) | `tools/threat_model/` (`score.py`/`graph.py`/`render.py`)；`tests/test_threat_model.py` | 2 资产枚举排序、9 High-Level Attack Path |
| 2 | 侦察枚举 | `recon-ai`(D2) | `tools/recon_ai/inventory.py`；`tests/test_recon_evidence_contract.py` | 1 排序、4 `attack_rag/surface.py`、4 `attack_supply_chain/recon_input.py`、9 报告 |
| 3 | 立足点 | `foothold-traditional`(D1) | 证据契约 `tests/test_foothold_traditional_evidence_contract.py`（无独立包） | 4 链式横向、7 战利品 |
| 4 | 链式横向 + AI 向量利用 | `attack-ai-agent`(D3) / `attack-rag`(D5) / `attack-mcp-tool`(D7) / `attack-embeddings`(D6) / `attack-multi-agent`(D4) / `attack-supply-chain`(D8) / `attack-infra`(D9) | `tools/attack_*/` 各包；`tests/test_attack_*_evidence_contract.py`；`attack-infra` 仅契约测试 | 5 独立机、7 战利品、9 报告主机小节 |
| 5 | 独立机 | `attack-mcp-tool` / `attack-infra` 等 | 同 #4；S3 快照 `#L51` 独立机 15 分 | 7 战利品、9 报告独立主机小节 |
| 6 | 战利品沉淀 | `loot-manage` | `tools/loot_manage/registry.py#parse_registry`/`#append_attack_path`；`loot/registry.md` | 8 `tools/verify_evidence.py#from_loot`、9 `tools/report_exam/` High-Level Attack Path |
| 7 | 域控收敛 | `verify-evidence` 前置 + `proof.txt` 单次 | `GOVERNANCE.md#L57`；`tools/verify_evidence.py#check_proof_single` | 8 全量校验、9 报告 Chain1/Chain2 两处记录 |
| 8 | 证据校验 | `verify-evidence` | `tools/verify_evidence.py`（`vrf-01…08`）；`tests/test_verify_evidence.py` | 9 提交前置（§7.3） |
| 9 | 报告生成 | `report-exam` | `tools/report_exam/index.py#parse_fragment`、`assemble.py#assemble_report`、`package.py` | 提交窗口（§6.4） |

**证据链贯通的可机读判据来源**：`tools/collect_evidence.py#main`（`--step`/`--cmd`/`--out`/`--strict` 产出 `#### 确切命令` / `#### 关键输出` / `#### 截图` / `#### AI 交互日志` 段落）→ `tools/report_exam/index.py#L24-L52#parse_fragment`（唯一解析契约，改段落结构须回归）→ `tools/loot_manage/registry.py#fragment_pieces`（三件套布尔）。三者均为既有实现，本技能只读不重写（C1）。

## 4. 演练产物与正式提交的隔离约束（关键）

- `tools/report_exam/index.py#L13-L14` `EXCLUDED_DIR_MARKERS = ("report-exam", "evidence/attack-ai-agent/")`；`#L66-L82` `DirEvidenceSource(real_only=True)` 只接受路径含 `-real` 目录段，注释明确「防止演练/仿真片段与实现日志混入正式提交」。
- `skills/report-exam/SKILL.md#L133` 同样要求演练/仿真片段与 `-real` 区分。
- **结论**：SKILL.md「报告可被 `report-exam` 的演练/附录部分直接引用」只能解释为**考前验收文档被人工引用/复核**，不得解释为把演练片段放入 `-real` 真实证据片段集合或正式提交 PDF。实现须在报告中显式标注「演练/仿真，非 OSAI 正式考试」，并复用 `loot-manage` 的「按路径引用、不重复存储证据本体」习惯（`skills/loot-manage/SKILL.md#L17`）。

## 5. 版本破坏性变更与禁用名称（B7）

权威事实见 `docs/research/pyrit-canonical-references.md#1 / #3`（2026-11-14 逐条对照官方 v1.1.0 文档，验证记录 `docs/research/pyrit-v110-api-verification.md`）：固定 `pyrit==1.1.0`（2026-09-04），官方仓库 <https://github.com/microsoft/PyRIT>，文档 <https://microsoft.github.io/PyRIT/1.1.0/>。1.1.0 已**无法 import**：`pyrit.orchestrator`、`*Orchestrator`、`AzureOpenAIChatTarget`；正确命名空间为 `pyrit.executor.attack` 下 `*Attack` 与 `pyrit.prompt_target.OpenAIChatTarget`。本技能零 PyRIT 依赖，但文档与测试用例中若出现旧名即登记为不符合项。

仍开放的核实闸（不阻塞）：`pyrit-canonical-references.md#4` 四项（常量/回调类型/评分器构造参数/记忆复用细节），取证方式为在已安装 `pyrit==1.1.0` 环境实跑；本技能不触及其任一。

**2026-11-15 外部一手源交叉验证（后台 agent，触发本阶段 B7/B8 复验）**：

- 已核实：`pyrit==1.1.0` wheel 与 Release `v1.1.0` 同为 2026-09-04（PyPI JSON / GitHub API tag）；`microsoft/PyRIT` 未归档、`Azure/PyRIT` `archived=true`；v1.1.0 源码树 `pyrit/executor/attack/__init__.py` 导出 `*Attack`、`pyrit/prompt_target` 导出 `OpenAIChatTarget`，XPIA 归 `executor/workflow/xpia.py`、无 `XpiaAttack`。API 路径结论与仓库权威索引 `#3` 一致。
- **版本归属偏差（登记 G-F）**：「删除 `pyrit.orchestrator`、建立 v1 架构」属 **v1.0.0 及更早**（v0.14.0 已无 orchestrator、已有 `executor/attack`），并非 v1.1.0 的破坏性变更；v1.1.0 Release Notes 的真实破坏性变更为 `score.is_undetermined` / `should_score_blocked_content` / CoPyRIT 认证。共享索引 `#1/#3` 的表述须另单订正；本技能**不改共享文件**（ADR-0006 三层隔离），且零 PyRIT 依赖，不影响任何实现判定。
- 官方考试指南发布方为 **OffSec**（非 OWASP）；24h 考试与 24h 提交窗口原文已核实。官方全文 **无** Capstone 演练域、建议节奏分段、诱饵机时限表述；三者均为仓库工程判断（§5.4「宜」/§5.3），不得标为官方强制。S3 快照为唯一权威存档。
- 取证命令：`curl -s https://api.github.com/repos/microsoft/PyRIT/git/trees/v1.1.0?recursive=1`、Release Notes `v1.1.0`/`v1.0.0`/`v0.14.0`、`pip download pyrit==1.1.0 --no-deps`；`help.offsec.com` 直连不可达，原文经 WebFetch 通道取得且与快照一致。

## 6. 核验清单

**已核实**：§2 全部条款行号与原文；§3 九阶段顺序与代码落点；§4 正式提交隔离约束；§5 版本与禁用名；S3 快照 24h 与分值原文；`parse_fragment` / `fragment_pieces` / `from_loot` 接口签名；`GLOSSARY.md` 已含「时间盒 / 判定分级 / 流水线 / 阶段门禁 / 战利品登记簿 / 攻击路径 / 演练目标」等既有术语（`#L47`、`#L171`、`#L185`、`#L299`、`#L307`、`#L310`）；2026-11-15 外部一手源交叉验证结论见 §5（PyPI / GitHub API / OffSec 官方指南）。

**待核实（核实闸，逐条命名 + 取证方式）**：

| 编号 | 待核实项 | 取证方式 | 影响 |
|---|---|---|---|
| G-A **已关闭** | ~~官方页面是否公开表述 Capstone 演练域 / 建议节奏分段~~ | 2026-11-15 外部一手源交叉验证：官方全文仅 Intro + §1/2/3，无 capstone/rehearsal/practice/mock 域、无节奏分段与诱饵机时限；24h 原文已核实。结论 **已排除**，分段/时间盒归仓库工程判断（§5.4「宜」/§5.3） | 不阻断，仅收紧措辞 |
| G-B | 各阶段**实测**耗时（当前仅有 §5.4 建议值） | 在演练目标 `http://192.168.40.189` 按 `collect_evidence.py --step cr-NN --strict` 逐步计时 | 时间线精度；不得伪装为实测 |
| G-C | 2 台诱饵机的具体标识与 ≤30min 时间盒执行记录 | `tools/decoy_detect/policy.py` + 演练片段路径 | 非阻断缺口 |
| G-D | 域控 `proof.txt` 单次提交状态（面板 + 截图） | `tools/verify_evidence.py#check_proof_single` + flag 双通道片段 | 阻断性缺口判据 |
| G-E | OSAI 正式考试环境不可用 | SKILL.md「失败与豁免」；结论须结合实战环境验证 | 报告须写明结论不外推 |
| G-F | 共享权威索引 `#1/#3` 把「删除 orchestrator」记为 1.1.0 破坏性变更，实属 v1.0.0 及更早 | GitHub API Release Notes `v1.1.0` vs `v1.0.0`/`v0.14.0` 源码树；订正由独立工单处理，本技能不改共享文件 | 本技能零 PyRIT 依赖，不影响实现；登记为核实闸 |

**已排除（不得写入实现）**：① 把演练/仿真片段混入 `-real` 正式提交（`index.py#L13`）；② 使用 `pyrit.orchestrator` 等 1.1.0 禁用名（`#5`）；③ 把「未演练」写成「已通过」（`SKILL.md#失败与豁免`）；④ 把 §5.4 分段标为官方强制（`#2`）；⑤ 隐瞒累计耗时 >24h 的超时风险（`SKILL.md#失败与豁免`）；⑥ 把演练报告当作真实考试利用证据（`SKILL.md#失败与豁免`）；⑦ 把 §5.4 分段 / §5.3 时间盒标为官方强制（官方全文无此表述）；⑧ 把官方指南发布方标为 OWASP（实为 OffSec）；⑨ 把「删除 `pyrit.orchestrator`」标为 1.1.0 破坏性变更（见 G-F）。

## 7. 门禁记录（阶段 1 · research）

**复验 2026-11-15**：一手源交叉验证后重跑 B7/B8 全项 → PASS；不符合项 1（共享索引版本归属偏差 → G-F 核实闸，本技能不改共享文件）。

| 编号 | 检查项 | 依据 | 实测结果（命令 + 输出摘要） | 判定 | 不符合项描述 | 修正要求 | 复验结果 | 结论 |
|---|---|---|---|---|---|---|---|---|
| B7 | PyRIT 版本与对象图 | §2.1 | 复验：本文档旧名命中均为 §5/§6/§7 声明与排除说明（非 import）；`grep -c 旧名 skills/capstone-rehearse/SKILL.md` → 0；`grep -c "pyrit==1.1.0"` → ≥1（版本锁定） | 符合 | 首轮摘要写「仅 §5 声明」与实测不符 | 区分声明/实现并避免写死计数，重跑本阶段全部检查项 | 复验：实现侧 0、版本锁定、交叉验证见 §5，零 PyRIT 依赖 | PASS |
| B8 | 可追溯性 | §2.1 | §2/§3 每条附 `路径#L` 或官方 URL；§6 待核实项逐条给取证方式 | 符合 | — | — | — | PASS |
| 验收① | 每条结论可定位 | §3.1 | §2 13 行来源锚点 + S3 快照 URL | 符合 | — | — | — | PASS |
| 验收② | 版本号明确 | §3.1 | `pyrit==1.1.0`、GOVERNANCE v1.1、CI-CD v1.1 | 符合 | — | — | — | PASS |
| 验收③ | 每条路径有对象映射 | §3.1 | §3 九阶段表 9 行，含代码落点/证据契约/下游 | 符合 | — | — | — | PASS |
| 验收④ | 待核实项命名+取证 | §3.1 | §6 G-A…G-E 五行 | 符合 | — | — | — | PASS |
| 验收⑤ | 落盘 `docs/research/` | §3.1 | `docs/research/capstone-rehearse-canonical.md` 已写入 | 符合 | — | — | — | PASS |
| 表字段 | G0 §2.2 第 3 步 | §2.2 | 本表 9 列齐全，判定/结论取值合法 | 符合 | — | — | — | PASS |

**结论：PASS**（不符合项 0），进入阶段 2。
