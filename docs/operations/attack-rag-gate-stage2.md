# attack-rag — 阶段 2 `to-spec ①` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.2 | `docs/specs/attack-rag-spec-v1.md` 七节齐全；§5 行为约束 11 条覆盖三路径与五步闭环；原始规格登记 issue #16 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_rag -t . -q` → 125 例 OK（清单口径 102 例 / 5 模块） | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B1 五要素与 SKILL.md 一致；B2 `python scripts/check_glossary.py` → PASS（66 个废弃术语）；B8 每节可回溯至 SKILL.md | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`docs/specs/attack-rag-spec-v1.md`；提交 `084d763`。
