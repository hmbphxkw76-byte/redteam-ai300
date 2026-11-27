# attack-mcp-tool — 阶段 7 `domain-modeling` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.7 | `GLOSSARY.md` 已收「MCP」「工具面」「AI向量机」「证据片段」；「证据三件套」为 SKILL.md 质量门口径（命令+输出+截图），非独立词条；`attack-mcp-tool-terms.md` 提供双向映射 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_mcp_tool -t . -q` → 116 例 OK（25.7s） | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B1 术语与技能五要素一致；B2 `python scripts/check_glossary.py` → PASS（66 个废弃术语）；B8 术语可回溯至 `GLOSSARY.md` 与映射表 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`GLOSSARY.md`、`docs/operations/attack-mcp-tool-terms.md`；提交 `08d6b85`。
