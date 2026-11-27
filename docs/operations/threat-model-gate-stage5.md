# threat-model — 阶段 5 `triage` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.5 | 工单标签 `ready-for-agent`（issue #85、#159、#185、#324、#325）；agent brief 含目标/输入/约束/验收/验证命令 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/threat_model -t . -q` → 73 例 OK | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B8 标签字符串与 `docs/operations/triage-labels.md` 五角色映射一致；`ready-for-agent` 工单均含 brief | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：issue #85、#185、#324（标签与 brief）；提交 `9c5581d`。
