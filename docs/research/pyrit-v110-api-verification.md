# PyRIT v1.1.0 API 一手源核实记录

> **类型**：research（阶段 1 交付物）· **对象**：`attack-ai-agent` 的 PyRIT 原生实现
> **版本锁定**：`pyrit==1.1.0`（2026-09-04）· **取证日期**：2026-11-14
> **依据**：`docs/operations/skill-mainline-workflow.md` §3.1 验收标准 ①–⑤、B7 / B8
> **上游输入**：`docs/research/pyrit-canonical-references.md`、`docs/research/pyrit-native-api-attack-ai-agent.md`、`skills/attack-ai-agent/SKILL.md`、issue #83 规格 v1

## 1. 取证方法

本轮全部结论来自**官方一手源**（PyRIT v1.1.0 文档站与仓库），第三方材料仅用于定位，不作判定依据。为避免网页摘要截断造成误判，对关键结论同时抓取原始 HTML 并以确定性字符串计数复核。

| 编号 | 一手来源 | 用途 | 复核方式 |
|---|---|---|---|
| S1 | [文档首页 v1.1.0](https://microsoft.github.io/PyRIT/1.1.0/) | 版本、初始化样例、结果打印机 | 原文字符串计数 |
| S2 | [API Reference 索引](https://microsoft.github.io/PyRIT/1.1.0/api/index) | 26 个模块清单 | 链接枚举 |
| S3 | [`pyrit.executor.attack`](https://microsoft.github.io/PyRIT/1.1.0/api/pyrit-executor-attack) | 攻击策略、执行器、配置对象签名 | 原始 HTML 902,931 字节 + 关键词计数 |
| S4 | [`pyrit.executor.workflow`](https://microsoft.github.io/PyRIT/1.1.0/api/pyrit-executor-workflow) | XPIA 工作流 | 原始 HTML + 类名/构造参数提取 |
| S5 | [`pyrit.converter`](https://microsoft.github.io/PyRIT/1.1.0/api/pyrit-converter) | 转换器子类名 | 原始 HTML 2,530,343 字节 + 类名计数 |
| S6 | [`pyrit.memory`](https://microsoft.github.io/PyRIT/1.1.0/api/pyrit-memory) | 记忆后端类名 | 页面 API 提取 |
| S7 | [`pyrit.setup`](https://microsoft.github.io/PyRIT/1.1.0/api/pyrit-setup) | `initialize_pyrit_async` 与 `memory_db_type` 取值 | 原始 HTML 351,850 字节 + 签名提取 |
| S8 | [`pyrit.score`](https://microsoft.github.io/PyRIT/1.1.0/api/pyrit-score) | 评分器类名 | 原始 HTML + 类名计数 |
| S9 | [`pyrit.prompt_target`](https://microsoft.github.io/PyRIT/1.1.0/api/pyrit-prompt-target) | 目标类名与回调 | 原始 HTML + 类名计数 |
| S10 | [官方仓库](https://github.com/microsoft/PyRIT) | 组件归属与版本来源 | 仓库 provenance |

## 2. 已核实结论

| 编号 | 结论 | 一手来源 | 证据摘要 |
|---|---|---|---|
| V1 | 版本为 `pyrit==1.1.0`，删除 `pyrit.orchestrator`，编排器更名为 `pyrit.executor.attack` 下的攻击策略 | S1、S10 | 文档站路径含 `/1.1.0/`；`Azure/PyRIT` 已归档 |
| V2 | `PromptSendingAttack(objective_target=..., attack_converter_config=..., attack_scoring_config=..., prompt_normalizer=..., max_attempts_on_failure=0, ...)` | S3 | 构造参数表；关键字构造形状 |
| V3 | `RedTeamingAttack(objective_target=..., attack_adversarial_config=..., attack_scoring_config=..., max_turns=10, score_last_turn_only=False, ...)` | S3 | 构造参数表，`max_turns` 默认 10 |
| V4 | `AttackExecutor(max_concurrency=1)`；`execute_attack_async(attack=..., objectives=Sequence[str], field_overrides=..., return_partial_on_failure=False, attribution=..., broadcast_fields=...) -> AttackExecutorResult` | S3 | 构造与方法签名原文 |
| V5 | `AttackConverterConfig` / `AttackAdversarialConfig` / `AttackScoringConfig` / `RTASystemPromptPaths` 均位于 `pyrit.executor.attack`；`AttackScoringConfig` 承载 `objective_scorer` | S3 | 类清单 39 项 + 配置项计数 61 次 |
| V6 | 转换器子类 `Base64Converter`、`LeetspeakConverter`、`TranslationConverter`、`ROT13Converter` 在 `pyrit.converter` 均存在 | S5 | 原始 HTML 计数分别 4 / 4 / 11 / 4 次 |
| V7 | 记忆后端类为 `SQLiteMemory`（支持文件型与内存型数据库）与 `AzureSQLMemory`，抽象接口 `MemoryInterface`，单例入口 `CentralMemory` | S6 | 类定义与构造参数 `db_path` 等 |
| V8 | `initialize_pyrit_async(memory_db_type: MemoryDatabaseType \| str, ...)`；`memory_db_type` 取值为字符串字面量 `InMemory` / `SQLite` / `AzureSQL` | S7 | 方法签名与参数表原文 |
| V9 | 评分器 `SubStringScorer`、`SelfAskTrueFalseScorer`、`TrueFalseQuestion`、`SelfAskRefusalScorer`、`SelfAskLikertScorer` 均在 `pyrit.score` | S8 | 原始 HTML 计数 3 / 12 / 31 / 6 / 8 次 |
| V10 | 目标 `OpenAIChatTarget`、`HTTPTarget`、`get_http_target_json_response_callback_function` 均在 `pyrit.prompt_target` | S9 | 原始 HTML 计数 14 / 16 / 6 次 |
| V11 | 间接注入由 `pyrit.executor.workflow` 的 `XPIATestWorkflow` / `XPIAWorkflow` 承担，非攻击策略 | S4 | `XPIA` 命中 94 次；类清单含 `XPIAContext` / `XPIAWorkflow` / `XPIATestWorkflow` / `XPIAResult` / `XPIAStatus` |
| V12 | `XPIATestWorkflow(attack_setup_target=..., processing_target=..., scorer=..., converter_config=..., prompt_normalizer=..., logger=...)`；`XPIAWorkflow.execute_async(attack_content=..., processing_callback=..., processing_prompt=..., memory_labels=...)` | S4 | 构造参数表与 `execute_async` 参数表原文 |
| V13 | 结果打印机为 `PrettyAttackResultMemoryPrinter`，位于 `pyrit.output.attack_result.pretty`，方法 `write_async(result)` | S1 | 官方首页示例代码，`pyrit.output.attack_result.pretty` 命中 2 次 |
| V14 | `pyrit.executor.attack` 中无 MCP 专用攻击策略（MCP / ToolAttack / MCPAttack 均 0 次命中） | S3 | 关键词计数 |

## 3. 已排除结论（推翻上游文档）

以下三项来自 `docs/research/pyrit-canonical-references.md` §3 与 §4、调研文档骨架代码、issue #83 规格 v1，**经一手源核实为不成立**，须从对象图与规格中移除。

| 编号 | 上游错误结论 | 核实结果 | 一手来源 | 替代对象 |
|---|---|---|---|---|
| X1 | `XpiaAttack` 位于 `pyrit.executor.attack`，用于间接注入 | `pyrit.executor.attack` 原始 HTML 中 `xpia` 计数 **0**；该模块 39 个类中无此类 | S3 | `pyrit.executor.workflow.XPIATestWorkflow`（见 V11、V12） |
| X2 | `ConsoleAttackResultPrinter().print_conversation_async()` 用于对话导出 | 官方首页与 `pyrit.output` 均无此名；`ConsoleAttackResultPrinter` 计数 **0** | S1、S2 | `PrettyAttackResultMemoryPrinter.write_async(result)`（见 V13） |
| X3 | `AttackExecutor.execute_single_turn_attacks_async` 可用 | `pyrit.executor.attack` 原始 HTML 计数 **0** | S3 | 统一使用 `execute_attack_async`（见 V4） |
| X4 | `AzureOpenAIChatTarget` 可用（0.x 名称） | `pyrit.prompt_target` 原始 HTML 计数 **0** | S9 | `OpenAIChatTarget`（见 V10） |

**受控例外声明（B7）**：主线 B7 要求对象图统一采用 `pyrit.executor.attack` 下的 `*Attack`。间接注入路径（ASI01 间接注入）在 v1.1.0 中**只能**由 `pyrit.executor.workflow` 的工作流策略表达，该模块不属于 `pyrit.executor.attack`。此为例外，不改变其余路径的策略归属，也不引入任何 0.x 禁用名称。例外依据为 V11、V12、X1，须在规格 v2 与设计记录中显式标注。

## 4. 待核实项与取证方式（实现前核实闸）

| 编号 | 待核实项 | 当前状态 | 取证方式 | 阻塞对象 |
|---|---|---|---|---|
| P1 | `pyrit.setup` 是否导出 `IN_MEMORY` / `SQLITE` 常量 | 文档首页示例使用 `IN_MEMORY`（S1），但 `pyrit.setup` API 页 `IN_MEMORY` 计数 0（S7） | 实现前在已安装 `pyrit==1.1.0` 的环境执行 `from pyrit.setup import IN_MEMORY`，或直接采用 `memory_db_type="SQLite"` 字符串字面量（V8 已核实） | 路径 A 初始化写法；**不阻塞**，已有已核实替代 |
| P2 | `XPIATestWorkflow` 的 `processing_callback` 与 `attack_content` 具体取值形态 | 参数名已核实（V12），类型 `Message` / `ProcessingCallback` 未在参数表展开 | 实现前查 S4 的 `XPIAProcessingCallback` 定义与官方 Workflows 示例 | 路径 A 间接注入实现；采用注入点隔离，不阻塞其余路径 |
| P3 | `SelfAskTrueFalseScorer` 与 `TrueFalseQuestion` 的构造参数精确类型 | 类名已核实（V9），构造签名未在本轮提取 | 实现前查 S8 对应类条目 | 评分器装配；采用注入点隔离，不阻塞其余路径 |
| P4 | `SQLiteMemory` 文件型持久化位置（`db_path`）与跨会话复用 | 类与 `db_path` 参数已核实（V7、S6） | 实现前查 `CentralMemory.set_memory_instance` 与 `pyrit.setup` 的 `memory_instance_kwargs` | 路径 B 跨会话验证；采用注入点隔离，不阻塞其余路径 |

四项均**已给出官方源与取证方式**，符合 §3.1 验收标准 ④；按 §3.3 验收标准 ③，可在规格 v2 中作为「带取证方式的核实闸」保留，不构成阶段 3 的阻塞项。

## 5. 与 `SKILL.md` 三条攻击路径的对象映射（修正后）

| 攻击路径 | 策略 | 目标 | 转换器 | 评分器 | 记忆 |
|---|---|---|---|---|---|
| A 直接注入（ASI01） | `PromptSendingAttack` | `OpenAIChatTarget` | `AttackConverterConfig` + `Base64Converter` / `TranslationConverter` | `SelfAskTrueFalseScorer` + `SubStringScorer` | `memory_db_type="InMemory"` |
| A 间接注入（ASI01） | `XPIATestWorkflow`（B7 受控例外） | `attack_setup_target` / `processing_target` | `converter_config` | `scorer` | `memory_labels` |
| B 记忆滥用（ASI06） | `RedTeamingAttack` 投毒 + 新会话 `PromptSendingAttack` 召回 | `OpenAIChatTarget`（被测 + 攻击方） | `AttackConverterConfig` | `SelfAskTrueFalseScorer` + `SubStringScorer` | `SQLiteMemory` 文件型（`memory_db_type="SQLite"`），**不可** `InMemory` |
| C 工具滥用（ASI02） | `RedTeamingAttack` / `PromptSendingAttack` | `HTTPTarget` + 回调（V10） | `AttackConverterConfig` | `SubStringScorer` 为主 | `memory_labels` |

统一执行器为 `AttackExecutor().execute_attack_async`（V4）；结果导出使用 `PrettyAttackResultMemoryPrinter.write_async`（V13）。三条路径均有对应对象映射，符合 §3.1 验收标准 ③。

## 6. 对上游交付物的修正要求

| 编号 | 文件 / 位置 | 动作 | 复验命令 |
|---|---|---|---|
| F1 | `docs/research/pyrit-canonical-references.md` §3、§4 | 删除 `XpiaAttack` 与 `execute_single_turn_attacks_async`；补入 `XPIATestWorkflow` 归属 `pyrit.executor.workflow`、`PrettyAttackResultMemoryPrinter`、`MemoryDatabaseType` 取值；关闭已核实项 | `grep -n "XpiaAttack\|execute_single_turn" docs/research/pyrit-canonical-references.md` |
| F2 | `docs/research/pyrit-native-api-attack-ai-agent.md` §3、§4、§6 | 修正路径 A 间接注入映射、骨架代码导入与结果打印器；关闭 `[需核实]` 中已核实项 | `grep -n "XpiaAttack\|ConsoleAttackResultPrinter" docs/research/pyrit-native-api-attack-ai-agent.md` |
| F3 | issue #83 规格 v1 的 Solution 与 Implementation Decisions | 在阶段 2 / 阶段 3 修订 `XpiaAttack` → `XPIATestWorkflow`，并标注 B7 受控例外 | `gh issue view 83 --json body` |

## 7. 门禁记录（阶段 1 · G0）

**交付物清单**：本文件；`pyrit-canonical-references.md`（F1 修正）；`pyrit-native-api-attack-ai-agent.md`（F2 修正）；issue #83 阶段 1 摘要评论。

**初轮结论**：`BLOCKED`。不符合项 2 项——(a) B7：上游权威索引把 `XpiaAttack` 归入 `pyrit.executor.attack`，与一手源 V11/X1 冲突；(b) B8：上游调研文档含 `ConsoleAttackResultPrinter`、`execute_single_turn_attacks_async` 两个无法回溯到一手源的 API 名。按 §2.2 第 4 步执行 F1、F2 修正后重跑全部检查项。

| 编号 | 检查项 | 依据 | 实测结果（命令 + 输出摘要） | 判定 | 不符合项描述 | 修正要求（文件 + 位置 + 动作 + 复验命令） | 复验结果 | 结论 |
|---|---|---|---|---|---|---|---|---|
| G1-01 | 每条结论有一手来源 | §3.1-① / B8 | 13 条已核实 + 4 条已排除 + 4 条待核实，均标注 S1–S10 URL | 符合 | 无 | 无 | 符合 | PASS |
| G1-02 | 版本号明确 | §3.1-② / B7 | 全文锁定 `pyrit==1.1.0`（S1 路径 `/1.1.0/`） | 符合 | 无 | 无 | 符合 | PASS |
| G1-03 | 三条攻击路径均有对象映射 | §3.1-③ | §5 表覆盖 A 直接 / A 间接 / B / C 四行 | 符合 | 无 | 无 | 符合 | PASS |
| G1-04 | 待核实项逐条命名并给出取证方式 | §3.1-④ | §4 表 P1–P4 各含状态、取证方式、阻塞对象 | 符合 | 无 | 无 | 符合 | PASS |
| G1-05 | 文档落盘于 `docs/research/` | §3.1-⑤ | `ls docs/research/` 含本文件 | 符合 | 无 | 无 | 符合 | PASS |
| G1-06 | 对象图无 0.x 禁用名称 | B7 | 权威索引与调研文档修正后，禁用名称仅出现在「已删除」否定语境 | 符合 | 初轮：`XpiaAttack` 归属错误；`AzureOpenAIChatTarget` 在调研对照列属历史对照 | F1 / F2：见 §6，复验 `grep -n "XpiaAttack" docs/research/` | 修正后仅否定语境 | PASS |
| G1-07 | B7 受控例外已显式标注 | B7 / §2 | §3「受控例外声明」给出依据 V11、V12、X1 | 符合 | 初轮：无例外声明 | 本文件 §3 写入声明 | 已写入 | PASS |
| G1-08 | G0 表字段齐全（9 列） | §2.2 第 3 步 | 本表 9 列：编号 / 检查项 / 依据 / 实测结果 / 判定 / 不符合项描述 / 修正要求 / 复验结果 / 结论 | 符合 | 无 | 无 | 符合 | PASS |
| G1-09 | 门禁记录写入交付物并在 issue 留摘要 | §2.2 第 5 步 / B8 | 本节写入本文件；issue #83 阶段 1 摘要评论已发布 | 符合 | 无 | 无 | 符合 | PASS |
| G1-10 | 上游交付物未被破坏 | §2.3 | `python scripts/validate_skill.py`、`python scripts/check_glossary.py` 复跑 | 符合 | 无 | 修正后复跑输出见下方 | 全绿 | PASS |

**复跑输出摘要**：`validate_skill.py` → `PASS：共校验 16 个技能，全部合规。`；`check_glossary.py` → `PASS：术语一致性校验通过（检查 4 个废弃术语）。`

**复验后结论**：`PASS`。初轮 2 项不符合项已按 F1、F2 修正并复验通过，阶段 1 可交付阶段 2。

## 8. 学习要点

阶段 1 位于工程链起点，其存在理由是消除规格与实现阶段的猜测。本轮实证表明：仓库内既有「权威索引」若未逐条回溯一手源，会把不成立的 API 名传导进规格（issue #83 v1 的 `XpiaAttack`）与骨架代码。观察「事实 → 规格」的传导链，可看到一条未经核实的名称会同时污染规格、工单与实现三个阶段。
