# 11 阶段主线工作流 · 独立提示词库（跨 IDE 部署层）

## 1. 定位与同步规则

本目录是 `docs/standards/cross-ide-mainline-workflow.md`（跨 IDE 通用版方案）的**提示词部署层**：

- 提示词正文的事实源是 cross-ide doc §4；本目录把每个阶段模板扩展为「目标 / 输入 / 输出 / 触发条件 / 上下游衔接 / G0 门禁」统一结构的独立文件，可直接单文件复制到任意 IDE 使用。
- **同步规则（C1 单一事实源）**：修改提示词语义时，先改 cross-ide doc §4（或先改本目录），再同步另一处，两处语义必须一致。IDE 目录下的拷贝（如 `.github/prompts/`、`.cursor/rules/`）不作为事实源、不回改。
- 本目录属冷备文档（Token 预算纪律 C3），日常会话默认不整目录加载，按需取用。

## 2. 目录结构

```
docs/standards/prompts/
├── README.md            # 本文件：结构说明 + 变量表 + IDE 放置与激活指南
├── 00-mainline.md       # 编排器：全量 11 阶段一键执行（唤醒词语义）
├── 01-research.md       # 阶段 1  调研（一手源核实事实）
├── 02-to-spec-1.md      # 阶段 2  行为规格 v1（七节，只答 What）
├── 03-to-spec-2.md      # 阶段 3  工程规格 v2 定稿（布尔验收条件）
├── 04-to-tickets.md     # 阶段 4  垂直切片工单拆解
├── 05-triage.md         # 阶段 5  五标签分类定级 + agent brief
├── 06-codebase-design.md# 阶段 6  模块边界与 seam 设计
├── 07-domain-modeling.md# 阶段 7  术语基准统一（GLOSSARY/ADR）
├── 08-implement-spec.md # 阶段 8  最小可验证实现切片
├── 09-tdd.md            # 阶段 9  红—绿—重构测试收敛
├── 10-code-review.md    # 阶段 10 双轴审查（Standards / Spec）
└── 11-pr-push-review.md # 阶段 11 PR + 推送前评审 + 双通道推送
```

## 3. 每个阶段文件的统一结构

每个阶段文件固定四段，保证「结构统一、可独立执行」：

1. **同步源指针**：指向 cross-ide doc 对应小节（C1）。
2. **字段表**：目标 / 输入 / 输出 / 触发条件 / 上游衔接 / 下游衔接 / G0 门禁，各一行。
3. **提示词正文**（代码块内）：自包含指令——首行声明阶段身份，第二段校验上游产物（缺失即索取或回退，不得凭空假设），然后是任务与硬约束，末尾强制 G0 收尾。整段复制到任何 AI IDE 对话即生效，不依赖平台。
4. **G0 收尾自检**：该阶段的可勾选验收清单。

独立执行的衔接保障：每个提示词自带「上游校验 + 回退规则」，因此单独运行阶段 N 时，若上游产物缺失，agent 会先索取/回退而不是继续——衔接关系内嵌在提示词里，不依赖外部编排。

## 4. 变量表（使用前替换）

| 变量 | 含义 | 本项目默认值（迁移时替换） |
|---|---|---|
| `{CAPABILITY_DOC}` | 能力声明文档路径 | `skills/<技能名>/SKILL.md` |
| `{SKILL_NAME}` / `{TOPIC}` | 技能名 / 调研主题 | 缺省询问；默认 tracer bullet 同下行 |
| `{DEFAULT_SKILL}` | tracer bullet | `attack-ai-agent` |
| `{ISSUE}` | 规格 issue 编号/链接 | 阶段 2 产物，阶段 3 起引用 |
| `{COVERAGE}` | 业务代码覆盖率阈值 | `80%` |
| `{BASE_REF}` | 审查/推送基线 | `merge-base origin/main HEAD` |
| `{GATE_CMD}` | 门禁套件命令 | 测试 + 覆盖率 + 术语/预算检查器 + lint（见 CI-CD S1–S4） |
| `{PRIMARY_CHANNEL}` / `{BACKUP_CHANNEL}` | 推送通道 | SSH `origin` → HTTPS `origin-https`，各试一次即停 |

## 5. 三种使用方式

1. **全量执行**：把 `00-mainline.md` 的提示词正文粘贴进对话（或注册为 IDE 命令，见 §6），替换变量后发送。agent 将按 1→11 逐阶段推进，每阶段使用对应的独立提示词。
2. **单阶段执行**：粘贴某个阶段文件的提示词正文并替换变量。适用于重跑某个阶段（如仅重做 to-spec②）或跨会话续接。
3. **自动推进中人工介入**：阶段 2 的 seam 核对、阶段 3 的差异确认等本就设计为暂停点，agent 会在该处停下等用户确认——这不是流程中断，而是原设计行为。

## 6. IDE 组织、放置与激活

通用原则：提示词正文平台无关；部署 = 把文件放入各 IDE 的 prompt / command / rule 目录并按需加该平台要求的 frontmatter。**只适配调用外壳，流程与模板不变。**

### 6.1 VS Code（GitHub Copilot Chat）

- **放置**：`.github/prompts/<name>.prompt.md`。每个文件成为 Chat 中的斜杠命令（如 `research.prompt.md` → `/research`）。
- **frontmatter**（可选）：`description:`（命令说明，显示在补全列表）、`mode: ask | edit | agent`（默认交互模式）。
- **激活**：Copilot Chat 输入框键 `/` 即列出；需较新版本 VS Code / Copilot Chat，以官方文档为准。
- **全局纪律**（G0 基线、Token 预算等持续生效的规则）放 `.github/instructions/*.instructions.md`，frontmatter `applyTo: "**/*.md"` 等模式控制注入范围。
- **放置脚本**：

```bash
mkdir -p .github/prompts
cp docs/standards/prompts/00-mainline.md .github/prompts/mainline.prompt.md
for f in docs/standards/prompts/[0-9][0-9]-*.md; do
  n=$(basename "$f" | sed -E 's/^[0-9]+-//; s/\.md$//')
  cp "$f" ".github/prompts/${n}.prompt.md"
done
```

### 6.2 Cursor

- **放置**：`.cursor/rules/<name>.mdc`（Project Rules），frontmatter：

```
---
description: <一句话说明，用于 agent 决定何时采用>
globs:
alwaysApply: false
---
```

- **激活**：`alwaysApply: false` + `globs` 留空 → 对话中 `@<规则名>` 手动激活（等效单阶段触发）。编排器规则命名为 `mainline.mdc`，通过 `@mainline` 触发全量流程；不建议 `alwaysApply: true`（常驻注入成本高）。
- 旧版单文件 `.cursorrules` 已弃用，新项目一律用 Project Rules。

### 6.3 Claude Code

- **放置**：`.claude/commands/<name>.md` → 注册为斜杠命令 `/name`；frontmatter 可加 `description`、`argument-hint`（如 `argument-hint: [技能名]`）。
- **指针**：仓库根 `CLAUDE.md` 加一行指向 cross-ide doc（写法同 `AGENTS.md`）。

### 6.4 Cline

- **放置**：`.clinerules/` 目录下 `.md` 文件自动全部注入上下文。
- **建议**：只放「00 编排器 + G0/预算纪律」两条；11 个阶段提示词按需粘贴，避免常驻上下文膨胀。

### 6.5 Windsurf

- **放置**：`.windsurf/rules/*.md`（支持 frontmatter 触发模式：手动 / glob / 常驻）；旧 `.windsurfrules` 单文件已弃用。

### 6.6 Aider（无命令机制）

- `CONVENTIONS.md` 经 `--read CONVENTIONS.md` 常驻（放指针 + G0 纪律）；阶段提示词从本目录复制粘贴。

### 6.7 WorkBuddy / CodeBuddy

- `AGENTS.md` 指针与唤醒词小节已存在（`/主线 [技能名]` 等）；阶段提示词可注册为用户级 skill，或直接按需粘贴。

### 6.8 平台机制对照表

| 平台 | 机制 | 目录 | 激活方式 |
|---|---|---|---|
| VS Code + Copilot | Prompt Files | `.github/prompts/*.prompt.md` | Chat 中 `/` 命令 |
| VS Code + Copilot | Instruction Files | `.github/instructions/*.instructions.md` | 按 `applyTo` 自动注入 |
| Cursor | Project Rules | `.cursor/rules/*.mdc` | `@规则名` 或 glob 自动 |
| Claude Code | Slash Commands | `.claude/commands/*.md` | `/name` |
| Cline | Rules | `.clinerules/*.md` | 自动全量注入 |
| Windsurf | Rules | `.windsurf/rules/*.md` | 按触发模式 |
| Aider | 约定文件 | `CONVENTIONS.md` | `--read` 常驻 |
| WorkBuddy / CodeBuddy | AGENTS.md + skills | 仓库根 / 用户级 skills | 唤醒词 / 粘贴 |

> 各平台命令与规则机制随版本演进，以官方文档为准；上表给出的是组织方式，语义以本目录提示词正文为准。

## 7. 迁移与裁剪注意

- 迁移 = 复制本目录 + cross-ide doc + 在目标 IDE 指令文件加指针；**流程、门禁、提示词模板不变**。
- §4 变量表中「本项目默认值」列按目标项目替换（覆盖率阈值、推送通道、门禁命令等）。
- 纯个人项目裁剪建议见 cross-ide doc §1 与 MEMORY 相关条目：保留 research / to-spec 两遍 / codebase-design / tdd / code-review 内核，轻量化 to-tickets / domain-modeling / pr-push-review，折叠 triage 为规划自查。
