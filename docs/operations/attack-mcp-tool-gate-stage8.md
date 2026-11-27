# attack-mcp-tool — 阶段 8 `implement-spec` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.8 | 实现包 10 个主模块：model/transport/mcp/poison/grade/evidence/shot/steps/runner/cli；Ch7 增量另有 chain/escape/uihost；步骤契约 11 项（mcp-01…mcp-11） | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_mcp_tool -t . -q` → 116 例 OK（25.7s） | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B3 `check_tools_compile.py` → 309 文件、失败 0；B4 严格模式证据；B5 flag 双通道；B7 对象图符合 ADR-0004；B9 静态检索无凭据硬编码 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`tools/attack_mcp_tool/`、`python scripts/check_tools_compile.py`；提交 `08d6b85`。
