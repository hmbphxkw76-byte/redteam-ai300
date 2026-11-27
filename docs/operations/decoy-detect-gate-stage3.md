# decoy-detect — 阶段 3 `to-spec ②` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.3 | `docs/specs/decoy-detect-spec-v2.md`：v1→v2 差异 + AC1–AC15，7.1KB | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/decoy_detect -t . -q` → Ran 59 tests, OK | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B1 规格独立成版；B2 术语沿用 v1；B3 AC 全部映射到真实测试 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`docs/specs/decoy-detect-spec-v2.md`、`tests/decoy_detect/`；提交 `749dafa`。
