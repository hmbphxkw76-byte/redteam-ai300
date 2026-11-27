# attack-embeddings 阶段 6 `codebase-design` 门禁记录 · 历史留痕回填

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.6 | `docs/operations/attack-embeddings-design.md`：3 处真实 seam——嵌入后端 S2（`DeterministicEmbedder`/`InMemoryVectorStore`→`EmbeddingHarness`）、探测/打分 S6（`probing.probe_model`）、证据写入器 S3（`EvidenceWriter.emit`）；`attack-embeddings-ch6-design.md` 共 7 seam（S1–S7）与单向依赖图 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_embeddings -t . -q` → Ran 77, OK | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B2 术语一致；B7 设计无 `pyrit.orchestrator`/`*Orchestrator`；B8 新增 S5–S7 附理由并逐条对应 AC-C | 符合（回溯） |

**结论：PASS（回溯）**。证据指针：`docs/operations/attack-embeddings-design.md`、`docs/operations/attack-embeddings-ch6-design.md`；提交 `8438894`。
