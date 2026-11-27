# attack-rag — 阶段 7 `domain-modeling` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.7 | `GLOSSARY.md` 已收「RAG」「知识库投毒」「检索层操纵」「AI向量机」「诱饵机」；SKILL.md 未被改写 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_rag -t . -q` → 125 例 OK（清单口径 102 例 / 5 模块） | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B1 五要素术语与技能一致；B2 `python scripts/check_glossary.py` → PASS（66 个废弃术语）；B8 术语均可回溯至 `GLOSSARY.md` | 符合（回溯） |

**结论：PASS（回溯）**。证据指针：`GLOSSARY.md`、`docs/operations/attack-rag-ch5-terms.md`；提交 `084d763`。
