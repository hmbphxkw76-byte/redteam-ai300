# ADR-0006 `--no-verify` 例外审计 — foothold-traditional Ch9

分支 `feat/foothold-traditional-ch9`。pre-push 锁阻断（3 worktree 改动共享文件）。
逐 hunk 复核：`git diff origin/main --stat -- GLOSSARY.md scripts/check_token_budget.py scripts/measure_coverage.py .github/workflows/ci.yml tools/collect_evidence.py docs/contracts/collect_evidence.contract.md` → **空**。
即本分支对共享文件零改动，推送不引入任何共享文件分歧，不可能产生冲突。
其余 worktree 状态与 `attack-infra-ch9-push-audit.md` 记录一致（recon-ai-ch6 staged 内容已在 main，union 贡献为零；threat-model-ch10 陈旧 HEAD）。
据 ADR-0006 例外与用户授权采用 `--no-verify`；不触碰任何其它 worktree。

## CI 复验记录
首轮 PR 事件 S1「契约 PR 变更清单门禁」失败：PR 正文含 `collect_evidence` + `契约` 关键词触发启发式判定，但缺 `## 契约变更清单` 段。已在 PR 正文补齐四子项（变更元素/before→after/受影响/兼容），本地 `check_contract_manifest.py --pr-body --changed` PASS。`gh run rerun` 会复用旧 PR body，故以本提交触发新事件复验。
