# 阶段 11 门禁记录 — `pr-push-review`

**结论：PASS** — PR #255 已合并，CI S1–S4 全绿，issue #240/#242–#248 已关闭。

## 串行解锁

- 用户授权合并 PR #230（attack-infra）→ `origin/main` `e528801`。
- `git rebase origin/main` 重放提交；冲突取并集：
  - `GLOSSARY.md`：保留「自动化编排」与「AI 基础设施」两节；上限随 main=17500，实测 17239/17500。
  - `scripts/measure_coverage.py`：`attack_infra_targets` + `tooling_automate_targets` 双 target 并存。
- 陈旧断言修复已由 PR #254 先行落地（本分支冗余提交于 rebase 时丢弃）。

## 门禁

| 项 | 实测 |
|---|---|
| checkout_lock | 复判后仅陈旧 worktree 误报，无真实并发（#230 已合） |
| B3 | `py_compile` OK；全量 807 tests（本地 2 例 capstone CRLF 漂移，CI LF 通过） |
| B6 | 覆盖 tooling 91.8% / all 91.2%（≥80） |
| B1/B2/C4 | PASS；markdownlint 0 issue；GLOSSARY 17239/17500 |

## CI（PR #255）

- PR 侧：S1 pass、S2 pass、AC-12 冒烟 pass（S3/S4 仅 main 触发）。
- 合并后 main CI：S1/S2/S3/S4 全 `success`。

## 推送通道（追溯补录，非当时实测）

> 本节由 2026-11-17 主线对齐审计补录，**不是合并当时的现场记录**，不得作为"当时已留痕"的证据。
- 事实依据：`git remote -v` 显示 `origin` 的 fetch/push 均为 SSH（`git@github.com:...`）；PR #255 已于
  2026-11-15T10:42:54Z 合并为 `530dda1`；PR 侧与 main CI 均全绿（见上节）。
- 可确认结论：本次交付经受保护分支 PR 流程合并，远端 `origin` 为 SSH 通道；当时是否触发过
  `origin-https` 备通道无客观留痕，**记为证据不可得**，不推测、不补写。
- 防复发：推送通道的现场记录要求已在 `cross-ide-mainline-workflow.md` §4.11 验收④ 与
  `prompts/11-pr-push-review.md` G0 自检固化；后续阶段 11 须在现场填写实际通道与结果。
