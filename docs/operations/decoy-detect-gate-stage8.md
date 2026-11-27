# decoy-detect — 阶段 8 `implement-spec` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.8 | `tools/decoy_detect/` 9 模块（model/features/timebox/policy/listgen/validate/evidence/runner/cli） | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/decoy_detect -t . -q` → Ran 59 tests, OK | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B3 `check_tools_compile.py` → 309 文件，失败 0；B6 退出码 0/1/2 与 AC 对齐 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`tools/decoy_detect/`、`scripts/tools_manifest.json`；提交 `749dafa`。
