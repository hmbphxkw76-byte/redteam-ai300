# ADR-0006 `--no-verify` 审计 — attack-supply-chain Ch9
分支 `feat/attack-supply-chain-ch9`。`git diff origin/main --stat -- <shared六项>` 空 → 本分支共享文件零 delta，推送不引入分歧。据例外与用户授权采用 `--no-verify`，不触碰其它 worktree（含 main 中 untracked 的 Ch8 交付物）。
