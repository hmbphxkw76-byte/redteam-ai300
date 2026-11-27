# threat-model — 阶段 9 `tdd` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.9 | 5 测试文件共 73 例；manifest 口径 3 模块 53 例；覆盖 AC-01..28，只测外部行为 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/threat_model -t . -q` → 73 例 OK；`measure_coverage.py --target threat-model` → 87.3%（745/853） | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B3 全量通过；B4 证据契约 7 例通过；B6 覆盖率 87.3% ≥80%；B8 覆盖率数字可复跑 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`tests/threat_model/`、`scripts/measure_coverage.py`；提交 `9c5581d`。
