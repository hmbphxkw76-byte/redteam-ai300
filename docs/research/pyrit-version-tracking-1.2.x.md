# PyRIT 1.1.0 → 1.2.x 版本事实核查（升级框架输入）

> **版本** v1.0 · **核实日期** 2026-11-24 · **性质** 一手源取证记录
> **用途** 为 `tools/pyrit_compat/` 的版本清单与兼容层提供事实基线；不改写 `pyrit-canonical-references.md`（其 1.1.0 归属偏差仍由 issue #252 跟踪）。
> **边界** 本机未安装 PyRIT 发行版（`importlib.util.find_spec("pyrit") is None`），运行时对象图未实例化；以下 1.2.x 结论均来自官方发布页与官方源码，不冒充本地实测。

## 1. 发布事实（一手源：PyPI JSON API）

| 版本 | 上传 UTC | wheel SHA-256 | 来源 |
|---|---|---|---|
| 1.1.0 | 2026-09-04T22:16:36Z | `84581036…ba20b0a` | https://pypi.org/pypi/pyrit/json |
| 1.2.0 | 2026-11-13T03:11:17Z | `fabee89a…719e8e4` | 同上 |
| 1.2.1 | 2026-11-16T22:55:21Z | `4e404c41…ce2806a` | 同上 |

`info.version = 1.2.1`，即采集时最新稳定版。完整哈希见 `tools/pyrit_compat/data/versions/<version>.json#release.hashes`，可用 `checker lock --version <v>` 即时生成 pip 锁。
GitHub 发布页：`https://github.com/microsoft/PyRIT/releases/tag/v1.2.0`（published 2026-11-13）、`…/v1.2.1`（published 2026-11-18T20:12:13Z）。

## 2. 1.2.0 破坏性变更（发布页明确列出）

1. Python 3.10 不再支持；要求 `>=3.11,<3.15`。
2. CoPyRIT backend/CLI/browser 必须同 commit 构建；不同 commit 即使包版本相同也会被拒。
3. 自定义 scenario 必须用当前参数/context API，且 `initialize_async()` 无参；数据集选择用显式 sources/fetch policies/limits，无限制用 `"all"` 而非 `None`。
4. backend scenario 读取改为仅异步。
5. 自定义 `MessageScorer` 子类把 `_score_piece_async(..., objective=...)` 改为 `_score_piece_with_expectation_async(..., expectation=...)`（#3312）。
6. Gandalf target/scorer 移除（#3467）。
7. 部分 API target 创建需管理员权限（#3247、#3173）；API 创建 HTTP target 上传改用服务端选定目录（#3172）。
8. Alembic 迁移影响持久化 scores/scenarios/conversations/target identities/observations/attack results，回滚需应用与数据库协同。

来源：https://github.com/microsoft/PyRIT/releases/tag/v1.2.0 。

## 3. 1.2.1 结论

发布页原文：`packaging-only patch release`、`No runtime behavior or public API changes were introduced`，仅修正 wheel 内 license/notice/provenance 文件（#4257）。
来源：https://github.com/microsoft/PyRIT/releases/tag/v1.2.1 。因此 1.2.0 的适配集合覆盖 1.2.1，无需第二套兼容分支。
文档站 `https://microsoft.github.io/PyRIT/1.2.1/` 返回 404（仅提供 1.2.0 首页），故 API 事实以 GitHub tag 源码为准。

## 4. 签名逐项比对（v1.1.0 / v1.2.0 / v1.2.1 tag 源码）

原始路径形如 `https://raw.githubusercontent.com/microsoft/PyRIT/v1.2.1/pyrit/<file>`；归一化参数名快照见 `tools/pyrit_compat/data/versions/<version>.json#signatures`。

| 符号 | 结论 | 对本仓库的影响 |
|---|---|---|
| `pyrit.setup.initialization.initialize_pyrit_async` | 三版本参数一致 | 无；发布页的「无参 initialize_async」属 scenario API，不是本函数（CHG-003 显式登记为非影响） |
| `AttackExecutor.__init__` / `execute_attack_async` | 一致 | 无 |
| `PromptSendingAttack.__init__` | `params_type` 默认值 `AttackParameters` → `PromptSendingAttackParameters`（1.2.0 起） | 显式改写，避免静默默认行为差异（CHG-002） |
| `HTTPTarget.__init__` | 新增 keyword-only `trace_config`（1.2.0 起）；`http_request` 始终必填 | 新增参数为加法兼容；1.1.0 调用需显式拒绝（CHG-001） |
| `OpenAIChatTarget.__init__` / `SubStringScorer.__init__` / `SelfAskTrueFalseScorer.from_question` / `XPIATestWorkflow.__init__` | 参数一致 | 无 |
| `SQLiteMemory.__init__` | 1.2.x 为 `*args/**kwargs` 包装器 | 标为 `passthrough-wrapper`，不误报参数移除 |
| `pyrit.models` 导出 | 三版本均有 `Message`/`MessagePiece`，无 `PromptRequestResponse`/`PromptRequestPiece` | 既有 `attack-rag` 调用属预存漂移（CHG-013） |
| `pyrit.common` 导出 | 三版本均不导出 `initialize_pyrit_async` | 既有 `attack-multi-agent` 调用属预存漂移（CHG-012） |
| `pyrit.score` 导出 | 三版本均导出 `ContentScorable`/`TrueFalseQuestion`/`SubStringScorer`/`SelfAskTrueFalseScorer` | 无 |

## 5. 调用点影响清单

AST 扫描 `tools/` + `scripts/` 共 20 个 PyRIT import 点；分类结果见 `docs/operations/pyrit-compat-call-sites.json`：映射 5 个、已核实未变 15 个、未分类 0 个。

| 调用点 | 变更 ID | 处置 |
|---|---|---|
| `tools/attack_ai_agent/backends.py:245` `HTTPTarget` | CHG-001、CHG-014 | `http_request` 形态本已正确；兼容层拒绝遗留 `http_target` |
| `tools/attack_ai_agent/backends.py:315` `PromptSendingAttack` | CHG-002、CHG-015 | 参数形态本已正确；默认值改写由兼容层显式告警 |
| `tools/attack_multi_agent/pyrit_attack.py:35` `PromptSendingAttack` | CHG-002、CHG-015 | 预存 `attack_target`/`scorer`/`memory` 改为 `objective_target` + executor + 独立评分 |
| `tools/attack_multi_agent/pyrit_attack.py:36` `HTTPTarget` | CHG-001、CHG-014 | 预存 `http_target=` 改为 `http_request=`（由 endpoint 构造原始请求） |
| `tools/attack_rag/backends.py:110` 消息模型 | CHG-013 | 预存 `PromptRequestResponse` 改为 `Message`/`MessagePiece` |

Gandalf、scenario 异步读、数据集选择、CoPyRIT artifact 匹配四类变更在本仓库无调用点，按「已核实非影响」登记，不伪造适配代码。

## 6. 运行时实测与诚实边界

- WorkBuddy 内置 Python 3.13.12 未安装 PyRIT；本机 `C:/Users/liude/AppData/Local/Programs/Python/Python313/python.exe` 已安装 `pyrit==1.2.1`。
- 2026-11-24 用该解释器运行 `python -m tools.pyrit_compat.runtime_probe --version 1.2.1`，结果 `PASS`：发行版版本匹配；14/14 符号签名检查 PASS；确定性 `SubStringScorer` + `ContentScorable` 命中 `true`。报告见 `docs/operations/pyrit-compat-runtime-verification.json`。
- 运行时额外发现但不属于参数丢失的字段：`XPIATestWorkflow.processing_target`、`ContentScorable.scorable_type`、`TrueFalseQuestion.category/metadata`、`MessagePiece` 若干元数据字段；均为加法字段，不触发 `PARAM_REMOVED`。
- 1.1.0 与 1.2.0 未在本机安装，其结论仍仅来自 tag 源码；**不冒称三版本 venv 运行时矩阵已完成**。
- `XPIATestWorkflow` 端到端对象图仍保留仓库既有「signature_unverified」闸门：签名一致不等于目标侧可用。
- 所有示例均不涉及真实凭据或向 `http://192.168.40.189` 投放载荷。
