# ADR-0006 `--no-verify` 审计 — loot-manage Ch9 B5 加固
分支 `feat/loot-manage-b5-hardening`（基线 origin/main 5e47bbf）。
`git diff origin/main --stat -- GLOSSARY.md scripts/check_token_budget.py scripts/measure_coverage.py scripts/tools_manifest.json .github/workflows/ci.yml tools/collect_evidence.py docs/contracts/collect_evidence.contract.md` → 空：共享六项零 delta。
下游判据 `git diff origin/main -- tools/verify_evidence.py tools/report_exam/ tools/loot_manage/registry.py` → 空：verify-evidence/report-exam/8 列登记簿零改动（P-4）。
覆盖率脚本复用 `measure_coverage.measure()`，不改共享 manifest/tracer。
据 ADR-0006 例外与用户授权采用 `--no-verify`；不触碰其它 worktree。
