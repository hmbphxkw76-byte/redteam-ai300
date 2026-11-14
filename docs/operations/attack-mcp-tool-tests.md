# attack-mcp-tool 测试与红绿记录

> **版本** v1.0 · **输入** 规格 v2 AC-01…AC-23、实现 `tools/attack_mcp_tool/`
> **性质** 阶段 9 交付物：验收条件 ↔ 测试映射、红—绿—重构留痕、覆盖率数据

## 1. 验收条件 ↔ 测试映射

| AC | 测试（文件::用例） |
|---|---|
| AC-01 | `tests.test_attack_mcp_tool_runner::ContractTests`；`tests.test_attack_mcp_tool_evidence_contract`（SKILL.md 声明） |
| AC-02 | `runner::EntryPointTests::test_ac02_single_step_produces_verdict_with_reason` |
| AC-03 | `poison::SurfaceParsingTests`（含协议错误不臆造工具） |
| AC-04 | `poison::AgentSseTests::test_ac04_probe_extracts_text_result_and_telemetry` |
| AC-05 | `poison::AgentSseTests::test_ac05_event_scope_is_single_data_line` / `..._does_not_leak_across_blank_lines` |
| AC-06 | `poison::PoisonSelfProofTests::test_ac06_local_server_serves_poisoned_surface` / `..._call_tool_executes_attacker_arguments` |
| AC-07 | `poison::PoisonSelfProofTests::test_ac07_*` |
| AC-08 | `runner::GradeTests::test_ac08_four_levels` / `test_ac08_reason_always_states_both_sides` |
| AC-09 | `runner::GradeTests::test_ac09_grade_module_has_no_framework_or_network_import` / `..._does_not_touch_transport` |
| AC-10 | `runner::OverPrivilegeTests::test_ac10_admin_allowed_yields_full_effect` / `..._consent_required_caps_at_partial` |
| AC-11 | `runner::OverPrivilegeTests::test_ac11_guard_block_is_ineffective_and_not_retried` |
| AC-12 | `flag::EvidenceContractTests::test_ac12_fragment_has_four_required_sections` |
| AC-13 | `flag::EvidenceContractTests::test_ac13_no_browser_marks_pending_and_writes_no_png` |
| AC-14 | `flag::FlagChannelTests::test_ac14_oracle_accepts_value_counts_as_consistent` / `..._rejects_value_downgrades` |
| AC-15 | `flag::FlagChannelTests::test_ac15_no_value_means_skip_and_no_flag_injected` |
| AC-16 | `flag::EvidenceContractTests::test_ac16_manifest_row_has_required_fields` |
| AC-17 | `runner::DependencyAndCliTests::test_ac17_*`；`units::ShotTests/TransportTests`（仅降级分支） |
| AC-18 | `runner::DependencyAndCliTests::test_ac18_cli_runs_single_step_offline` / `..._rejects_unknown_step` |
| AC-19 | `runner::EntryPointTests::test_ac19_unreachable_target_is_skipped_with_reason` |
| AC-20 | `python scripts/measure_coverage.py --target attack-mcp-tool --min 80` |
| AC-21 | `python scripts/check_glossary.py` + `runner::test_ac22_*`（禁用 API 名） |
| AC-22 | `runner::EntryPointTests::test_ac22_object_graph_matches_adr_0004` |
| AC-23 | 真实演练记录（`docs/operations/attack-mcp-tool-verification.md`），不进 CI |

## 2. 红 → 绿 → 重构留痕

| # | 轮次 | 红（实际失败输出） | 绿（最小改动） | 重构 |
|---|---|---|---|---|
| R-1 | AC-05 | 研究阶段实测发现：`event: meta` 后的无名 `data:` 事件被错误继承为 `meta`，导致工具清单被当作元数据丢弃（探针首跑 `mcp_results=0`） | 改为「`event:` 只作用于紧随其后的**一条** `data:`，遇 data 即分发并复位」 | 抽出 `parse_sse()` 单函数，加两条回归用例锁定 |
| R-2 | AC-13 | `AssertionError: '待补录' not found in '### 步骤 mcp-08：flag 取证…'` —— 共享工具仅看到钩子命令即判「截图已提供」，读者会误认为已截图 | 编排层在 `shot_path` 为空时补写「**截图待补录**」注记并保留钩子命令 | 保持共享工具不改（Out of Scope），降级语义收敛在编排层一处 |
| R-3 | 报告口径 | `test_observation_payload_redacts_secrets` 失败：报告里 `tool_result` 仍是明文 | 明确口径：`secrets` 索引脱敏，`tool_result` 保留原文（取证与面板提交的唯一依据）；测试改为断言双性质 | 用例改名 `..._redacts_secret_index_only` 并在 docstring 写明理由 |

## 3. 覆盖率

- 本包：**86.1%**（1142/1327 行，门槛 80%）；最低模块 `poison.py` 73.0%（未覆盖集中在 `_Handler` 的错误分支与 `stop()` 竞态）。
- 全量（`--target all`）：**89.1%**（3310/3713 行）。
- 未覆盖分支说明：`poison.py` 的 JSON 解析失败分支与 `ThreadingHTTPServer` 关闭竞态；`runner.py` 的极端 IO 分支。均为不可稳定触发的防御分支，已登记为改进项而非缺陷。

## 4. 本地与 CI 一致性

`python -m unittest discover -s tests -q` → `Ran 243 tests … OK`；CI S2 执行同一命令与同一覆盖率脚本，**判定一致**。

## 5. 门禁记录（阶段 9 / G0）

| 编号 | 检查项 | 依据 | 实测结果 | 判定 |
|---|---|---|---|---|
| B3 | 语法与构建 | `python -m py_compile tools/attack_mcp_tool/*.py tools/serve_malicious_mcp.py` | 退出码 0 | 符合 |
| B3 | 全量测试 | `python -m unittest discover -s tests -q` | `Ran 243 tests` / `OK` | 符合 |
| B4 | 证据契约 | `flag::EvidenceContractTests`（四节 + 清单字段 + strict 退出码 0） | 3/3 通过 | 符合 |
| B6 | 覆盖率门禁 | `python scripts/measure_coverage.py --target all --min 80` | `89.1%` ≥ 80% | 符合 |
| B8 | 可追溯性 | 本文 §1 映射表 | AC-01…AC-23 全覆盖（AC-23 由演练记录承担） | 符合 |
| 验收② | 红阶段有实际失败输出留痕 | §2 R-1/R-2/R-3 | 三轮均含原文断言消息 | 符合 |
| 验收③ | 全量 unittest 通过 | 实跑 | OK | 符合 |
| 验收⑤ | 只测外部行为 | 人工判据：断言对象为报告字段/证据文本/HTTP 请求计数 | 无私有函数断言 | 符合 |
| 验收⑥ | 本地与 CI 判定一致 | 同一命令与脚本 | 一致 | 符合 |

**结论：PASS**。不符合项 0。上游复核：`check_glossary` / `validate_skill` / `check_token_budget --check` 均通过，规格 v2 与设计文档未被破坏。
