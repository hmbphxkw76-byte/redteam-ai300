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
| 9 | tdd | PASS（B3/B4/B6/B8，32 用例 / 92.1%） | `docs/operations/verify-evidence-gate-stage9.md` |
| 10 | code-review | PASS（B1–B8，硬违规清零） | `docs/operations/verify-evidence-code-review.md` |
| 11 | pr-push-review | PASS（PR #227 已合并，CI 全绿） | `docs/operations/verify-evidence-gate-stage11.md` |

- 交付物：v1 = `docs/specs/verify-evidence-spec-v1.md`；v2 = `docs/specs/verify-evidence-spec-v2.md`；规格 issue = #204。
- 隔离：worktree `D:/_verify-evidence_wt` · 分支 `feat/verify-evidence`（ADR-0006）。
- 收口：阶段 11 常规通道被 `checkout_lock.py` 阻断，按钩子例外通道推送（并集已核对），PR #227 合并，main CI `success`。
- 记录收口（15:40）：stage3/8 压缩、stage9/10/11 压至 C4 ≤2KB 并校正时点数字；SKILL 补「修订记录」与机读边界声明；独立复核 5 条部分实现见 `verify-evidence-skill-coverage.md` §8。行为判据未改动。
- 对齐纠偏（21:25）：删除阶段 11 重复预填行；8 处测试路径由 `tests/` 更新为 `tests/shared_tools/`（#268 分组后的现路径），1 处行号引用改为函数名锚点，时点数字不变。
