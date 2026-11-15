# 阶段 9 门禁记录 — `tdd`

- 交付物：`tests/test_verify_evidence.py`（10 → 28 用例，新增 `VerifyEvidenceV2Tests` + `FakeTools`）；`tests/test_report_exam.py` 夹具对齐（AC-09）；覆盖率目标注册
- 红—绿—重构留痕：
  - **红 1**：实现改为按目标键判 `proof-single` 后，`test_duplicate_proof_txt_is_blocking` → `AssertionError: True is not False`（期望阻断，实际放行）。
  - **红 2**：新增 AC 用例首轮 3 错 —— `AC-01`（from_loot 路径 report 为空导致 checks 不等）、`AC-07`（夹具 flag 值与原文不同屏）、`AC-18`（下游以独立 spec 加载，函数对象不同一）。
  - **绿**：修 `_load_module` 注册 `sys.modules`（dataclass 解析 `cls.__module__` 必需）、夹具改用 `OSAI{demo-flag}`、AC-18 改判据行为等价（schema + checks 相等）。
  - **重构**：抽出 `FakeTools`（S-3 替身）、`_artifacts`（产物夹具）、`good_points()`（分值矩阵），删除一次性 `_run` 辅助。

| 编号 | 检查项 | 依据 | 实测结果（命令 + 摘要） | 判定 | 不符合项 | 修正要求 | 复验 | 结论 |
|---|---|---|---|---|---|---|---|---|
| B3 | 语法与构建 | B3 | `python -m py_compile` → OK；`python -m unittest discover -s tests` → `Ran 458 tests ... OK (skipped=2)` | 符合 | — | — | — | PASS |
| B4 | 证据契约 | §6.1 | 本技能无 per-step 片段产出；S2 覆盖即 AC 用例集（28 用例覆盖 AC-01…AC-18） | 符合（SKILL 已声明 S1-only 豁免） | — | — | — | PASS |
| B6 | CI 门禁与覆盖率 | CI-CD §3 S2 | `measure_coverage.py --target verify-evidence --min 80` → 390/404 = **96.5%**（门槛 80） | 符合 | — | — | — | PASS |
| B8 | 可追溯性 | B8 | 用例名以 `test_ACxx_` 前缀对齐 v2 编号；红阶段输出摘录见上 | 符合 | — | — | — | PASS |
| 验收① | 每条 AC 有测试 | §3.9 | AC-01…AC-18 各有 `test_ACxx_*`；AC-19 由覆盖率命令判定；AC-20 由全量套件判定 | 符合 | — | — | — | PASS |
| 验收② | 红阶段有失败输出 | §3.9 | 红 1/红 2 摘录见上（含具体断言消息） | 符合 | — | — | — | PASS |
| 验收③ | 全量通过 | §3.9 | 458 tests OK | 符合 | — | — | — | PASS |
| 验收④ | 覆盖率 ≥80% | §3.9 | 96.5%（阶段 10 修复后 92.3%，仍达标） | 符合 | — | — | — | PASS |
| 验收⑤ | 只测外部行为 | §3.9 | 断言对象为 checks/blocking/missing/pending/退出码；AC-17 替身计数为规格要求的例外 | 符合 | — | — | — | PASS |
| 验收⑥ | 本地与 CI 一致 | §3.9 | CI S2 使用同一 `measure_coverage.py --target all`，已并入 verify-evidence 目标 | 符合 | — | — | — | PASS |

**阶段 10 追加数据**：审查修复后 `unittest discover` → `Ran 521 tests, OK (skipped=2)`；`--target verify-evidence` → 420/455 = 92.3%。

**结论：PASS**（不符合项 0），进入阶段 10。
