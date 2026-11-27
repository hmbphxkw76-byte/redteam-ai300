# attack-multi-agent — 阶段 9 `tdd` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.9 | `tests/attack_multi_agent/` 4 个模块、57 例：`units`、`tools`、`runner`、`evidence_contract` | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_multi_agent -t . -q` → Ran 57 tests in 7.494s, OK (skipped=1) | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B3 全量通过；B4 证据契约模块锁定 8 步与 8 次调用；B6 `measure_coverage` → 1054/1179 = 89.4%（≥80） | 替代（回溯） |

- 用例分布：`test_attack_multi_agent_units.py`（模型/定级/步骤/传输/A2A/扫描/证据截图/PyRIT 缝）、`tools`（5 个 dry-run + 实路径退出码）、`runner`（全量 8 步/切片/单 agent/门失败/CLI）、`evidence_contract`（步骤声明、调用数、术语）。
- 覆盖率：`python scripts/measure_coverage.py --target attack-multi-agent` → 总计 1054/1179 = 89.4%，最低模块 `shot.py` 79.3%，最高 `steps.py` 98.4%。
- 跳过项：1 例为真实 PyRIT 环境依赖，按设计跳过并保留人工核实路径。
- 红阶段留痕：历史失败输出未单独归档，判定依据为现有测试模块与本次复跑结果（**未发生**独立的红→绿三轮记录）。

**结论：PASS（回溯）**。证据指针：`tests/attack_multi_agent/`、`scripts/measure_coverage.py`；提交 `a69be85`。
