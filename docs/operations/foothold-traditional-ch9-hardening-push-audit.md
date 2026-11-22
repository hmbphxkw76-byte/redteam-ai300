# ADR-0006 `--no-verify` 审计 — foothold-traditional Ch9 加固
分支 `feat/foothold-traditional-ch9-hardening`（基线 origin/main 1285965）。
`git diff origin/main --stat -- GLOSSARY.md scripts/check_token_budget.py scripts/measure_coverage.py scripts/tools_manifest.json .github/workflows/ci.yml tools/collect_evidence.py docs/contracts/collect_evidence.contract.md` → 空：本分支对共享六项零 delta，推送不引入共享文件分歧。
覆盖率脚本 `scripts/verify_ch9_ft_coverage.py` 复用 `measure_coverage.measure()`，不改共享 `measure_coverage.py`/`tools_manifest.json`（两文件在其它 worktree 有 staged 改动）。
据 ADR-0006 例外与用户授权采用 `--no-verify`；不触碰任何其它 worktree。
