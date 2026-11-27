# threat-model — 阶段 3 `to-spec ②` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.3 | 工程规格 v2 六节：`docs/specs/threat-model-spec-v2.md`（7,802B）；AC-01..28 布尔化并指向真实测试模块 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/threat_model -t . -q` → 73 例 OK；v1 未被 v2 取代 | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B6 覆盖率门映射 AC-24（87.3%）；B7 AC-13 断言无 PyRIT/旧版对象；B8 v1→v2 差异逐条可追溯 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`docs/specs/threat-model-spec-v2.md`、`docs/specs/threat-model-spec-v1.md`、issue #324；提交 `9c5581d`。
