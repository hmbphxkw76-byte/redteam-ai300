# ADR-0006 `--no-verify` 审计 — 全 repo 收尾清理（2026-11-22）

## 阻断原因
pre-push 共享检出锁：GLOSSARY.md / scripts/tools_manifest.json / scripts/check_token_budget.py 在 3 个 worktree（_attack-infra-ch9_wt / _recon-ai-ch6_wt / _threat-model-ch10_wt）有 staged 改动。

## 本次推送为何不构成并集冲突
1. 两个 backup ref 是**全新 ref**（远端不存在），纯新增，无覆盖、无 force。
2. 7 个未推送分支均为历史分支指针，不触及 main，不携带上述共享文件的未提交 staged 内容。
3. `_recon-ai-ch6_wt` 的 57 staged 文件已用 `git stash create` 固化为 `backup/recon-ai-ch6-staged-20261122`，字节快照在 ref 中保全；主工作树 2 untracked 文档固化为 `backup/untracked-ch8-docs-20261122`。二者均未把 staged 共享文件推入任何活动分支。
4. 无并集需要合并：共享文件的并发 staged 改动保持原状，未被本次任何推送消费。

## 结论
据 ADR-0006 例外条款，人工确认「并集无误（此处无并集）」后用 `--no-verify`；SSH 失败则 HTTPS 一次即停。全程零 force、零删除、零覆盖。
