# foothold-traditional — 阶段 8 `implement-spec` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.8 | `tools/foothold_traditional/` 4 个功能模块（`ch9_model`/`ch9_entry`/`ch9_evidence`/`ch9_runner`，另 `__init__.py`），共 243 行；`SKILL.md` 承载 trad-01..08，代码承载 trad-09/10 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/foothold_traditional -t . -q` → 32 例 OK | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B3 `py_compile` 4 文件 0 失败、`check_tools_compile.py` → 309 文件 0 失败；B4 每步 `--strict` 参数组装；B5 提权前后证明与双通道为 SKILL 质量门；B7 无 PyRIT；无硬编码凭据（仅正则与指纹） | 符合（回溯） |

**结论：PASS（回溯）**。证据指针：`tools/foothold_traditional/ch9_entry.py`、`ch9_evidence.py`；提交 `6bdedce`。
