# PyRIT 变更版本归属核实记录（issue #252）

> **核实日期**：2026-11-28 · **方法**：GitHub API releases/tags/git-trees + raw 源码 + PyPI JSON，全部一手源，逐条附 URL。
> **性质**：事实核实记录（非规格 / 非门禁）。引用本文件用 `路径#锚点`，不复述正文（AGENTS.md C1）。
> **范围**：只判定 A/B/C 三组主张的版本归属；v1.1.0 API 细节见 `docs/research/pyrit-v110-api-verification.md`，不重复。

## A. orchestrator 删除 / AzureOpenAIChatTarget 并入 —— 已证实「v1.0.0 及更早」，确切版本更早

### A1. orchestrator → executor.attack：确切版本 v0.10.0（2025-12-15 发布）

| 证据 | 来源 |
|---|---|
| v0.9.0 树有 `pyrit/orchestrator/`（23 个文件）、无 `pyrit/executor/` | <https://api.github.com/repos/microsoft/PyRIT/git/trees/v0.9.0?recursive=1> |
| v0.10.0 树 `pyrit/orchestrator` 为 0、`pyrit/executor/attack/` 存在（含 `core/attack_executor.py` 等） | <https://api.github.com/repos/microsoft/PyRIT/git/trees/v0.10.0?recursive=1> |
| v0.10.0 release notes「Orchestrators --> Executors」节明言 "In v0.10.0, we standardized the interface"，给出 `pyrit.executor.attack` 映射（`PromptSendingOrchestrator`→`PromptSendingAttack` 等）；PR #945、#1085「[BREAKING] Remove last references to orchestrators」 | <https://api.github.com/repos/microsoft/PyRIT/releases/tags/v0.10.0> |
| v0.14.0 / v1.0.0 / v1.1.0 三棵树均无 orchestrator、均有 `pyrit/executor/attack/`（truncated=false，全量） | <https://api.github.com/repos/microsoft/PyRIT/git/trees/v0.14.0?recursive=1> · <https://api.github.com/repos/microsoft/PyRIT/git/trees/v1.0.0?recursive=1> · <https://api.github.com/repos/microsoft/PyRIT/git/trees/v1.1.0?recursive=1> |

### A2. AzureOpenAIChatTarget 并入 OpenAIChatTarget：两步完成，均远早于 v1.0.0

| 阶段 | 确切版本 | 证据与来源 |
|---|---|---|
| 独立文件 `pyrit/prompt_target/azure_openai_chat_target.py` 存在 | v0.1.0–v0.1.1 | 树：<https://api.github.com/repos/microsoft/PyRIT/git/trees/v0.1.1?recursive=1> |
| 文件删除、类并入 `openai_chat_target.py`（类仍在） | v0.1.2 | 树：<https://api.github.com/repos/microsoft/PyRIT/git/trees/v0.1.2?recursive=1>；raw 该文件含 `class AzureOpenAIChatTarget(OpenAIChatInterface)`：<https://raw.githubusercontent.com/microsoft/PyRIT/v0.1.2/pyrit/prompt_target/openai_chat_target.py> |
| 类名 `AzureOpenAIChatTarget` 消失，更名 `AzureOpenAITextChatTarget` | v0.4.0（2024-08-23） | v0.3.0 raw 仍有该类、v0.4.0 raw 只有 `AzureOpenAITextChatTarget`：<https://raw.githubusercontent.com/microsoft/PyRIT/v0.3.0/pyrit/prompt_target/prompt_chat_target/openai_chat_target.py> · <https://raw.githubusercontent.com/microsoft/PyRIT/v0.4.0/pyrit/prompt_target/prompt_chat_target/openai_chat_target.py>；v0.4.0 `__init__` 导出 `AzureOpenAITextChatTarget`、无 `AzureOpenAIChatTarget`：<https://raw.githubusercontent.com/microsoft/PyRIT/v0.4.0/pyrit/prompt_target/__init__.py> |
| Azure 专用 chat target 全部并入 `OpenAIChatTarget`（`is_azure_target` 开关） | v0.5.0（2024-11-27） | release notes："Open AI and Azure Open AI targets were refactored… share a common interface `OpenAITarget`… `is_azure_target=True` or `False`"（PR #466）：<https://api.github.com/repos/microsoft/PyRIT/releases/tags/v0.5.0>；v0.5.0 `__init__` 无任何 AzureOpenAI 导出：<https://raw.githubusercontent.com/microsoft/PyRIT/v0.5.0/pyrit/prompt_target/__init__.py> |

**A 结论（已证实）**：两项变更均属「v1.0.0 及更早」，非 v1.1.0。确切版本：orchestrator→executor.attack = **v0.10.0**；AzureOpenAIChatTarget 类名退役 = **v0.4.0**，功能并入 OpenAIChatTarget = **v0.5.0**。v0.10.0 另有 openai SDK 化参数破坏（#1194/#1235），属后续强化而非并入本身。

## B. v1.1.0 真实破坏变更 —— 已证实（release notes 原文，2026-09-04 发布）

来源：<https://api.github.com/repos/microsoft/PyRIT/releases/tags/v1.1.0>（「⚠️ Breaking changes」节）；PyPI 1.1.0 存在（wheel/sdist 上传 2026-09-04，`requires_python >=3.10,<3.15`）：<https://pypi.org/pypi/pyrit/1.1.0/json>。

1. **`score.is_undetermined`**：读 `score_value` / `get_value()` 前须检查（PR #2491，score model phase 2）。
2. **`should_score_blocked_content`**：部分被拦截响应默认计分；设 `False` 保留旧行为。
3. **CoPyRIT 认证**：改用 Microsoft Graph，需 allowed group 配置（PR #2281）。
4. （补充，同节原文）fixed-egress CoPyRIT 部署需并行 Azure Container Apps 环境；Azure SQL 部署需新 migrations（PR #2438）。

**B 结论（已证实）**：三项主张全部逐字命中 v1.1.0 release notes；v1.1.0 破坏变更中**不含** orchestrator / AzureOpenAIChatTarget 任何字样。

## C. 旧名在 v1.1.0 无法 import —— 已证实（静态源码级）

| 旧名 | v1.1.0 证据 | 来源 |
|---|---|---|
| `pyrit.orchestrator.*`（如 `PromptSendingOrchestrator`） | 全树 3231 条路径（truncated=false）中含 "orchestrator" 的路径为 0 → 模块不存在，import 必 `ModuleNotFoundError` | <https://api.github.com/repos/microsoft/PyRIT/git/trees/v1.1.0?recursive=1> |
| `AzureOpenAIChatTarget` | `pyrit/prompt_target/__init__.py` 与 `pyrit/__init__.py` 均无 AzureOpenAI / orchestrator / legacy / alias / compat 字样；`openai_chat_target.py` 0 次提及 → 无兼容别名，import 必 `ImportError` | <https://raw.githubusercontent.com/microsoft/PyRIT/v1.1.0/pyrit/prompt_target/__init__.py> · <https://raw.githubusercontent.com/microsoft/PyRIT/v1.1.0/pyrit/__init__.py> · <https://raw.githubusercontent.com/microsoft/PyRIT/v1.1.0/pyrit/prompt_target/openai/openai_chat_target.py> |
| 兼容 shim 已先行清除 | v1.0.0 notes「Pre-v1 compatibility paths are gone」（#1951/#2111/#2195），故 v1.1.0 亦无 deprecated 别名可走 | <https://api.github.com/repos/microsoft/PyRIT/releases/tags/v1.0.0> |

**C 结论（已证实，限定静态）**：树 + 导出源码证明旧名在 v1.1.0 无模块、无别名；未做 `pip install pyrit==1.1.0` 运行时 import 实测（依赖重，静态证据已充分）。

## 未证实 / 反证清单

- **未证实**：无。A/B/C 全部主张均获一手源支持。
- **反证（对「属 v1.1.0」的误归属）**：v1.1.0 release notes 破坏变更节与全量 PR 清单均无 orchestrator 删除 / AzureOpenAIChatTarget 并入条目；v0.14.0（早于 v1.0.0）树已无 orchestrator。来源同 A1/B。
- **精度修正**：主张 A 的「v1.0.0 及更早」成立但偏宽——确切版本为 v0.10.0（orchestrator）与 v0.4.0/v0.5.0（Azure 并入），引用时应写确切版本。
