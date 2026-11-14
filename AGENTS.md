# AGENTS.md

AI 编码智能体在本仓库工作的约定入口。工程技能（`to-tickets`、`triage`、`to-spec`、`domain-modeling` 等）依赖 `docs/operations/` 下的配置，请先读取。

## Agent skills

### Mainline workflow

每份 `skills/*/SKILL.md` 的主线落地：先读 `docs/operations/skill-mainline-workflow.md`（唯一可信源），按其中 11 阶段顺序自动推进并逐阶段过 G0 门禁。

### 唤醒词 / 触发短语（全量 11 阶段一键落地）

用户可用以下任一短短语触发「完整 11 阶段主线落地」，无需长说明；agent 识别后立即按 `skill-mainline-workflow.md` 顺序 1→11 推进，逐阶段过 G0 门禁（用户 2026-11-14 设定，详见项目记忆与 `skill-mainline-workflow.md`）：

- `/主线 [技能名]` · `全量落地 [技能名]` · `走全量 [技能名]` · `11阶段 [技能名]` · `完整流程 [技能名]`

约定：
1. `[技能名]` 缺省时询问目标，或默认 tracer bullet `attack-ai-agent`（已有 `docs/research/pyrit-native-api-attack-ai-agent.md` 与 issue #83）。
2. **强制包含 to-spec 两遍**：阶段 2（行为规格 v1，七节模板）与阶段 3（工程规格 v2 定稿，布尔验收条件）必须各自独立执行、独立留痕、版本号递增，**不得合并为一次、不得跳过任一遍**。`to-spec` 必须加载在本流程中。
3. 阶段 1 `research` 必跑（事实须一手源核实），即便用户称「已想清楚」。
4. 顺序固定、不跳、不合并、不并行；每阶段收尾 G0 结论 `PASS` 才进下一阶段。

### Issue tracker

工作项以 GitHub Issue 形式存于 `hmbphxkw76-byte/redteam-ai300`，经 `gh` CLI 读写。见 `docs/operations/issue-tracker.md`。

### Triage labels

五个规范 triage 角色映射为默认标签字符串：`needs-triage`、`needs-info`、`ready-for-agent`、`ready-for-human`、`wontfix`。见 `docs/operations/triage-labels.md`。

### Domain docs

单上下文布局：`GLOSSARY.md` 位于仓库根，ADR 位于 `docs/governance/adr/`。见 `docs/operations/domain.md`。
