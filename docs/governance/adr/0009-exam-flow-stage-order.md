# ADR-0009：考试链状态机阶段顺序对齐宪法 §4.5

- 状态：已接受
- 日期：2026-11-28
- 决策者：hmbphxkw76-byte

## 背景

`tools/osai_orchestrator/exam_flow.py` 的 `STAGES` 原以 `recon` 为首位、`threat-model` 次位，与 GOVERNANCE §4.5（MUST：`威胁建模(threat-model) → 侦察枚举(recon-ai) → 立足点 …`）及 `skills/capstone-rehearse/SKILL.md` 的编排顺序冲突。全仓审计 R07 标记此为实现与宪法的离群偏差。

按 GOVERNANCE §9.2 冲突优先级（官方事实 > MUST > SHOULD > 技能本地），宪法 §4.5 的 MUST 顺序高于实现侧的任意排列；`exam_flow.py` 是唯一离群项。

## 决策

1. `STAGES` 重排为 `threat-model` 首位、`recon` 次位，其余七阶段相对顺序不变。
2. `REQUIRED_GATES` 按阶段名索引，`recon` 与 `threat-model` 均消费 `H1`，重排不改变任何门判定逻辑（仅改变推进次序）。
3. `tests/osai_orchestrator/test_exam_flow.py` 三处顺序断言同步：`test_stage_order_is_fixed`（首两位）、`test_advance_single_step`（默认起点前进一步）、`test_run_with_handoffs_consumes_h1_to_h6`（H1 被阻时停留首阶段）。
4. `exam_flow.py` 在 `STAGES` 上方加宪法来源注释（隐藏约束：顺序由 §4.5 裁定，非任意）。

## 后果

### 正面

- 实现与宪法 §4.5、capstone-rehearse 编排顺序三者一致，消除 R07 离群偏差。
- 默认 `ExamPipeline()` 起点变为 `threat-model`，符合「威胁建模为执行前置」的宪法语义。

### 代价 / 权衡

- 顺序消费者仅 `exam_flow.py` 自身（`STAGES[0]` 默认值、`STAGES.index` 动态推进），无其他模块硬编码 `recon` 首位，故无下游破坏。
- 门按名索引，重排为零逻辑变更；127 个 orchestrator 测试全绿验证无回归。

## 关联

- GOVERNANCE §4.5（编排 MUST 顺序）、§9.2（冲突优先级）。
- `skills/capstone-rehearse/SKILL.md`（threat-model 先于 recon-ai）。
- `docs/operations/osai-exam-readiness-design.md` #449（状态机只消费 handoff 返回值，不复制判据）。
- 全仓审计 R07；先红后绿留痕见本会话 TDD 记录。