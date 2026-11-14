# 锁定 PyRIT 于 v1.1.0，禁止 0.x API

本仓库以 PyRIT 作为 AI 红队攻击的实现框架。PyRIT 在 **v1.1.0（2026-09-04）** 做了破坏性重构：删除 `pyrit.orchestrator`，原 `*Orchestrator` 类更名为 `pyrit.executor.attack` 下的 `*Attack`；`AzureOpenAIChatTarget` 合并为单一 `OpenAIChatTarget`。我们决定**锁定 `pyrit==1.1.0`**，并在规格、实现与评审中禁止使用任何 0.x 旧 API（详见 `docs/research/pyrit-canonical-references.md`）。

**Considered Options:**
- 跟随最新 PyRIT（>1.1.0）：可获新特性，但 API 仍在演进、文档存在漂移，攻击实现需持续追版本。
- 使用 0.x 旧版：旧教程较多，但 `pyrit.orchestrator` / `*Orchestrator` / `AzureOpenAIChatTarget` 在现行版本已无法 `import`，套用即失败。
- 锁定 v1.1.0（选定）：API 稳定、官方 1.1.0 文档完整（`microsoft.github.io/PyRIT/1.1.0/`），足以覆盖 OWASP LLM 三类攻击路径（ASI01 提示注入 / ASI06 记忆滥用 / ASI02 工具集成滥用）。

**Consequences:**
- 所有 PyRIT 代码以 `pyrit==1.1.0` 为唯一基准，实现前以官方 1.1.0 文档取证（四项待核实项见 issue #83 的 VG-1..4 核实闸）。
- 后续若升级 PyRIT 主版本，须显式重开本 ADR 并复测全部攻击路径对象图装配。
- 仓库 CI 在 S2 测试层以可注入假后端替代真实 PyRIT 对象，保持零外部依赖（与 ADR-0003 一致）。
