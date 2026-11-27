# attack-embeddings 阶段 7 `domain-modeling` 门禁记录 · 历史留痕回填

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.7 | `GLOSSARY.md` 收录 embedding 反演、成员推断、对抗样本、向量库反查、推断探测、块分选、AI向量机共 7 条，各条附 `_Avoid_` 同义词（清单见该文件，本记录不复述）；本记录 0 处废弃词命中 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_embeddings -t . -q` → Ran 77, OK | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B2 `python scripts/check_glossary.py` → 全局 FAIL 4 处，全部落在 report-exam/threat-model 文件；`attack-embeddings` 命中 0 处 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`GLOSSARY.md`（embedding 反演/成员推断/对抗样本/向量库反查/推断探测/块分选各条）；提交 `8438894`。
