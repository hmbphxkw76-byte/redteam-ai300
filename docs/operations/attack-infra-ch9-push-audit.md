# ADR-0006 `--no-verify` 例外审计记录 — attack-infra Ch9

> 分支 `feat/attack-infra-ch9` · 提交 `724a95d` · 日期 2026-11-22
> 例外依据：ADR-0006「逐 hunk 确认并集贡献为零」+ 用户授权「确保数据完整无缺情况下择优执行」。

## 锁报告

pre-push 共享检出锁阻断，列出 3 个 worktree 改动 `GLOSSARY.md` 与
`scripts/check_token_budget.py`。需按各 wt 的 HEAD 复判（项目已知：锁按 origin/main
比较，陈旧 worktree 会误报）。

## 逐 worktree 复判（只读证据）

| worktree | HEAD vs origin/main | 未提交共享改动 | 实质判定 |
|---|---|---|---|
| `D:/_attack-infra-ch9_wt`（本任务） | 基线 56cf6d4 | 已提交到 724a95d | 本次推送内容 |
| `D:/_threat-model-ch10_wt` | 2 behind / 1 ahead | 无 staged / 无 unstaged | 陈旧 HEAD 误报；其共享改动已在其分支提交，经各自 PR 合并 |
| `D:/_recon-ai-ch6_wt` | 31 behind / 3 ahead | staged：GLOSSARY +10/-1、budget +5/-2 | 见下方逐 hunk |

## `_recon-ai-ch6_wt` staged 改动逐 hunk 并集确认

1. `check_token_budget.py`：`"GLOSSARY.md": 17500 → 18000`。
   - origin/main 现值：20500；本分支现值：21500。
   - 该 18000 低于两者，若应用将**回退**预算；本分支 21500 严格更高。
   - 并集贡献 = **0**（本分支已包含更高值；不引入该 worktree 的任何新增内容）。
2. `GLOSSARY.md` 新增 `推断探测 (inference probing)` 与 `块分选 (chunk triage)`。
   - 实测：`git show origin/main:GLOSSARY.md | grep -qF` 两条均命中 → 已在 main。
   - 并集贡献 = **0**（本分支基于 origin/main，已含这两条）。

结论：全部 flagged 共享文件的并集贡献为 0；本分支内容是严格超集
（cap 21500 > 20500 > 18000，术语齐全）。无数据丢失、无内容冲突。

## 推送决定

依 ADR-0006 例外与用户授权，采用 `--no-verify` 推送本分支；不触碰任何其它 worktree
的暂存区或工作树，不改写 main，不合并任何并发会话内容。推送后 `origin/main` 与
本分支的合并仍走受保护 PR 正常流程。

## 复验命令（供审计复核）

```
git -C D:/_recon-ai-ch6_wt status --short -- GLOSSARY.md scripts/check_token_budget.py
git show origin/main:scripts/check_token_budget.py | grep '"GLOSSARY.md":'
git show origin/main:GLOSSARY.md | grep -qF '推断探测 (inference probing)' && echo present
git show origin/main:GLOSSARY.md | grep -qF '块分选 (chunk triage)' && echo present
```
