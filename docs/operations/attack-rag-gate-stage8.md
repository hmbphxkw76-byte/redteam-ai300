# attack-rag — 阶段 8 `implement-spec` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.8 | `tools/attack_rag/` 29 个 .py，其中覆盖率清单 18 模块；主链 `rag-00..05`、Ch5 `rag-06..09`、Ch11 `rag-10`；等价记录 `attack-rag-verification.md` | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_rag -t . -q` → 125 例 OK（清单口径 102 例 / 5 模块） | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B3 `python -m py_compile tools/attack_rag/*.py tools/collect_evidence.py tools/inject_kb.py` → 无错；B4 严格模式证据；B5 flag 双通道 | 符合（回溯） |

**结论：PASS（回溯）**。证据指针：`tools/attack_rag/`、`tools/collect_evidence.py`、`tools/inject_kb.py`；提交 `084d763`。
