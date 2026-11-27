# attack-mcp-tool — 阶段 6 `codebase-design` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.6 | 等价设计记录 `docs/operations/attack-mcp-tool-design.md`、`attack-mcp-tool-ch7-gap-design.md`；真实 seam：`Runtime` 注入 client/writer/capture/server，替身 `FakeHttpClient`、`RecordingWriter`、`NullCapture`；Ch7 增 `UiHostClient` | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_mcp_tool -t . -q` → 116 例 OK（25.7s） | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B2 术语 PASS；B7 无 0.x 编排器；B8 设计与实现互指；seam 数与设计记录一致（三缝 + 1 UI 缝，server 注入由 `Runtime` 承载） | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`docs/operations/attack-mcp-tool-design.md`、`tools/attack_mcp_tool/runner.py`；提交 `08d6b85`。
