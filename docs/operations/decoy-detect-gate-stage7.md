# decoy-detect — 阶段 7 `domain-modeling` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.7 | `GLOSSARY.md`：诱饵机、诱饵判定清单、三维度特征、时间盒、计分目标；`_Avoid_` 词齐全 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/decoy_detect -t . -q` → Ran 59 tests, OK | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B2 `python scripts/check_glossary.py` → PASS（66 废弃术语） | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`GLOSSARY.md#诱饵机`、`GLOSSARY.md#诱饵判定清单`；提交 `749dafa`。
