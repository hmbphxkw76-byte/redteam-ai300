# tooling-automate 主线门禁索引

> 依据 `docs/operations/skill-mainline-workflow.md` §2；逐阶段记录见 per-stage 文件（每个 ≤2KB）。B1–B8 定义见 §2.1，此处不重复（C1）。

## 隔离基线（ADR-0006）

- worktree `D:/_tooling-automate_wt` · 分支 `feat/tooling-automate` · 基线 `origin/main` = `20ce2eb`。
- 复用核验：`git status --porcelain` 空、`git rev-list --count origin/main..feat/tooling-automate` = 0、`HEAD` == `origin/main`；等价 `mainline_worktree.py create` 结果。
- 本地主工作树 `main` 落后 `origin/main` 1 提交；全部落地仅在 worktree 内进行，不改共享主工作树。
- 目标 issue 仓库 `hmbphxkw76-byte/redteam-ai300`（`gh repo view` 已确认）。

| 阶段 | 名称 | 结论 | 门禁记录 |
|---|---|---|---|
| 1 | research | PASS（B7/B8，0 不符合项） | `docs/research/tooling-automate-canonical.md` §门禁记录 |
| 2 | to-spec① v1 | PASS（B1/B2/B8，C4 修正后 0 不符合项） | `docs/operations/tooling-automate-gate-stage2.md` |

- 阶段 1 交付物：`docs/research/tooling-automate-canonical.md`（16 条条款映射、VG-1…VG-4 核实闸、已排除清单）。
- 阶段 2 交付物：v1 = `docs/specs/tooling-automate-spec-v1.md`（7993B，七节 / 30 US）；规格 issue = #240（`ready-for-agent`）；seam 结论 = 1 处（用户 2026-11-15 确认）。
- 门禁摘要：阶段 1 / 2 已按 T5 补登于 issue #240 评论区。
