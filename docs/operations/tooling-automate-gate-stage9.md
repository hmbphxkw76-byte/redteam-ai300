# 阶段 9 门禁记录 — `tdd`

- 交付：`test_tooling_tdd_contract.py`（6 例，AC-08/10/11/13/14/16）；`cli.main` 增可注入 `runner`；覆盖纳入新用例
- 全量：`unittest discover -s tests` → Ran 650，OK（skip 2）；覆盖 212/231 = 91.8%（门限 80）

## 红→绿→重构

| 轮次 | 命令 | 摘要 |
|---|---|---|
| 红 | `unittest test_tooling_tdd_contract -v` | 6 例 errors=1：`public_entrypoint` → `TypeError: main() got unexpected keyword 'runner'` |
| 绿 | `cli.main(argv, runner=None)` 转发 `run_plan` | 6 例 OK |
| 重构 | 复跑编译+全量+覆盖 | 编译 OK；650 OK；91.8%（cli.py 70→86.7%） |

- 偏差闭环：红阶段暴露 `main()` 缺注入点，与 AC-08 不符；最小改动转绿，断言未放宽。

## AC→测试对位（20/20）

| AC | 测试 | AC | 测试 |
|---|---|---|---|
| 01 | seven_fields_required / load_ok | 11 | summary_consumable |
| 02 | manual_classification | 12 | naming_convention_passthrough |
| 03 | coverage_denominator / empty | 13 | exit_codes_three_state / exit_zero / exit_one |
| 04 | ordered_by_step / dry_run | 14 | usage_error_no_passed / exit_two |
| 05 | strict_evidence_argv / failure | 15 | no_third_party（S1） |
| 06 | build_argv_dispatch / no_gate_redefinition | 16 | no_gate_redefinition（S2） |
| 07 | step_namespace / step_conflict | 17 | readonly_no_side_effects |
| 08 | public_entrypoint / s1_entry_injectable | 18 | no_pyrit_import（S1） |
| 09 | markdown_summary | 19 | 全量 650 OK |
| 10 | reuse_declaration_every_row | 20 | 覆盖 91.8% ≥ 80 |

## 门禁

| 编号 | 检查 | 实测 | 结论 |
|---|---|---|---|
| B3 | 语法构建 | `py_compile` OK；650 OK | PASS |
| B4 | 证据契约 | strict_evidence_argv + naming 断言三件套透传 | PASS |
| B6 | CI | S1：validate/glossary/budget 全 PASS；S2：91.8% | PASS |
| B8 | 可追溯 | AC→测试 20/20；红绿重构留痕 | PASS |

**结论：PASS**（不符合项 0），进入阶段 10（`code-review`）。
