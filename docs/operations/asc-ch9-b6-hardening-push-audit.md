# ADR-0006 `--no-verify` 审计 — attack-supply-chain Ch9 B6 加固
分支 `feat/asc-ch9-b6-hardening`（基线 origin/main 1285965）。
`git diff origin/main --stat -- GLOSSARY.md scripts/check_token_budget.py scripts/measure_coverage.py scripts/tools_manifest.json .github/workflows/ci.yml tools/collect_evidence.py docs/contracts/collect_evidence.contract.md` → 空：本分支对共享六项零 delta。
覆盖率脚本复用 `measure_coverage.measure()`，不改共享 `measure_coverage.py`/`tools_manifest.json`（两文件在其它 worktree 有 staged 改动）。
Ch8 既有投毒模块 `git diff origin/main -- tools/attack_supply_chain/ch8_*.py tools/attack_supply_chain/poison_engine.py` → 空：零回归（P-4）。
据 ADR-0006 例外与用户授权采用 `--no-verify`；不触碰其它 worktree。
