# AGENTS.md

AI 编码智能体在本仓库工作的约定入口。工程技能（`to-tickets`、`triage`、`to-spec`、`domain-modeling` 等）依赖 `docs/operations/` 下的配置，请先读取。

## Token 预算纪律（全项目强制 · 2026-11-14 生效）

目标：在不削减得分前提（GOVERNANCE §6/§7/§8.2、flag 双通道、G0 `PASS`）下降低编排层与运行时 token。细则见 `docs/operations/skill-mainline-workflow.md` §2.4；度量与门禁 `python scripts/check_token_budget.py --check`（CI S1）；三层保障模型见 `docs/governance/adr/0005-token-budget-discipline.md`。

**跨 IDE 迁移必须同步 C1–C8** 到目标 IDE 的 rules 文件；仅复制 11 阶段流程视为迁移未完成。

- **C1 单一事实源（MUST）**：同一事实只存一份，其余只写 `路径#锚点`；禁止转抄宪法条款、B1–B8 定义、PyRIT API 事实、证据片段、AI 交互日志、门禁记录。
- **C2 增量门禁（MUST）**：G0 记录只写「本阶段变更项 + 判定 + 复验命令 + 结论」，每项输出摘要 ≤3 行；§2.3 上游复核实跑命令、不复述上游正文；全量 B1–B8 汇总只在阶段 11 出具一次，**逐条判定语义不变**。
- **C3 按需读取（MUST）**：已注入上下文的文件不重读；>200 行先 Grep 定位再按 offset/limit 读；**冷备文档默认不加载**（清单见检查器 `COLD_GLOBS`：跨 IDE 通用版、backlog、历史 PyRIT 映射、实现/门禁记录、模板与示例）。本地 `.workbuddy/memory/2026-*.md` 日志同样按冷备处理，持久事实只读 `MEMORY.md` 主题索引。
- **C4 产物预算（MUST）**：规格 v1 ≤8KB、v2 ≤10KB、单阶段门禁记录 ≤2KB、PR 正文 ≤3KB、issue 摘要 ≤400B、子 agent brief ≤1KB；超限即 `BLOCKED`。压缩产物时验收条件必须逐条完整保留。仓库外产物用 `python scripts/check_token_budget.py --artifact <KIND> <PATH>` 判定（`KIND` 取 `spec-v1` / `spec-v2` / `gate-record` / `pr-body` / `issue-summary` / `agent-brief`）。其中 `pr-body` 由 CI S1 在 `pull_request` 事件自动判定；其余五类在生成时本地调用。
- **C5 子 agent 契约（SHOULD）**：子 agent 不继承主会话注入，brief 首行必须显式写明「遵循 `AGENTS.md` C1–C8」；brief 只带路径 / 验收命令 / 约束，不带正文；`docs/research/` 已核实事实不再起 research 子 agent；并行子 agent ≤2。
- **C6 运行时 AI（SHOULD）**：确定性 `SubStringScorer` 命中即判，不追加 LLM judge；用 `--step` 单步复现代替全量路径；每轮只带增量上下文；recon / loot / evidence 落盘后按路径引用，不反复贴入对话。
- **C7 记忆蒸馏（SHOULD）**：日志 append-only，单文件达 24KB 即按主题蒸馏进 `.workbuddy/memory/MEMORY.md` 并归档；`MEMORY.md` ≤3,000 字符，只存指针不存正文。
- **C8 不可豁免（MUST NOT）**：§6 证据三/五件套、§8.2 八项检查、flag 双通道、11 阶段顺序与 to-spec 两遍必须完整保留，任何删减判定不合规。与预算条款冲突时按 GOVERNANCE §9.2 优先保分。

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
