# ADR-0006 `--no-verify` 审计 — loot-manage Ch9
分支 `feat/loot-manage-ch9`。`git diff origin/main --stat -- <shared六项>` 为空 → 本分支共享文件零 delta，推送不引入分歧。其余 worktree 状态见前序审计。据例外与用户授权采用 `--no-verify`，不触碰其它 worktree。
