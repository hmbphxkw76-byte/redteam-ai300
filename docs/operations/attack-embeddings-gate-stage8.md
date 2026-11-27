# attack-embeddings 阶段 8 `implement-spec` 门禁记录 · 历史留痕回填

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.8 | `tools/attack_embeddings/` 16 个模块文件：manifest 纳管 14 个（model、attacks、harness、runner、evidence、cli、exporter、fingerprint、probing、triage、slotfill、beamsearch、decision、envelope）+ `entry.py`、`live.py`；`python scripts/check_tools_compile.py` → 309 个文件，失败 0 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_embeddings -t . -q` → Ran 77, OK | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B3 编译 0 失败；B4 各步 `collect_evidence.py --strict`；B5 无硬编码凭据；B7 仅 emb-07 走 PyRIT；B9 取矩阵 ⑨ 组合 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`tools/attack_embeddings/`、`scripts/check_tools_compile.py` 输出；提交 `8438894`。
