# AI red team 混合测试架构：Python 编排为主 + PyRIT 有边界升级

> **性质**：完整优化方案与执行结果确认，非考试提交件。
> **事实源**：`docs/governance/references/OSAI-Exam-Guide-snapshot.md`（考试规则）、
> `docs/operations/osai-ai300-curated-payloads.md`（策略对比）、
> `docs/operations/pyrit-integration-verification-2026-11-26.md`（PyRIT 实测）、
> `tools/attack_ai_agent/hybrid.py`（本方案实现）、`tests/attack_ai_agent/test_hybrid.py`（21 例验证）。
> **边界**：全部实测来自 DVAA / AIVP 演练目标，不是 OSAI 正式考试环境；
> `proven` 只表示「可复现出现」，不代表稳定成功；命中率必须带分子分母。

## 1. 优化方案说明

### 1.1 选型依据

从考试得分结构反推，而非按工具先进度选型：

| 一手事实 | 推导 |
|---|---|
| 75/100 通过，八台计分目标；得分需要正确答案 + 报告完整性 | 覆盖广度优先于单台深度 |
| 面板校验值与截图双通道缺失、文档缺失是取消资格项 | 证据链是所有 100 分的前置条件 |
| 24h 考试 + 24h 报告双窗口 | 时间与认知负担是硬预算 |
| OSAI 明确允许 AI 工具；官方鼓励在 attack 全流程使用 | 合规不成为约束，但使用顺序影响收益 |
| PyRIT `RedTeamingAttack` 对加固目标 3 轮 92.7s 得 `FAILURE`；`Crescendo`/`TAP` 未实跑 | 原生多轮成本高、无命中率基线，不宜首轮 |

**结论**：Python 编排负责全局确定性与证据，精选载荷清单负责首轮命中率，
PyRIT 只在「对话面 + 前置层耗尽 + 显式启用 + 边界合规」时升级执行。

### 1.2 分层与职责边界

| 层 | 组件 | 职责 | 明确不做 |
|---|---|---|---|
| L0 证据骨架 | `evidence_pipeline.py`、`osai-orchestrator`、`tooling-automate` | 八目标映射、双通道留痕、预算栅栏、AI 交互日志 | 不含攻击载荷、不判命中 |
| L1 形态适配 | `dialogue.ChatSpec`、`target_profile` | 把目标画像翻译为路径/请求体/响应取值；字段缺失退回整段 | 不改载荷文本、不发起 PyRIT |
| L2 首轮载荷 | `strategies.json`（11 条）、`negation.judge`、`dialogue.score` | proven 6 条优先，两次上限，确定性→否定语境→语义否决 | 语义层只否决、不认定生效 |
| L3 即时生成 | 调用方注入的 `generated_payloads` | 有边界补位：受 refuted 黑名单约束，命中后回填 | 不在模块内自行构造措辞 |
| L4 PyRIT 升级 | `hybrid.escalation_gate` → `pyrit_multiturn.run_multiturn` | 门控后的多轮对抗；双模型评分；`executed` 事实层 | 不隐式触发、不绕过门控、不重复刷同一载荷 |
| L5 统一出口 | `HybridResult.as_dict()` | 步骤、判定、升级决策、回退原因一次输出 | 不伪造 flag/截图/面板值 |

依赖单向：`hybrid → (dialogue, strategies, negation) → 目标`；
`hybrid → pyrit_multiturn → pyrit_semantic → pyrit`。反向无依赖；
顶层零 pyrit 导入，零 pyrit 环境可完整跑 L0–L3。

### 1.3 Python 编排流程

`hybrid.run_hybrid()` 是唯一公开 seam，顺序固定、不跳不合并：

1. **形态解析**：`spec = spec or dialogue.PRESETS["chat"]`，记录 `shape` 到诊断字段；
2. **tier1（proven）**：逐条最多 2 次；生效即停；出现拒绝标记即停；异常收敛为「发送失败」；
3. **即时生成补位**：使用注入的 `generated_payloads`，最多 1 次；命中即标记「回填策略库」；
4. **tier2（unstable）**：最多 1 轮；命中即停；
5. **升级门控**：`EscalationContext` → `escalation_gate()`，记录判定与冲突到结果；
6. **升级执行**：仅 allowed 时调用注入的 `escalator`；异常被捕获，不向外抛；
7. **统一出口**：`executed` 只反映真实执行，`effective` 只由评分链或原生 objective_score 决定。

### 1.4 PyRIT 升级：触发、禁止与冲突裁决

### 应触发（全部满足，缺一不可）

1. `target_shape ∈ {chat, agent_chat}`——仅对话面；
2. `objective` 非空且单一；
3. tier1 已实际执行且无生效载荷；
4. 已完成即时生成补位或 tier2 尝试（不得跳过低成本层）；
5. `pyrit_available=True` 且双模型凭据齐备；
6. `user_opt_in=True`——调用方显式启用；
7. `1 ≤ max_turns ≤ 3`、`1 ≤ timeout ≤ 600`、`prior_escalations < 1`。

### 不应触发（任一命中即拒，reason 必填）

| 条件 | reason 关键词 |
|---|---|
| 非对话形态（MCP 工具面 / 检索面 / 传统向量） | 非对话形态 |
| 已有生效载荷 | 已有生效载荷 |
| objective 为空 | 目标描述为空 |
| 出现明确拒绝或规则检测 | 拒绝即停 |
| 凭据缺失 / pyrit 不可用 | 缺少双模型凭据 / 降级 |
| 未显式启用 | 未显式启用升级 |
| tier1 未执行 / 仅 tier1 无补位 | tier1 未执行 / 即时生成补位 |
| 轮次、超时、次数越界 | 越界 / 次数已用尽 |

### 冲突判定规则（优先级从高到低，已固化为测试用例）

1. 硬阻断（凭据缺失、越界、拒绝、检测、已有生效载荷）> 用户 opt-in；
2. tier1 未试完 > 用户 opt-in；
3. 无 opt-in 一律不升级，即使 pyrit 与凭据均就绪；
4. opt-in 但 pyrit 不可用 → 允许 Python 补位，不升级、不报错；
5. 多条冲突全部记录到 `conflicts`，不隐式合并或覆盖。

### 1.5 调用边界

| 项 | 约定 |
|---|---|
| 调用方 | 仅 `hybrid.run_hybrid()`；技能脚本不直接 `import pyrit` |
| 被调用范围 | 仅 `pyrit_multiturn.run_multiturn()`；不直接调用 `pyrit_semantic.make_*` 或原生类 |
| 输入 | `objective, strategies_to_run, generated_payloads, base_url, spec, pattern, sender, escalator, pyrit_available, credentials_ok, user_opt_in, max_turns, timeout` |
| 输出 | `HybridResult.as_dict()`：`executed / effective / steps / escalation / escalation_result / fallback / diagnostics` |
| 异常处理 | sender 异常 → StepOutcome「发送失败」；escalator 异常 → fallback「升级执行异常」，`escalation_result=None`；均不向外抛 |
| 回退策略 | 生效即固化 → 命中即回填 → 未生效转下一目标 → 升级失败保留失败事实、不伪称成功 |

## 2. 分阶段实施清单

| 阶段 | 目标 | 改动文件 | 验收条件 | 状态 |
|---|---|---|---|---|
| P0 规则对齐 | 把考试计分与证据约束转为选型依据 | 无（只读快照与策略文档） | 75/100、双通道、24h 三约束均有逐字出处 | 完成 |
| P1 能力盘点 | 盘点既有组件与 seam，确定零重写边界 | 无（只读） | 六层组件与依赖方向确认 | 完成 |
| P2 门控实现 | 触发/禁止/冲突裁决固化为纯函数 | `tools/attack_ai_agent/hybrid.py` | `escalation_gate()` 纯函数、无副作用 | 完成 |
| P3 编排实现 | 唯一 seam、依赖注入、事实层 | 同上 | `run_hybrid()` 顶层零 pyrit 导入 | 完成 |
| P4 场景验证 | 典型/边界/误触发全覆盖 | `tests/attack_ai_agent/test_hybrid.py` | 21 例全绿 | 完成 |
| P5 方案落档 | 本方案文档与结果确认 | 本文档 | 与现有文档不冲突、术语门禁 PASS | 完成 |
| P6 门禁回归 | 全量与静态门禁复跑 | 无 | 见 §3 | 待执行 |
| P7 提交合并 | PR、CI、合并、main 同步 | 无 | CI 全绿、main 同步 0/0 | 待执行 |
| P8 考试窗口 | 真实目标取证、截图、报告 | 不入库 | 只在正式窗口填写，不伪造 | 未开始 |

## 3. 验证与对齐方案

### 3.1 场景验证矩阵（21 例，全离线）

| 类别 | 场景 | 期望 | 用例 |
|---|---|---|---|
| 典型 | 条件全满足 | 允许升级 | `test_allow_when_all_conditions_met` |
| 典型 | 默认无 opt-in | 停 Python 层，不调用 escalator | `test_default_stops_at_python_layer` |
| 典型 | 门控放行 | escalator 收到 objective/max_turns/base_url | `test_escalation_called_when_gate_allows` |
| 典型 | 载荷命中 | 停在首轮、不生成、不升级 | `test_success_stops_before_generation_and_escalation` |
| 边界 | 非对话形态（mcp/rag/traditional） | 拒绝 | `test_deny_non_chat_shape` |
| 边界 | `agent_chat` 形态 | 允许（同属对话面） | 同上 |
| 边界 | 空 objective / 轮次 0、4 / 超时 0、601 | 拒绝 | `test_deny_empty_objective`、`test_deny_turn_and_timeout_bounds` |
| 边界 | 升级次数已用尽 | 拒绝 | `test_deny_exhausted_escalation_budget` |
| 边界 | 拒绝或检测信号 | 立即停止该载荷 | `test_refusal_or_detection_stops`、`test_refusal_stops_immediately` |
| 误触发 | opt-in + 凭据缺失 | 拒绝，硬阻断优先 | `test_opt_in_cannot_override_missing_credentials` |
| 误触发 | opt-in + 已有生效载荷 | 拒绝，避免重复投入 | `test_opt_in_cannot_override_effective_payload` |
| 误触发 | opt-in + pyrit 不可用 | 拒绝并降级，不报错 | `test_opt_in_without_pyrit_degrades` |
| 误触发 | 多条冲突并存 | 全部记录不丢失 | `test_multiple_conflicts_all_recorded` |
| 异常 | escalator 抛错 | 收敛为未生效 | `test_escalator_exception_is_contained` |
| 异常 | sender 抛错 | 记为发送失败 | `test_sender_exception_is_contained` |
| 契约 | 结果事实层 | `executed/effective/escalation` 均在 | `test_result_as_dict_has_fact_layer` |

### 3.2 与既有资产对齐

- **不破坏既有结论**：`strategies.json` 11 条、`negation.judge`、`dialogue.score`、
  `pyrit_multiturn.run_multiturn` 均只被调用、未被改写。
- **不新增版本事实缺口**：新增模块在 `tools/attack_ai_agent/` 内，无新的 PyRIT import
  符号；S1 映射覆盖率维持 33/33。
- **零 pyrit 环境**：顶层无 pyrit 导入，`import tools.attack_ai_agent.hybrid` 与
  L0–L3 流程在无包环境可执行；pyrit 路径由注入替身覆盖验证。
- **事实层一致**：`executed` 语义沿用 #458 的「声明与执行分离」，不把降级写成成功。

### 3.3 验证命令

```bash
python -m unittest tests.attack_ai_agent.test_hybrid
python -m unittest discover -s tests -t .
python -m tools.pyrit_compat.checker check --root . --target 1.2.1
python scripts/check_glossary.py
python scripts/check_token_budget.py --check
python scripts/check_tools_compile.py --check-missing
npx markdownlint-cli2 "docs/operations/ai-red-team-hybrid-architecture.md"
```

## 4. 与 AI red team 进攻方最佳实践原则的对应关系

| 原则（一手框架） | 本架构的落实 | 偏离或限制 |
|---|---|---|
| MITRE ATLAS：先侦察资产与暴露面再选手法 | L1 形态适配由 `target_profile` 驱动；换目标只改画像 | 资产发现仍依赖上游技能，本模块不重做 |
| MITRE ATLAS：按技术适用性而非通用性选攻击 | 门控按目标形态限定仅对话面；工具面/检索面走各自技能 | 非对话面不在此架构内 |
| OWASP LLM Top 10：提示注入与敏感信息泄露需可复现判据 | 11 条策略带 `pattern`；否定语境守卫 + 实值断言 | 判据只说明「可复现出现」，不承诺成功率 |
| OWASP LLM Top 10：过度代理与工具权限需独立验证 | MCP 工具面由 `attack-mcp-tool` 独立八步验证，不走 PyRIT 升级 | 明确排除在 L4 之外 |
| NIST AI RMF：测量需有记录、可审计、可复核 | `HybridResult` 留步骤/阶段/冲突/升级决策；AI 交互日志由 L0 统一 | 报告正文须由考生完成，不自动生成 |
| NIST AI RMF：风险管理按影响与可能性分级 | 升级限 1 次、3 轮、600s；refuted 黑名单免重复投入 | 成本上限按演练数据设定，非正式考试实测 |
| OffSec OSAI 指南：鼓励全流程使用 AI，但文档不充分即取消资格 | AI 用于编排与判定；证据片段 + 面板 + 截图双通道为统一出口 | 截图与面板值只在考试窗口产生，本架构不含伪造 |
| 进攻方通用纪律：拒绝即停、避免重放被拦截动作 | `_run_steps` 遇拒绝标记立即停止；门控再拒绝升级 | 拒绝标记是字符串启发式，非语义判定 |
| 进攻方通用纪律：成功即固化、失败回填 | 命中即返回；即时生成命中标记回填策略库 | 回填由调用方执行，模块不自写数据文件 |

## 5. 最终对齐结构、验证结构与执行结果确认

### 5.1 最终对齐结构

```
证据骨架 L0  →  形态适配 L1  →  首轮载荷 L2  →  即时生成 L3  →  门控 L4  →  统一出口 L5
   ↑                ↑                ↑                ↑             ↑             ↑
八目标映射      ChatSpec        strategies.json    注入载荷     escalation_gate  HybridResult
双通道留痕      target_profile   negation.judge     refuted 名单   pyrit_multiturn  executed/effective
```

### 5.2 验证结构与结果（执行时填写）

| 验证项 | 命令 | 实测结果 | 状态 |
|---|---|---|---|
| 单元场景 | `python -m unittest tests.attack_ai_agent.test_hybrid` | `Ran 21 tests ... OK` | PASS |
| 全量回归 | `python -m unittest discover -s tests -t .` | `Ran 1657 tests`，`OK (skipped=2)` | PASS |
| S1 映射门禁 | `python -m tools.pyrit_compat.checker check --root . --target 1.2.1` | 33/33、0 error、4 warn | PASS |
| 术语一致性 | `python scripts/check_glossary.py` | 66 个废弃术语检查通过 | PASS |
| 产物预算 | `python scripts/check_token_budget.py --check` | 结论 PASS（预算 + 规范契约齐全） | PASS |
| 编译检查 | `python scripts/check_tools_compile.py --check-missing` | 309 文件失败 0 | PASS |
| Markdown | `npx markdownlint-cli2 <本文档>` | 0 issues in 0 files | PASS |
| CI | PR 检查全绿 + main CI | 待提交后确认 | 待确认 |

**执行确认（2026-11-26 本机实测）**：新增 21 例场景测试全绿；全量 `Ran 1657 tests ... OK (skipped=2)`；
S1 映射门禁 PASS；术语、预算、编译、Markdown 四门禁 PASS。CI 结果在提交后按 §5.2 更新。

### 5.3 执行结果确认

### 已落地（代码与测试，可复核）

- `tools/attack_ai_agent/hybrid.py`：唯一 seam `run_hybrid()`、纯函数 `escalation_gate()`、
  `EscalationContext / EscalationGate / HybridResult` 三类值类型；顶层零 pyrit 导入。
- `tests/attack_ai_agent/test_hybrid.py`：21 例覆盖典型 4、边界 6、误触发 4、
  异常 2、契约 1 及参数化子场景。

### 停留在设计（须考试窗口或调用方配合）

- 即时生成载荷由调用方注入；refuted 命中后的回填由调用方写入策略库；
  截图与面板值由考试窗口产生——本模块不伪造、不代办。
- MCP 工具面、检索面、传统向量走既有技能，不纳入 L4 升级。

### 待正式窗口验证

- 正式考试目标上的命中率与 `FAILURE` 分布；`CrescendoAttack`/`TAPAttack` 未实跑，
  不列入成功率基线。
