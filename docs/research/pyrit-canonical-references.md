# PyRIT 权威引用索引（可复用单一可信源）

> **用途**：本文件是后续所有 PyRIT 相关 `research` / `to-spec` / `implement` 阶段的**单一可信源**。
> 任何涉及 PyRIT 版本、仓库、文档、API 命名空间的判断，**先读本文件**，再决定是否需要向官方源取证。
> 不要依赖对话记忆或 0.x 旧教程。**版本归属**：orchestrator→`executor.attack` 架构重构属 **v0.10.0**、`AzureOpenAIChatTarget` 并入属 **v0.4.0/v0.5.0**（均早于 v1.0.0）；v1.1.0 的破坏性变更在评分/部署面（见 §3）。

## 1. 版本锁定（必读）

- **固定版本**：`pyrit==1.1.0`（2026-09-04 发布）
- **安装**：`pip install pyrit==1.1.0`
- **严禁**：套用 0.x 旧教程。以下旧名在 1.1.0 已**无法 import**（经 v1.1.0 源码树+导出复核成立）：`pyrit.orchestrator`、`*Orchestrator`（如 `PromptSendingOrchestrator`）、`AzureOpenAIChatTarget`。**版本归属订正（#252）**：删除/更名发生在更早版本——orchestrator→`executor.attack` 于 **v0.10.0**；`AzureOpenAIChatTarget` 类名 **v0.4.0** 退役、功能 **v0.5.0** 并入 `OpenAIChatTarget`——非 v1.1.0 的变更，v1.1.0 仅延续其缺失。取证：`pyrit-version-attribution-252.md`。

## 2. 官方源（一级，取证优先）

| 用途 | URL |
|---|---|
| 官方仓库 | https://github.com/microsoft/PyRIT （原 `Azure/PyRIT` 已归档，仅作 provenance） |
| 文档（v1.1.0） | https://microsoft.github.io/PyRIT/1.1.0/ |
| 历史归档 | https://github.com/Azure/PyRIT （只读，确认出处用） |

## 3. v1.1.0 API 命名空间要点（架构变更版本归属已订正）

> **一手源核实**：以下命名空间已于 2026-11-14 逐条对照官方文档 v1.1.0 API Reference，详见 `pyrit-v110-api-verification.md`。经核实被推翻的旧结论已移除。
> **版本归属订正（#252，2026-11-28）**：下列为 v1.1.0 API **现状**（事实不变）；orchestrator 删除/更名属 v0.10.0、Azure 并入属 v0.4.0/v0.5.0，**非 v1.1.0 破坏性变更**。v1.1.0 真实破坏变更见本节末「评分/部署面」条。取证：`pyrit-version-attribution-252.md`。

- `pyrit.orchestrator` 已删除、编排器更名为 `pyrit.executor.attack` 下的**攻击策略**（`*Attack`）【架构变更属 **v0.10.0**，非 v1.1.0】：
  `PromptSendingAttack`、`RedTeamingAttack`、`CrescendoAttack`、`PAIRAttack`、`TreeOfAttacksWithPruningAttack` 等。
  **注意**：`XpiaAttack` 不存在于 v1.1.0；间接注入（XPIA）由 `pyrit.executor.workflow` 的 `XPIATestWorkflow` / `XPIAWorkflow` 承担。
- `AzureOpenAIChatTarget` 已并入单一 `OpenAIChatTarget`（`pyrit.prompt_target`）【类名 **v0.4.0** 退役、功能 **v0.5.0** 并入，非 v1.1.0】；`HTTPTarget` 与 `get_http_target_json_response_callback_function` 同模块。
- 执行器：`AttackExecutor(max_concurrency=1)`，批量方法为 `execute_attack_async(attack=..., objectives=...)`。**无** `execute_single_turn_attacks_async`。
- 配置对象（均位于 `pyrit.executor.attack`）：`AttackConverterConfig`、`AttackAdversarialConfig`、`AttackScoringConfig`、`RTASystemPromptPaths`。
- 转换器：`pyrit.converter`，已核实子类 `Base64Converter`、`LeetspeakConverter`、`TranslationConverter`、`ROT13Converter`。
- 评分器：`pyrit.score`（`SelfAskTrueFalseScorer` + `TrueFalseQuestion`、`SelfAskLikertScorer`、`SelfAskRefusalScorer`、`SubStringScorer` 等）。
- 记忆：`pyrit.memory`，后端类 `SQLiteMemory`（支持文件型与内存型）、`AzureSQLMemory`，接口 `MemoryInterface`，单例 `CentralMemory`。
- 初始化：`initialize_pyrit_async(memory_db_type=...)`；`memory_db_type` 取值 `InMemory` / `SQLite` / `AzureSQL`（`MemoryDatabaseType` 字符串字面量）。
- 结果导出：`PrettyAttackResultMemoryPrinter`（`pyrit.output.attack_result.pretty`），方法 `write_async(result)`。**无** `ConsoleAttackResultPrinter`。
- 工具面 / MCP：v1.1.0 `pyrit.executor.attack` 无专用攻击策略，以 `HTTPTarget` + 回调对接，并标注与 `attack-mcp-tool`（D7）的衔接点。
- **v1.1.0 真实破坏性变更（评分/部署面，release notes 原文逐字核实）**：① 读 `score_value` / `get_value()` 前须查 `score.is_undetermined`（#2491）；② 部分被拦截响应默认计分，设 `should_score_blocked_content=False` 保留旧行为；③ CoPyRIT 认证改用 Microsoft Graph + allowed group（#2281）；④ fixed-egress CoPyRIT 需并行 Azure Container Apps、Azure SQL 需新 migrations（#2438）。来源：v1.1.0 release notes「⚠️ Breaking changes」。

## 4. 核实闸状态（2026-11-14 取证；2026-11-28 #252 版本归属订正）

已关闭（原 `[需核实]` 项）：converter 子类名、`pyrit.memory` 后端类、`XPIA` 归属、结果打印机、`memory_db_type` 取值、MCP 专用策略。

仍为**带取证方式的核实闸**（实现前在已安装 `pyrit==1.1.0` 的环境确认，不阻塞其余路径）：

1. `pyrit.setup` 是否导出 `IN_MEMORY` / `SQLITE` 常量（官方首页示例用 `IN_MEMORY`，API 页未列）；已核实替代：`memory_db_type="SQLite"` 字符串字面量。
2. `XPIATestWorkflow` 的 `processing_callback` 与 `attack_content` 具体类型形态（参数名已核实）。
3. `SelfAskTrueFalseScorer` / `TrueFalseQuestion` 构造参数精确类型（类名已核实）。
4. `SQLiteMemory` 的 `db_path` 与 `CentralMemory.set_memory_instance` 跨会话复用细节（类名与 `db_path` 参数已核实）。
5. **v1.1.0 评分破坏性变更**（#252 新增）：`score.is_undetermined` 判定路径、`should_score_blocked_content` 默认值与旧行为开关、CoPyRIT Graph 认证 allowed group 配置——实现前在已安装 `pyrit==1.1.0` 环境确认（release notes 已逐字核实，见 `pyrit-version-attribution-252.md` §B）。

**版本归属偏差收敛（#252）**：capstone-rehearse 登记的 G-F / VG-6（「删除 orchestrator 误记为 1.1.0」）已由本订正消除；确切版本 v0.10.0 / v0.4.0 / v0.5.0。该两闸状态更新属 capstone 主线（ADR-0006 技能边界），本工单不改其冻结规格。

## 5. 关联文档

- 版本归属核实记录（#252，确切版本 v0.10.0/v0.4.0/v0.5.0 + v1.1.0 评分破坏变更）：`docs/research/pyrit-version-attribution-252.md`
- 完整调研（含骨架代码、评分设计、开放项）：`docs/research/pyrit-native-api-attack-ai-agent.md`
- 工作流映射（SKILL.md 概念 → PyRIT 对象表）：`docs/operations/pyrit-implementation-workflow.md` §2
- 治理规范：`GOVERNANCE.md` §4.2（五要素）/ §6（质量基线）
- 术语基准：`GLOSSARY.md`
