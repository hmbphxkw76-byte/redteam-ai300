## 阶段 9 — tdd（B3/B4/B6/B8）

| 编号 | 检查项 | 实测结果（命令+摘要） | 判定 |
|---|---|---|---|
| B3 | 语法/构建 | `python -m unittest tests.test_attack_supply_chain_seams tests.test_attack_supply_chain_evidence_contract tests.test_validators`→Ran 26, OK | 符合 |
| B4 | 证据契约 | evidence contract 3 tests OK | 符合 |
| B6 | CI/覆盖率 | `measure_coverage.py --target attack-supply-chain --min 80`→总计 200/218=**91.7%** ≥80%；S1 预算检查红为**预存 WIP**（GLOSSARY 8990→16551、workflow 25670→29161 由先前未提交改动膨胀，非本技能产物） | 符合（覆盖率达标；S1 预存债记录，不归本技能） |
| B8 | 可追溯 | 测试断言 AC-01~AC-09/AC-17 外部行为；红→绿记录见测试演进（18→20 用例） | 符合 |

- 新增测试：`tests/test_attack_supply_chain_seams.py`（20 用例）；证据契约沿用既有夹具（3 用例）。
- 红→绿：初始缺 build_args 导出→补 `__init__` 后转绿；ArtPoisonBackend 未覆盖→加 fake art_module 用例覆盖。
- 覆盖率：91.7%（recon 96.2 / poison 97.9 / scan 80.4 / inject 90.9 / evidence 88.9 / workflow 97.4）。
- 不符合项 0（覆盖率达标）；**结论 PASS**（附注：CI S1 预存 WIP 预算债，见上）。
- 复验命令：`python scripts/measure_coverage.py --target attack-supply-chain --min 80`。
