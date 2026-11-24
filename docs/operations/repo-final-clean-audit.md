# 仓库最终清理审计

> **日期** 2026-11-24 · **性质** 最终收口留痕
> **前置** `docs/operations/repo-cleanup-invalidation-audit.md`（S0 清理）与本文件；本轮只删除可证明无独有提交的引用与冗余 tag，保留全部唯一副本。

## 1. 删除前验证方法

对每个远端分支 `b` 计算 `git rev-list origin/b ^main ^refs/remotes/origin/<其他所有分支>`：
- `unique=0`：该分支所有提交均可由 main 或其他远端分支恢复，判为可删；
- `unique>0`：含不可恢复提交，判为保留。

对 3 个未合并 CLOSED PR 分支（`feat/recon-ai-ch6` #312、`archive/mainline-wip-20261115` #201、`fix/report-image-path-relative` #140）同样按独有提交判定。首次计算误用 `refs/remotes/or/` 前缀并输出杂散哈希，已用 `origin/` 重算后作为唯一判据。

## 2. 删除项与证据

| 项目 | 证据 | 结果 |
|---|---|---|
| `docs/ai-range-target-selection` | `unique=0`，全部提交可由 main 恢复 | 远端删除成功 |
| `feat/attack-ma-regression-verify` | `unique=0` | 远端删除成功 |
| `feat/recon-ai-ch6` | `unique=0`（#312 未合并但其提交已由其他分支/main 覆盖） | 远端删除成功 |
| tag `backup/attack-rag-archive-20261115` | 全部提交已被远端引用包含；远端无该 tag | 本地 `git tag -d` 成功 |
| tag `backup/ch2-pre-merge-20261122-004518` | 同上 | 本地 `git tag -d` 成功 |
| 3 条 `origin-https/*` 陈旧跟踪引用 | 对应远端分支已删 | `git branch -rd` 清理成功 |

GitHub API 实测远端分支由 14 降至 **11**：`main`、4 个 `backup/*`、`feat/a2a-ch4-alignment`、3 个 `feat/verify-evidence-*`、`fix/report-image-path-relative`、`wip/archive-orphans`。

## 3. 保留项（BLOCKED / 唯一副本）

远端保留 10 个非 main 分支，逐条独有提交数：`backup/attack-infra-pre-rebase` 4、`backup/attack-mcp-tool-pre-rebase` 8、`backup/recon-ai-ch6-staged-20261122` 2、`backup/untracked-ch8-docs-20261122` 1、`feat/a2a-ch4-alignment` 1、`feat/verify-evidence-225` 2、`feat/verify-evidence-dual` 3、`feat/verify-evidence-records` 2、`fix/report-image-path-relative` 3、`wip/archive-orphans` 3。

本地保留 15 个含 1–8 个独有提交的 `backup/*`（唯一副本，非债务），4 个已计入远端独有的 `backup/*`，3 个 verify-evidence BLOCKED 分支，`feat/a2a-ch4-alignment`，以及 main。`.workbuddy/`、hooks、reflog 未动。

## 4. 对象清理

执行标准 `git gc`（**未**使用 `--prune=now`）：loose objects `324 → 0`，packs `4 → 2`，`in-pack 3525 → 3849`，`size-pack 6143 → 6120 KB`。近期不可达对象按标准策略保留，未强制销毁恢复路径。

## 5. 收尾验证

- 本地 main 与 `origin/main` 同为 `2686bfe0`；工作树 clean；worktree 仅 1 个。
- 远端 11 分支与本地跟踪引用一致；两份 Ch8 文档 SHA-256 与清理前一致（`27867f1a…1503c0d`、`79bf79af…a87d518d`）。
- 未 force push、未 `--prune=now`、未删除任何唯一副本。

结论：仓库已按"数据完整无缺"前提收口；剩余分支均为有意归档或含独有提交，不构成可安全清除的历史债务。
