# PyRIT 权威引用索引（可复用单一可信源）

> **用途**：本文件是后续所有 PyRIT 相关 `research` / `to-spec` / `implement` 阶段的**单一可信源**。
> 任何涉及 PyRIT 版本、仓库、文档、API 命名空间的判断，**先读本文件**，再决定是否需要向官方源取证。
> 不要依赖对话记忆或 0.x 旧教程——PyRIT 在 1.1.0 做了破坏性重构。

## 1. 版本锁定（必读）

- **固定版本**：`pyrit==1.1.0`（2026-09-04 发布）
- **安装**：`pip install pyrit==1.1.0`
- **严禁**：套用 0.x 旧教程。以下旧名在 1.1.0 已**无法 import**：`pyrit.orchestrator`、`*Orchestrator`（如 `PromptSendingOrchestrator`）、`AzureOpenAIChatTarget`。

## 2. 官方源（一级，取证优先）

| 用途 | URL |
|---|---|
| 官方仓库 | https://github.com/microsoft/PyRIT （原 `Azure/PyRIT` 已归档，仅作 provenance） |
| 文档（v1.1.0） | https://microsoft.github.io/PyRIT/1.1.0/ |
| 历史归档 | https://github.com/Azure/PyRIT （只读，确认出处用） |

## 3. v1.1.0 破坏性重构要点（影响所有实现）

> **一手源核实**：以下内容已于 2026-11-14 逐条对照官方文档 v1.1.0 API Reference，详见 `pyrit-v110-api-verification.md`。经核实被推翻的旧结论已移除。

- 删除 `pyrit.orchestrator`；编排器更名为 `pyrit.executor.attack` 下的**攻击策略**（`*Attack`）：
  `PromptSendingAttack`、`RedTeamingAttack`、`CrescendoAttack`、`PAIRAttack`、`TreeOfAttacksWithPruningAttack` 等。
  **注意**：`XpiaAttack` 不存在于 v1.1.0；间接注入（XPIA）由 `pyrit.executor.workflow` 的 `XPIATestWorkflow` / `XPIAWorkflow` 承担。
- `AzureOpenAIChatTarget` 与 `OpenAIChatTarget` 合并为单一 `OpenAIChatTarget`（`pyrit.prompt_target`）；`HTTPTarget` 与 `get_http_target_json_response_callback_function` 同模块。
- 执行器：`AttackExecutor(max_concurrency=1)`，批量方法为 `execute_attack_async(attack=..., objectives=...)`。**无** `execute_single_turn_attacks_async`。
- 配置对象（均位于 `pyrit.executor.attack`）：`AttackConverterConfig`、`AttackAdversarialConfig`、`AttackScoringConfig`、`RTASystemPromptPaths`。
- 转换器：`pyrit.converter`，已核实子类 `Base64Converter`、`LeetspeakConverter`、`TranslationConverter`、`ROT13Converter`。
- 评分器：`pyrit.score`（`SelfAskTrueFalseScorer` + `TrueFalseQuestion`、`SelfAskLikertScorer`、`SelfAskRefusalScorer`、`SubStringScorer` 等）。
- 记忆：`pyrit.memory`，后端类 `SQLiteMemory`（支持文件型与内存型）、`AzureSQLMemory`，接口 `MemoryInterface`，单例 `CentralMemory`。
- 初始化：`initialize_pyrit_async(memory_db_type=...)`；`memory_db_type` 取值 `InMemory` / `SQLite` / `AzureSQL`（`MemoryDatabaseType` 字符串字面量）。
- 结果导出：`PrettyAttackResultMemoryPrinter`（`pyrit.output.attack_result.pretty`），方法 `write_async(result)`。**无** `ConsoleAttackResultPrinter`。
- 工具面 / MCP：v1.1.0 `pyrit.executor.attack` 无专用攻击策略，以 `HTTPTarget` + 回调对接，并标注与 `attack-mcp-tool`（D7）的衔接点。

## 4. 核实闸状态（2026-11-14 一手源取证后）

已关闭（原 `[需核实]` 项）：converter 子类名、`pyrit.memory` 后端类、`XPIA` 归属、结果打印机、`memory_db_type` 取值、MCP 专用策略。

仍为**带取证方式的核实闸**（实现前在已安装 `pyrit==1.1.0` 的环境确认，不阻塞其余路径）：

1. `pyrit.setup` 是否导出 `IN_MEMORY` / `SQLITE` 常量（官方首页示例用 `IN_MEMORY`，API 页未列）；已核实替代：`memory_db_type="SQLite"` 字符串字面量。
2. `XPIATestWorkflow` 的 `processing_callback` 与 `attack_content` 具体类型形态（参数名已核实）。
3. `SelfAskTrueFalseScorer` / `TrueFalseQuestion` 构造参数精确类型（类名已核实）。
4. `SQLiteMemory` 的 `db_path` 与 `CentralMemory.set_memory_instance` 跨会话复用细节（类名与 `db_path` 参数已核实）。

## 5. 关联文档

- 完整调研（含骨架代码、评分设计、开放项）：`docs/research/pyrit-native-api-attack-ai-agent.md`
- 工作流映射（SKILL.md 概念 → PyRIT 对象表）：`docs/operations/pyrit-implementation-workflow.md` §2
- 治理规范：`GOVERNANCE.md` §4.2（五要素）/ §6（质量基线）
- 术语基准：`GLOSSARY.md`
