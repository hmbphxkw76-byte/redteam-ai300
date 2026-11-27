# threat-model — 阶段 6 `codebase-design` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.6 | 设计记录 `docs/operations/threat-model-design.md`、`threat-model-ch10-design.md`；真实 seam：分类器 `classify.enrich`、评分器 `score.score_and_rank`、信任边界 `boundaries.trust_boundaries/shortest_paths`、攻击图渲染 `graph.build_graph`+`render.render`、假设登记册 `assumptions.to_register` | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/threat_model -t . -q` → 73 例 OK | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B2 设计区分「信任区≠信任边界」；B7 依赖单向无环、无 PyRIT 对象图（矩阵 ⑬）；B8 每接口标 AC 编号 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`docs/operations/threat-model-design.md`、`docs/operations/threat-model-ch10-design.md`；提交 `9c5581d`。
