---
name: osai-exam-orchestrator
priority: P2
domain: D1, D2, D3, D4, D5, D7, D10, D11
scoring_unit: 通用
trigger: 需要在 24 小时考试窗口内增强编排韧性（防卡死、防跑飞、上下文压缩、人在环、独立复核），且不改变任何既有攻击技能
input: PentAGI 迁移清单 A/B 类判据、4 份提示词分册、既有 S-1 入口与 pyrit_compat 注册表
output: 可调用的运行时能力模块 tools/osai_orchestrator/（19 项能力域），纯增量、零外部依赖
---

# osai-exam-orchestrator — 考试编排与韧性增强

把迁移清单中的 A/B 类判据实现为纯逻辑能力层，**只增强既有技能，不修改、不替代任何既有 `skills/*/`**。工具执行经 `tooling-automate` 的 S-1 入口，版本兼容经 `tools/pyrit_compat/` 注册表，证据收口经 `tools/collect_evidence.py`。

## 执行体

按「运行时监督 → 计划与人在环 → 上下文与记忆治理 → 工具治理 → 报告治理」五域推进。

### 1. 运行时监督

- `ExecutionMonitor` 检测同工具调用（默认 5 次）与总调用（默认 10 次）阈值；推进判定由调用方基于事实给出，模块不猜测。
- `Reflector` 连续失败达阈值（默认 3 次）时给出继续/终止判定；无恢复动作即收口。
- `ToolCallBudget` 按角色分级硬上限（通用 100 / 受限 20），待办超出余量时判 `BLOCKED` 并要求重排。
- `Barrier` 仅在目标达成、证据路径存在、flag 双通道核验通过时放行 `done`；否则 `ask`。

### 2. 计划与人在环

- `Planner` 生成 3–7 步清单并校验 step_id 唯一、验证点存在；`wrap` 产出 `<task_assignment>` 包裹文本。
- `Refiner` 支持 add/remove/modify/reorder 四类增量操作，已完成步骤不可变。
- `HumanInLoop` 提供状态查询/停止/提交输入/改步骤/等待五类控制，状态先于变更、一次一动作。

### 3. 上下文与记忆治理

- `SummaryMarker` 标记摘要为历史上下文并检测检索片段中的指令式注入（只标记不执行）。
- `ContextCompactor` 压缩时保留 IP、证据路径与步骤标识，不产生新建议。
- `Anonymizer` 把地址/域名/凭据/令牌替换为占位符；`MemoryWhitelist` 只沉淀方法论类内容。
- `IndependentReviewer` 逐条对照原始要求，只认报告位置，不引用执行者结论。

### 4. 工具治理

- `TypedRegistry` 按类型与角色限定可用工具集；`CallIDNormalizer` 归一化跨模型调用 ID 并修复残缺参数。
- `ErrorClassifier` 区分确定性/瞬时错误；`RetryPolicy` 对确定性错误零重试。
- `BoundedRetriever` 仅接受本地来源、无目标标识的检索命中，默认上限 5。

### 5. 报告治理

- `TemplateOverlay` 按语境渲染模板，缺失变量即 `BLOCKED`；`Ontology` 固定节点/关系/状态词表，禁止自造。

## 质量门

- 19 项能力域均有失败用例与通过用例（标准库 `unittest`）。
- 不修改任何既有 `skills/*/SKILL.md`、`tools/*` 既有文件或 `GLOSSARY.md` 既有条目语义。
- 零第三方依赖、零 PyRIT 运行时强依赖；外部命令经可注入 `CommandRunner`。
- 术语符合 `GLOSSARY.md`；证据契约与 flag 双通道未被改写。

## 校验标准

```bash
python -m py_compile tools/osai_orchestrator/*.py
python -m unittest discover -s tests/osai_orchestrator -t . -v
python -m tools.osai_orchestrator --plan
python scripts/check_glossary.py
python scripts/check_token_budget.py --check
```

## 失败与豁免

- 本模块不含攻击逻辑，不连接真实目标、不读凭据、不投放载荷。
- 未实现的 A/B 项（如有）如实列入缺口，不伪造能力。
- 与既有技能冲突时以既有技能语义为准，本模块仅提供可选增强。

> 主线：`docs/operations/skill-mainline-workflow.md`（C1/C8：11 阶段、to-spec 两遍、G0）。
