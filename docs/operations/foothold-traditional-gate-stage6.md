# foothold-traditional — 阶段 6 `codebase-design` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.6 | 4 模块职责表：`ch9_model` 五值类型、`ch9_entry` 两步判据、`ch9_evidence` 参数组装与发射、`ch9_runner` 编排 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/foothold_traditional -t . -q` → 32 例 OK | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B2 依赖单向 `runner→{entry,evidence}→model`，`model` 零项目内导入；B7 无 `pyrit.*`/Orchestrator；seam 3 个：`ctx.command.run`（唯一执行注入）、`attach` 回调、`out_dir/target` 上下文参数；证据出口仍为 `tools/collect_evidence.py` | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`tools/foothold_traditional/ch9_runner.py`、`ch9_evidence.py#build_evidence_argv`；提交 `6bdedce`。
