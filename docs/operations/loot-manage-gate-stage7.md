# loot-manage — 阶段 7 `domain-modeling` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.7 | `GLOSSARY.md` §战利品管理（L195–212）收「战利品/战利品登记簿/攻击路径/问答取证」；「凭据指纹」见 L361 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/loot_manage -t . -q` → Ran 55 tests，OK | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B2 `check_glossary.py` PASS（66 废弃术语）；「攻击路径」与「攻击链」分列，未混用 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`GLOSSARY.md` §战利品管理、`docs/operations/domain.md`；提交 `0f90d71`。
