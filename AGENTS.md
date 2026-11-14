# AGENTS.md

AI 编码智能体在本仓库工作的约定入口。工程技能（`to-tickets`、`triage`、`to-spec`、`domain-modeling` 等）依赖 `docs/operations/` 下的配置，请先读取。

## Agent skills

### Mainline workflow

每份 `skills/*/SKILL.md` 的主线落地：先读 `docs/operations/skill-mainline-workflow.md`（唯一可信源），按其中 11 阶段顺序自动推进并逐阶段过 G0 门禁。

### Issue tracker

工作项以 GitHub Issue 形式存于 `hmbphxkw76-byte/redteam-ai300`，经 `gh` CLI 读写。见 `docs/operations/issue-tracker.md`。

### Triage labels

五个规范 triage 角色映射为默认标签字符串：`needs-triage`、`needs-info`、`ready-for-agent`、`ready-for-human`、`wontfix`。见 `docs/operations/triage-labels.md`。

### Domain docs

单上下文布局：`GLOSSARY.md` 位于仓库根，ADR 位于 `docs/governance/adr/`。见 `docs/operations/domain.md`。
