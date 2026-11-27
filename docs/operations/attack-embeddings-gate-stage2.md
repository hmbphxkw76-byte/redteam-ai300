# attack-embeddings 阶段 2 `to-spec ①` 门禁记录 · 历史留痕回填

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.2 | `docs/specs/attack-embeddings-spec-v1.md` 6649B，§1–§8 齐全；US-1..US-11 覆盖 emb-01..emb-08 与 §6 质量门；发布 issue #158 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_embeddings -t . -q` → Ran 77, OK | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B1 五要素与 `SKILL.md` 逐项对齐；B2 本文件 0 处废弃术语；B8 §8 seam 提案 S1–S4 与 #158 互链 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`docs/specs/attack-embeddings-spec-v1.md`、issue #158；提交 `8438894`（首落 `5537cd0`）。
