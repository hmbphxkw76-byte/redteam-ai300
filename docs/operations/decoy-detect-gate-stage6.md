# decoy-detect — 阶段 6 `codebase-design` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.6 | `docs/operations/decoy-detect-design.md`：3 处 seam——`features.extract`（输入）、`evidence.EvidenceWriter`（证据）、`listgen.render_markdown`（输出） | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/decoy_detect -t . -q` → Ran 59 tests, OK | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B7 无 PyRIT；模块依赖单向无环，`model.py` 为叶子 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`docs/operations/decoy-detect-design.md`、`tools/decoy_detect/model.py`；提交 `749dafa`。
