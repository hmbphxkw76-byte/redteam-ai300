# 阶段 11 门禁记录 — `pr-push-review`（残余项收口）

> 变更域：`8d17a5e`（清单补登与测量修复）+ `253c2ac`（记录与阶段 9 留痕）；远端基线 `3bf31b7`。

| 检查项 | 依据 | 实测 | 判定 |
|---|---|---|---|
| B3 编译/测试 | 主线 §2.1 | `check_tools_compile` 309 文件 0 失败；全量 1699 例 OK（skip 2） | 符合 |
| B4 证据契约 | 同上 | `check_evidence_contract` PASS（4 适配器） | 符合 |
| B6 覆盖率 | 同上 | `--target all --min 80` → 23 目标 90.1%，退出 0 | 符合 |
| B2 术语/预算 | §1.3 | `check_glossary` PASS；`check_token_budget --check` PASS；lint 6 文件 0 issue | 符合 |
| 契约清单/消费者 | 同上 | `check_contract_manifest --check`、`check_contract_consumers --check` 均 PASS | 符合 |
| 双轴评审 | §3.11 | Standards 2 项硬违规（条款归属错引、AC-16 与实测冲突）已修；Spec 3 项（阶段 9/11 未落、压缩删信息、测量模式波及全量）已修 | 符合 |
| 推送 | §3.11 | SSH `3bf31b7..253c2ac` 一次成功，`pre-push-verify` 全 OK | 符合 |
| CI S1–S4 | 同上 | 运行 `45936199230`：S1/S2/S3/S4 全 success | 符合 |

**结论：PASS**。证据：`tests/shared_tools/test_coverage_targets.py`、`scripts/measure_coverage.py`、`scripts/tools_manifest.json`。

## 附：本轮修正的两个自身缺陷

1. 评审前 `--target all` 出现 3 失败 16 错误（同进程清缓存导致跨目标污染），改为逐目标子进程聚合。
2. 「两份记录超 2KB」属 CRLF 原始字节误判（LF 口径为 1,997B / 1,999B）。已还原改写，并新增 `tests/shared_tools/test_gate_record_budget.py` 按 LF 口径守卫全部 214 份。
