# foothold-traditional — 阶段 9 `tdd` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.9 | `tests/foothold_traditional/` 3 模块（`ch9` 8 例、`ch9_hardening` 21 例、`evidence_contract` 3 例）；`python -m unittest discover -s tests/foothold_traditional -t . -q` → 32 例 OK | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/foothold_traditional -t . -q` → 32 例 OK | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B3 全量通过；B4 证据契约断言 8 步各一次 `--step`；B6 32 例 OK；`coverage_targets` 未登记该技能，无覆盖率数值（建议后续补登记）；PR #377 的 97.6% 由独立脚本自测，非 `--target` 口径，不采信 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`tests/foothold_traditional/test_foothold_traditional_evidence_contract.py`；提交 `6bdedce`。
