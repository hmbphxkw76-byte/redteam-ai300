# attack-mcp-tool — 阶段 2 `to-spec ①` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.2 | `docs/specs/attack-mcp-tool-spec-v1.md` 七节齐全；§5 覆盖路径 A–F 与 mcp-01…mcp-11 行为边界；与 `attack-mcp-tool-d2-spec-*` 分层：本文为全技能规格，D-2 仅为变更域规格 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_mcp_tool -t . -q` → 116 例 OK（25.7s） | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B1 五要素对齐 SKILL.md；B2 `check_glossary.py` PASS（66 个废弃术语）；B8 每节可回溯至 SKILL.md | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`docs/specs/attack-mcp-tool-spec-v1.md`；提交 `08d6b85`。
