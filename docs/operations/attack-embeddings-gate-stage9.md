# attack-embeddings 阶段 9 `tdd` 门禁记录 · 历史留痕回填

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.9 | `tests/attack_embeddings/` 6 个测试文件；全目录实跑 77 例 OK；manifest 口径 4 个测试模块 / 34 例；`python scripts/measure_coverage.py --target attack-embeddings` → 875/979 = 89.4%（14 模块，最低 `fingerprint.py` 78.6%、最高 `runner.py` 98.9%） | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_embeddings -t . -q` → Ran 77, OK（12.4s） | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B3 全绿；B4 `test_attack_embeddings_evidence_contract.py` 断言三件套；B6 89.4% ≥ 80，本地与 CI 同口径；B8 用例可回溯至 AC-1..AC-11 与 AC-C | 符合（回溯） |

**结论：PASS（回溯）**。证据指针：`tests/attack_embeddings/`、`scripts/measure_coverage.py` 输出；提交 `8438894`。
