# 用开发流程技能将 SKILL.md 落地为 PyRIT 原生实现

> **状态**：历史映射草案 · **适用范围**：`skills/` 下全部 SKILL.md 的 PyRIT 对象映射参考
> **主线顺序（唯一可信源）**：[skill-mainline-workflow.md](skill-mainline-workflow.md)（11 阶段，自动调用，逐阶段 G0 门禁）。本文 §3 的 10 阶段链已作废，保留仅用于说明 SKILL.md 概念 → PyRIT 对象映射。
> **配套**：[治理规范](../governance/GOVERNANCE.md) · [术语表](../../GLOSSARY.md) · [技能规格 backlog](../skill-specs-backlog.md)

## 1. 背景与目标

- **现状**：`skills/` 下每份技能以 `SKILL.md`（Markdown）承载规格，含 §4.2 强制五要素（元信息 / 执行体 / 质量门 / 校验标准 / 失败与豁免）。
- **目标**：用 **PyRIT 原生框架**（Microsoft Python Risk Identification Toolkit）实现 SKILL.md 声明的攻击逻辑，而非手写 HTTP/脚本。
- **前提**：本机已安装工程技能族（mattpocock/skills，位于 `~/.workbuddy/skills/`），其 `to-spec`、`to-tickets`、`triage`、`domain-modeling` 等依赖 `docs/operations/` 下的配置。

本文档回答：**用哪些开发流程技能、以何种顺序，把一份 SKILL.md 落地为可纳入 CI 的 PyRIT 实现。**

## 2. 关键映射前提：SKILL.md 概念 → PyRIT 原生对象

`to-spec` 的核心动作，是把 SKILL.md 的「攻击路径」翻译为 PyRIT 对象图，而非复述原文。映射关系如下（具体 API 名称须经 `research` 按官方一手源核实）：

> **版本锁定（重要）**：PyRIT **v1.1.0（2026-09-04）** 删除了 `pyrit.orchestrator`，编排器更名为 `pyrit.executor.attack` 下的**攻击策略**（`*Attack`）；`AzureOpenAIChatTarget` 合并为单一 `OpenAIChatTarget`。实现须固定 `pyrit==1.1.0`，严禁套用 0.x 旧教程。以下映射以 1.1.0 为准，权威细节见 `../research/pyrit-native-api-attack-ai-agent.md`。
>
> **权威引用索引（单一可信源，供后续 `research` / `to-spec` / `implement` 阶段复用，每次先读）**：`../research/pyrit-canonical-references.md`（含版本固定、官方仓库/文档 URL、v1.1 重构要点、待核实项）。

| SKILL.md 概念 | PyRIT 原生对象（v1.1.0） |
|---|---|
| 攻击路径（A/B/C） | 攻击策略 `Attack`（`pyrit.executor.attack`，由 `AttackExecutor` 驱动） |
| 目标 AI 组件（agent / RAG / LLM 端点） | `Target`（`pyrit.prompt_target`：`OpenAIChatTarget` / `HTTPTarget` 等） |
| 注入 / 投毒话术 | 攻击策略入参的 objective / `TrueFalseQuestion`，间接注入用 `XpiaAttack` |
| 载荷混淆 / 逃逸护栏 | `Converter`（`pyrit.converter`：Translation/ROT13/Base64 等，可链式） |
| 判定「攻击是否生效」 | `Scorer`（`pyrit.score`：`SelfAskTrueFalseScorer` / `SubStringScorer` 等） |
| 跨会话状态（记忆滥用） | `Memory`（`pyrit.memory`，SQLite 默认，可选 Postgres/Azure SQL 后端） |

**示例**（`attack-ai-agent`，详见调研文档）：

| 攻击路径 | PyRIT 映射（v1.1.0） |
|---|---|
| 提示注入（ASI01） | `PromptSendingAttack` + `OpenAIChatTarget` + 直接注入 objective（+ `XpiaAttack` 处理间接注入）+ `SelfAskTrueFalseScorer` |
| 记忆滥用（ASI06） | `RedTeamingAttack`（`max_turns` 建立上下文）+ Memory 后端，跨会话验证投毒/泄露 |
| 工具滥用（ASI02） | 工具面 `OpenAIChatTarget`/`HTTPTarget` + `RedTeamingAttack`/`PromptSendingAttack` + `SubStringScorer` 判定越权调用 |

## 3. 主线技能（每份 SKILL.md 落地都走这条链）

| # | 阶段 | 技能 | 在 PyRIT 落地中的职责 |
|---|---|---|---|
| 1 | 调研 | `research` | 查清 PyRIT 原生 API 的准确用法（orchestrator / target / converter / scorer / memory），落盘为 repo 内调研文件 |
| 2 | 规格化 | `to-spec` | 把攻击路径显式映射为 PyRIT 对象图（见 §2），产出物发布到 issue tracker |
| 3 | 拆解 | `to-tickets` | 拆成 tracer-bullet 垂直切片（skill = parent + 每攻击路径子 ticket + flag 取证），声明 blocking 边 |
| 4 | 分类 | `triage` | 用五标签判定 `ready-for-agent` vs `ready-for-human`（如目标端点配置需人工） |
| 5 | 设计 | `codebase-design` | 设计 PyRIT 封装的深层模块接口，决定 seam（每个 skill 一个 orchestrator 文件 vs 抽公共 target/scorer） |
| 6 | 术语 | `domain-modeling` | 把 PyRIT 概念（orchestrator / converter / scorer / target / memory）纳入 `GLOSSARY.md` |
| 7 | 实现 | `implement` / `implement-spec` | 按 spec + tickets 写 PyRIT 代码 |
| 8 | 测试 | `tdd` | 红-绿-重构：为 orchestrator/scorer/converter 封装先写单测，对齐 `tests/` + CI `py_compile` |
| 9 | 审查 | `code-review` | 双轴审查：Standards（编码规范）+ Spec（忠实于 SKILL.md 五要素与质量门） |
| 10 | 交付 | `pr` + `pre-push-review` | 写 PR body 并在推送前做语义级双轴评审，衔接 CI 门禁 |

## 4. 支线技能（按需触发）

| 技能 | 触发条件 | 职责 |
|---|---|---|
| `prototype` | 正式 `to-spec` 前不确定某攻击路径能否被 PyRIT 表达 | 跑通最小 orchestrator（spike） |
| `wayfinder` | 一次性落地全部 13 个技能（P0–P2）超过单 agent session 容量 | 建 decision map 逐个解决 |
| `diagnosing-bugs` | PyRIT 运行时异常（端点不通 / converter 报错 / scorer 误判） | 诊断循环 |
| `handoff` | 多 agent 之间交接实现上下文 | 压缩会话为交接文档 |
| `writing-for-agents` | 需重写 SKILL.md 或 `AGENTS.md`（如补「用 PyRIT 而非手写 HTTP」） | 编写面向 agent 的文档 |
| `wizard` | 只有人能做的步骤（配置目标端点凭据、CI secrets） | 生成交互式 bash 向导 |
| `improve-codebase-architecture` | 后续重构已成型的 PyRIT 封装层 | 扫描 deepening 机会 |
| `grilling` / `grill-with-docs` | 用治理规范质疑封装设计是否合规、是否偏离评分驱动优先级 | 设计质疑 |

## 5. 落地约束（必须遵守）

1. **`to-spec` 须把「攻击路径」翻译成 PyRIT 对象，而非复述 SKILL.md**：否则拆出的 ticket 无法落到代码。以 `attack-ai-agent` 为例，三个攻击路径须分别落到 §2 的三行映射。
2. **`domain-modeling` 须把 PyRIT 术语纳入 `GLOSSARY.md`**：现术语表仅到「MCP / RAG / A2A / Embedding」层面，无 orchestrator/scorer 等实现层词汇；直接进入实现会触发 `check_glossary` 门禁。
3. **CI 门禁定义验收标准**：每份 skill 落地须通过 `validate_skill` + `check_glossary` + `py_compile`（及 S2 证据契约测试），故 `tdd` 与 `code-review` 的判据应对齐 `scripts/` 与 `tests/`，而非主观判断。

## 6. 建议起点与验收

- **起点**：先用 `research` + `to-spec` 对单个技能（建议 `attack-ai-agent`，攻击面最典型）跑通一次 tracer bullet，确认「SKILL.md → PyRIT 对象映射」链路可行、产出可拆 ticket 的规格，再复制到 `attack-rag` 与 backlog 中的 P0 技能。
- **验收**：tracer bullet 完成的判据是——产出至少一条可运行的 PyRIT orchestrator 调用链，且其证据（命令 + 输出 + 截图）满足 §6 质量基线、经 `tools/collect_evidence.py` 落盘、通过 CI 门禁。

## 7. 参考

- GOVERNANCE §4.2（五要素）、§4.4（技能清单）、§4.5（编排流水线）、§6（质量基线）、§8（校验机制）
- GLOSSARY.md（术语唯一基准）
- ADR-0001（单 Markdown 治理）、ADR-0002（评分驱动优先级）、ADR-0003（CI/CD GitHub Actions）
