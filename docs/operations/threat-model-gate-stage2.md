# threat-model — 阶段 2 `to-spec ①` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.2 | 行为规格 v1 七节：`docs/specs/threat-model-spec-v1.md`（4,781B）；对应 issue #159、Ch10 v1 #324 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/threat_model -t . -q` → 73 例 OK（含 manifest 53 例） | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B2 术语用「威胁模型/信任边界/优先级攻击图」等规范词；B8 七节逐条可溯源至 SKILL.md | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`docs/specs/threat-model-spec-v1.md`、`skills/threat-model/SKILL.md`、issue #159；提交 `9c5581d`。
