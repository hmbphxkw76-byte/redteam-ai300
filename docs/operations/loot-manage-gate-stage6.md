# loot-manage — 阶段 6 `codebase-design` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.6 | `docs/operations/loot-manage-design.md`：`registry` 核心 + `cli` 薄封装，seam S1 解析/校验、S2 登记、S3 `validate --json` 交接 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/loot_manage -t . -q` → Ran 55 tests，OK | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B7 N/A（本包不引 PyRIT）；B2 用「战利品/登记簿/攻击路径/双通道」；B8 依赖单向 `cli → registry` | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`docs/operations/loot-manage-design.md`、`tools/loot_manage/registry.py`；提交 `0f90d71`。
