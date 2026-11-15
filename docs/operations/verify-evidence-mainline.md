# verify-evidence 主线门禁索引

> 依据 `skill-mainline-workflow.md` §2；逐阶段记录见 per-stage 文件（每个 ≤2KB）。B1–B8 定义见 §2.1，此处不重复（C1）。

| 阶段 | 名称 | 结论 | 门禁记录 |
|---|---|---|---|
| 1 | research | PASS（B7/B8） | `docs/research/verify-evidence-canonical.md` §门禁记录 |
| 2 | to-spec① v1 | PASS（B1/B2/B8） | `docs/operations/verify-evidence-gate-stage2.md` |
| 3 | to-spec② v2 | PASS（B1/B2/B6/B7/B8） | `docs/operations/verify-evidence-gate-stage3.md` |
| 4 | to-tickets | PASS（B2/B8） | `docs/operations/verify-evidence-gate-stage4.md` |
| 5 | triage | PASS（B8） | `docs/operations/verify-evidence-gate-stage5.md` |
| 6 | codebase-design | PASS（B2/B7/B8） | `docs/operations/verify-evidence-gate-stage6.md` |
| 7 | domain-modeling | PASS（B1/B2/B8） | `docs/operations/verify-evidence-gate-stage7.md` |
| 8 | implement-spec | PASS（B1–B5/B7/B8） | `docs/operations/verify-evidence-gate-stage8.md` |
| 9 | tdd | PASS（B3/B4/B6/B8） | `docs/operations/verify-evidence-gate-stage9.md` |
| 10 | code-review | PASS（B1–B8） | `docs/operations/verify-evidence-gate-stage10.md` |
| 11 | pr-push-review | PASS（B1–B8） | `docs/operations/verify-evidence-gate-stage11.md` |

- 交付物：v1 = `docs/specs/verify-evidence-spec-v1.md`；v2 = `docs/specs/verify-evidence-spec-v2.md`；规格 issue = #204。
- 隔离：worktree `D:/_verify-evidence_wt` · 分支 `feat/verify-evidence`（ADR-0006）。
