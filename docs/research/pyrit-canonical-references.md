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

- 删除 `pyrit.orchestrator`；编排器更名为 `pyrit.executor.attack` 下的**攻击策略**（`*Attack`）：
  `PromptSendingAttack`、`RedTeamingAttack`、`CrescendoAttack`、`XpiaAttack`、`PAIRAttack`、`TAPAttack`、`TreeOfAttacksWithPruningAttack`、`FuzzerAttack`。
- `AzureOpenAIChatTarget` 与 `OpenAIChatTarget` 合并为单一 `OpenAIChatTarget`（`pyrit.prompt_target`）。
- 执行器：`AttackExecutor`（`execute_attack_async` / `execute_single_turn_attacks_async`）。
- 配置对象（均位于 `pyrit.executor.attack`）：`AttackConverterConfig`、`AttackAdversarialConfig`、`AttackScoringConfig`。
- 转换器：`pyrit.converter`（可链式组合）。
- 评分器：`pyrit.score`（`SelfAskTrueFalseScorer`、`SelfAskLikertScorer`、`SelfAskRefusalScorer`、`SubStringScorer`、`AzureContentFilterScorer`、`InsecureCodeScorer`）。
- 记忆：`pyrit.memory`（SQLite 默认，可换 Postgres/Azure SQL 后端）。
- 初始化：`from pyrit.setup import IN_MEMORY, initialize_pyrit_async`；`await initialize_pyrit_async(memory_db_type=IN_MEMORY)`。

## 4. 待核实项（每次 research 若涉及，优先向官方 1.1.0 文档确认）

1. `pyrit.converter` 在 1.1 的具体子类名（ROT13 / Base64 / Translation 等是否沿用）。
2. `pyrit.memory` 后端抽象与类名（SQLite / Postgres / Azure SQL 后端类）。
3. `XpiaAttack` 的精确导入路径与入参（间接注入的关键策略）。
4. 工具面 / MCP（`attack-mcp-tool` / D7）在 1.1 核心是否提供专用攻击策略；若无，以 `HTTPTarget` + 自定义 target 对接，并标注与 backlog 中 `attack-mcp-tool` 的衔接点。

## 5. 关联文档

- 完整调研（含骨架代码、评分设计、开放项）：`docs/research/pyrit-native-api-attack-ai-agent.md`
- 工作流映射（SKILL.md 概念 → PyRIT 对象表）：`docs/operations/pyrit-implementation-workflow.md` §2
- 治理规范：`GOVERNANCE.md` §4.2（五要素）/ §6（质量基线）
- 术语基准：`GLOSSARY.md`
