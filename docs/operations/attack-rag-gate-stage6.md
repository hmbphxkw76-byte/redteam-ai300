# attack-rag — 阶段 6 `codebase-design` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.6 | `docs/operations/attack-rag-design.md` v1.1；真实 seam 两处：模型/嵌入后端 `RagBackend`、写入通道 `IngestChannel`；检索探针与投毒为纯函数，证据写入委托共享工具非新 seam | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_rag -t . -q` → 125 例 OK（清单口径 102 例 / 5 模块） | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B7 依赖单向无环、库模块无顶层 PyRIT 导入；B9 碰撞/越权不走 PyRIT 原语；B4 证据收口路径唯一 | 符合（回溯） |

**结论：PASS（回溯）**。证据指针：`docs/operations/attack-rag-design.md`、`tools/attack_rag/`（18 个清单模块）；提交 `084d763`。
