# ADR-0006 `--no-verify` 审计 — threat-model Ch9 C3 加固
分支 `feat/tm-c3-hardening`（基线 origin/main 7abd003）。
`git diff origin/main --stat -- GLOSSARY.md scripts/check_token_budget.py scripts/measure_coverage.py scripts/tools_manifest.json .github/workflows/ci.yml tools/collect_evidence.py docs/contracts/collect_evidence.contract.md` → 空：共享六项零 delta。
既有语义 `git diff origin/main -- tools/threat_model/decoy.py graph.py boundaries.py model.py score.py` → 空：诱饵判定与优先级图语义零改动。
覆盖率脚本复用 `measure_coverage.measure()`，不改共享 manifest/tracer。
据 ADR-0006 例外与用户授权采用 `--no-verify`；不触碰其它 worktree。
