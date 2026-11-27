# attack-mcp-tool — 阶段 3 `to-spec ②` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.3 | `docs/specs/attack-mcp-tool-spec-v2.md` §1 AC-01…AC-25 全布尔；§3 门禁映射 8 行均指向真实测试模块或脚本；v1 全文未改；D-2 规格仍只覆盖生命周期变更域 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_mcp_tool -t . -q` → 116 例 OK（25.7s） | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B1/B2 术语与五要素一致；B6 覆盖率 94.4%（1634/1731）；B7 无 0.x 编排器对象；B8 AC 可回溯至 SKILL.md 与真实测试 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`docs/specs/attack-mcp-tool-spec-v2.md`；提交 `08d6b85`。
