# 锁定 PyRIT 于 v1.1.0，禁止 0.x API

本仓库以 PyRIT 作为 AI 红队攻击的实现框架。PyRIT 在 **v1.1.0（2026-09-04）** 做了破坏性重构：删除 `pyrit.orchestrator`，原 `*Orchestrator` 类更名为 `pyrit.executor.attack` 下的 `*Attack`；`AzureOpenAIChatTarget` 合并为单一 `OpenAIChatTarget`。我们决定**锁定 `pyrit==1.1.0`**，并在规格、实现与评审中禁止使用任何 0.x 旧 API（详见 `docs/research/pyrit-canonical-references.md`）。

**Considered Options:**
- 跟随最新 PyRIT（>1.1.0）：可获新特性，但 API 仍在演进、文档存在漂移，攻击实现需持续追版本。
- 使用 0.x 旧版：旧教程较多，但 `pyrit.orchestrator` / `*Orchestrator` / `AzureOpenAIChatTarget` 在现行版本已无法 `import`，套用即失败。
- 锁定 v1.1.0（选定）：API 稳定、官方 1.1.0 文档完整（`microsoft.github.io/PyRIT/1.1.0/`），足以覆盖 OWASP LLM 三类攻击路径（ASI01 提示注入 / ASI06 记忆滥用 / ASI02 工具集成滥用）。

**一手源核实（2026-11-14 补记）**：本 ADR 签署后，阶段 1 对官方 v1.1.0 API Reference 逐条取证，记录见 `docs/research/pyrit-v110-api-verification.md`。结论修正三项：① `XpiaAttack` 在 v1.1.0 **不存在**，间接注入由 `pyrit.executor.workflow.XPIATestWorkflow` 承担（B7 受控例外）；② 结果导出为 `PrettyAttackResultMemoryPrinter`，无 `ConsoleAttackResultPrinter`；③ `AttackExecutor` 无 `execute_single_turn_attacks_async`。VG-1 / VG-2 / VG-3 / VG-4 中 converter 子类名、memory 后端类、XPIA 归属、结果导出类均已核实关闭；剩余 P1–P4 为带取证方式的核实闸。

**Consequences:**
- 所有 PyRIT 代码以 `pyrit==1.1.0` 为唯一基准；一手源核实记录为版本与 API 命名空间的单一可信源，取代 issue #83 中的 VG-1..4 旧取证项。
- 间接注入使用 `pyrit.executor.workflow` 工作流，属 B7 受控例外，须在规格、设计与代码中显式标注；其余路径仍统一用 `pyrit.executor.attack` 的 `*Attack`。
- 后续若升级 PyRIT 主版本，须显式重开本 ADR 并复测全部攻击路径对象图装配。
- 仓库 CI 在 S2 测试层以可注入假后端替代真实 PyRIT 对象，保持零外部依赖（与 ADR-0003 一致）。
