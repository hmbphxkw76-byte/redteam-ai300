## 阶段 9 — tdd（B3/B4/B6/B8）

- 交付物：`tests/test_verify_evidence.py`（10→32 用例）、`tests/test_report_exam.py` 夹具对齐（AC-09）、覆盖率目标注册。
- 红→绿→重构：红 1 `test_duplicate_proof_txt_is_blocking` → `AssertionError: True is not False`（按目标键判 proof 后旧夹具失配）；红 2 新增 AC 用例首轮 3 错（AC-01 from_loot 的 report 为空 / AC-07 flag 不同屏 / AC-18 独立加载致函数不同一）。绿：注册 `sys.modules`、夹具改 `OSAI{demo-flag}`、AC-18 改判行为等价。重构：抽 `FakeTools`/`_artifacts`/`good_points()`，删一次性 `_run`。

| 编号 | 判定 | 证据（命令 + 摘要） |
|---|---|---|
| B3 | 符合 | `py_compile` OK；全量 `unittest discover` 458 tests OK（阶段 11 复跑 578 tests OK） |
| B4 | 符合（S1-only 豁免） | 无 per-step 片段产出；AC 用例集覆盖 AC-01…18 |
| B6 | 符合 | `measure_coverage.py --target verify-evidence --min 80`：阶段 9 时点 390/404=96.5%；交付态 488/530=**92.1%**（均 ≥80） |
| B8 | 符合 | 用例名 `test_ACxx_` 对齐 v2 编号；红阶段输出见上 |
| 验收① | 符合 | AC-01…18 各有 `test_ACxx_*`；AC-19 由覆盖率命令、AC-20 由全量套件判定 |
| 验收② | 符合 | 红 1 / 红 2 含具体断言消息 |
| 验收③ | 符合 | 全量 unittest 0 失败 0 错误 |
| 验收④ | 符合 | 覆盖率 92.1% ≥80%（时点标注，避免记录过期） |
| 验收⑤ | 符合 | 断言 checks/blocking/missing/pending/退出码；AC-17 替身计数为规格例外 |
| 验收⑥ | 符合 | CI S2 用同一 `measure_coverage.py --target all`，已含 verify-evidence 目标 |

- 不符合项 0；**结论 PASS**。复验 `python -m unittest tests.test_verify_evidence && python scripts/measure_coverage.py --target verify-evidence --min 80`。
