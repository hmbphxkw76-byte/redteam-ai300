# attack-rag — 阶段 9 `tdd` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.9 | 7 个测试模块、全目录 125 例；清单 5 模块 102 例；覆盖率 `--target attack-rag` = 1307/1421 = 92.0%（门槛 80%） | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_rag -t . -q` → 125 例 OK；`python scripts/measure_coverage.py --target attack-rag` → 92.0% | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B3 编译无错；B4 严格模式与证据契约用例通过；B6 覆盖率 92.0% ≥ 80%；历史记录 89 例/92.0%（1139/1238） | 符合（回溯） |

**结论：PASS（回溯）**。证据指针：`tests/attack_rag/`、`scripts/measure_coverage.py`；提交 `084d763`。
