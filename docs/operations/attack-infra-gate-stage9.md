# attack-infra — 阶段 9 `tdd` 门禁记录

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.9 | `tests/attack_infra/` 7 个用例模块、151 条用例；负例覆盖 SPA 回退、匿名 401、本机回显、缺 AI 日志 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_infra -t . -q` → Ran 151 tests in 3.862s, OK | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B6 `python scripts/measure_coverage.py --target attack-infra` → 1957/2156 = 90.8%（门槛 80%） | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`tests/attack_infra/`、`tests/attack_infra/test_attack_infra_evidence_contract.py`；提交 `8313fb1`。
