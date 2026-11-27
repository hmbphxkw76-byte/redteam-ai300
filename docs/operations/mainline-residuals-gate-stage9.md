# 阶段 9 门禁记录 — `tdd`（残余项收口）

> 变更域：覆盖率清单补登 + 覆盖率测量语义修复 + 记录维护；非技能级留痕，不与 `<skill>-gate-stage*.md` 混用。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 红灯 | 主线 §3.9 | 新增 `tests/shared_tools/test_coverage_targets.py` 首跑 1 失败：缺目标 `capstone-rehearse`、`foothold-traditional`、`osai-exam-orchestrator` | 符合 |
| 绿灯 | 同上 | 补登 2 个目标 + 为 `osai-orchestrator` 声明 `skill` 字段 → 4 例 OK | 符合 |
| 覆盖率 | `measure_coverage` | `foothold-traditional` 165/169 = 97.6%（32 例全过）；`capstone-rehearse` 432/479 = 90.2%；既有目标未漂移（mcp-tool 94.4%、ai-agent 86.1%、report-exam 97.0%） | 符合 |
| 全量回归 | 主线 §2.3 | `python -m unittest discover -s tests -t . -q` → 1699 例 OK（skip 2） | 符合 |

## 红→绿过程中修掉的两个工具缺陷

1. `measure_coverage.ALL_TARGET_ORDER` 是硬编码目标白名单：清单登记后 `--target` 仍不可选，C1 失效。改为「偏好顺序过滤 + 清单余项追加」，顺序稳定且以清单为唯一事实源。
2. `measure()` 用 `importlib.reload` 计入顶层行，reload 不更新依赖方持有的类引用，`isinstance` 断言失效（`foothold-traditional` 首测 1 例假失败）。改为双模式择优：默认 `reload`（保既有口径），失败时用 `purge` 重测；`--target all` 逐目标起子进程聚合，避免同进程互相污染（实测曾出现 3 失败 16 错误）。

## 结论

**PASS**。证据：`scripts/tools_manifest.json`、`scripts/measure_coverage.py`、`tests/shared_tools/test_coverage_targets.py`。
