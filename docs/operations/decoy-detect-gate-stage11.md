# decoy-detect — 阶段 11 `pr-push-review` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.11 | PR #191（feat decoy-detect，2026-11-15 合入）、#272（AC-3 对齐证据，2026-11-17 合入）；提交 `749dafa` | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/decoy_detect -t . -q` → Ran 59 tests, OK | 符合（回溯） |
| B1–B9 全量汇总 | 主线 §2.1 | B1 PASS / B2 PASS / B3 PASS / B4 PASS / B5 不适用（不含利用）/ B6 PASS（95.3%）/ B7 无 PyRIT / B8 PASS / B9 符合（确定性规则） | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`docs/operations/decoy-detect-alignment-evidence.md`、PR #191、#272；提交 `749dafa`。
