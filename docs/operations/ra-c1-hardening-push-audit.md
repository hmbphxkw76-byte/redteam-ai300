# ADR-0006 `--no-verify` 审计 — recon-ai Ch9 C1 加固
分支 `feat/recon-ai-c1-hardening`（基线 origin/main f93b151）。
`git diff origin/main --stat -- GLOSSARY.md scripts/check_token_budget.py scripts/measure_coverage.py scripts/tools_manifest.json .github/workflows/ci.yml tools/collect_evidence.py docs/contracts/collect_evidence.contract.md` → 空：共享六项零 delta。
既有判据 `git diff origin/main -- tools/recon_ai/probes.py tools/recon_ai/policy.py tools/recon_ai/model.py tools/recon_ai/inventory.py tools/recon_ai/runner.py` → 空：STEP_SPECS=7、MAX_ACTIVE_PORTS=8、七字段契约零改动；不新增 step_id。
覆盖率脚本复用 `measure_coverage.measure()`，不改共享 manifest/tracer。
据 ADR-0006 例外与用户授权采用 `--no-verify`；不触碰其它 worktree。
