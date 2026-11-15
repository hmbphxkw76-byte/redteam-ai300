# attack-supply-chain 主线门禁索引

> 依据 `skill-mainline-workflow.md` §2；逐阶段记录见 per-stage 文件（每个 ≤2KB）。完整基线定义见 §2.1，此处不重复（C1）。

| 阶段 | 名称 | 结论 | 门禁记录 |
|---|---|---|---|
| 1 | research | PASS（B7/B8/B9） | `docs/research/attack-supply-chain-canonical.md` §6 |
| 2 | to-spec① v1 | PASS（B1/B2/B8） | `docs/operations/attack-supply-chain-gate-stage2.md` |
| 3 | to-spec② v2 | PASS（B1/B2/B6/B7/B8） | `docs/operations/attack-supply-chain-gate-stage3.md` |
| 4 | to-tickets | PASS（B2/B8） | `docs/operations/attack-supply-chain-gate-stage4.md` |
| 5 | triage | PASS（B8） | `docs/operations/attack-supply-chain-gate-stage5.md` |
| 6 | codebase-design | PASS（B2/B7/B8） | `docs/operations/attack-supply-chain-gate-stage6.md` |
| 7 | domain-modeling | PASS（B1/B2/B8） | `docs/operations/attack-supply-chain-gate-stage7.md` |
| 8 | implement-spec | PASS（B1-B5/B7-B9） | `docs/operations/attack-supply-chain-gate-stage8.md` |
| 9 | tdd | PASS（B3/B4/B6/B8，覆盖 91.7%） | `docs/operations/attack-supply-chain-gate-stage9.md` |
| 10 | code-review | PASS（B1-B9，硬违规 0） | `docs/operations/attack-supply-chain-gate-stage10.md` |
| 11 | pr-push-review | **BLOCKED**（预存工作树 WIP，未推送） | `docs/operations/attack-supply-chain-gate-stage11.md` |

- 交付物：v1 = `docs/specs/attack-supply-chain-spec-v1.md`；v2 = `docs/specs/attack-supply-chain-spec-v2.md`；规格 issue = #161。
