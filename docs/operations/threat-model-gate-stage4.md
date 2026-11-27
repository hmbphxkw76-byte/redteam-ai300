# threat-model — 阶段 4 `to-tickets` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.4 | 父工单 #185（Ch10 为 #325）+ 子工单；需求追踪矩阵 `docs/operations/threat-model-ch10-rtm.md` 覆盖 M1–M18，无「未落地」项 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/threat_model -t . -q` → 73 例 OK | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B2 工单标题用规范术语；B8 每张工单含验收条件与验证命令、阻塞边可在 tracker 查询 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`docs/operations/threat-model-ch10-rtm.md`、issue #185、#325；提交 `9c5581d`。
