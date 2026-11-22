# ADR-0006 `--no-verify` 例外审计 — foothold-traditional Ch9

分支 `feat/foothold-traditional-ch9`。pre-push 锁阻断（3 worktree 改动共享文件）。
逐 hunk 复核：`git diff origin/main --stat -- GLOSSARY.md scripts/check_token_budget.py scripts/measure_coverage.py .github/workflows/ci.yml tools/collect_evidence.py docs/contracts/collect_evidence.contract.md` → **空**。
即本分支对共享文件零改动，推送不引入任何共享文件分歧，不可能产生冲突。
其余 worktree 状态与 `attack-infra-ch9-push-audit.md` 记录一致（recon-ai-ch6 staged 内容已在 main，union 贡献为零；threat-model-ch10 陈旧 HEAD）。
据 ADR-0006 例外与用户授权采用 `--no-verify`；不触碰任何其它 worktree。
