# attack-mcp-tool — 阶段 9 `tdd` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.9 | manifest 口径 116 例 / 6 模块；全目录实跑 116 例 OK（25.7s）；覆盖率 94.4%（1634/1731，门槛 90%）；历史 `-tests.md` 87.0%（1262/1451）为早期口径 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_mcp_tool -t . -q` → 116 例 OK（25.7s） | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B3 全绿；B4 证据契约覆盖三件套与 AI 日志；B6 94.4% ≥ 90%；B8 AC 与测试可追溯；Windows stderr 有 `ConnectionAbortedError` 噪声，退出码 0 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`tests/attack_mcp_tool/`、`docs/operations/attack-mcp-tool-tests.md`；提交 `08d6b85`。两种用例口径不同但同为 116 例。
