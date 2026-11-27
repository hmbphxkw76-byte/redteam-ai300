# decoy-detect 工程规格 v2

> 回溯整理：依据 `skills/decoy-detect/SKILL.md` 与既有实现、测试归纳；**不代表原流程按序执行**。
> 整理日期：2026-11-27　状态：定稿（v2）

## 0. v1 → v2 差异清单

| # | v1 表述 | v2 收敛 | 理由 |
|---|---|---|---|
| 1 | 「提取三类信号」 | 每类给出可机读字段与布尔判据（AC1–AC3） | 可判定化 |
| 2 | 「≥2 类即诱饵」 | 固定阈值 `MIN_DECOY_DIMENSIONS = 2`（AC4） | 消除计数歧义 |
| 3 | 「单维度须交叉验证」 | 三态：验证判诱饵 / 未验证放弃 / threat 标记放弃（AC5） | 覆盖冲突分支 |
| 4 | 「超时记录不确定」 | `elapsed > 1800` 强制结论并置 `timebox_exceeded`（AC6） | 边界可测 |
| 5 | 「五字段清单」 | 五字段缺失即 `missing_fields` 非空（AC7） | 契约化 |
| 6 | 「≈2 台对齐」 | 仅告警、不改判（AC9） | 不凑数 |
| 7 | 未涉及证据 | 三件套委托共享收集器，strict 缺截图失败（AC10） | C1 单一事实源 |
| 8 | 未涉及工程门禁 | 静态、单测、覆盖率、无 PyRIT（AC12–AC15） | 可合并判定 |

## 1. 布尔验收条件

| ID | 验收条件（可判定布尔式） | 判定方式（真实测试/命令） |
|---|---|---|
| AC1 | `present_categories` 为空，或 `decoy_suspected` 为真 → 命中「行为特征」；有面且未疑似 → 不命中 | `test_decoy_detect_units.FeatureTests.test_classify_behavior_only` |
| AC2 | 高价值服务、可达入口、可利用配置错误三项全缺才命中「漏洞缺失」；缺任一项即不命中 | `FeatureTests.test_classify_leak_requires_all_three` |
| AC3 | `banner_service_count<=0`，或 `info_sufficient` 假，或 `inventory_match` 假 → 命中「无价值特征」；三变体均命中 | `FeatureTests.test_classify_no_value_variants` |
| AC4 | 命中维度数 ≥2 → 结论为「诱饵」 | `PolicyTests.test_two_dims_decoy` |
| AC5 | 维度数=1 且未验证 → 「不确定-已放弃」；经 `cross_validated` 或 `threat_model_decoy` → 「诱饵」 | `PolicyTests.test_one_dim_no_cross_uncertain` / `test_one_dim_cross_validated_decoy` / `test_one_dim_threat_model_decoy` |
| AC6 | `elapsed_seconds > 1800` → 结论强制「不确定-已放弃」且 `timebox_exceeded` 真；等于 1800 不超盒 | `TimeBoxTests.test_exceeded` / `test_start_stop_with_clock`；`RunnerTests.test_run_scan_fixture` |
| AC7 | 条目五字段（host_id / hit_dimensions / evidence / abandonment_reason / timestamp）齐全；缺任一则 `missing_fields` 返回该名 | `ModelTests.test_missing_fields_all_present` / `test_missing_fields_partial`；`ListGenTests.test_render_basic` |
| AC8 | 缺字段、单维度未验证即排除、超盒未按「不确定-已放弃」→ 违规列表非空；合规输入 → 空 | `ValidateTests.test_missing_fields_violation` / `test_single_dim_decoy_violation` / `test_single_dim_scored_violation` / `test_over_timebox_unmarked` / `test_over_timebox_wrong_conclusion` / `test_valid_no_violation` |
| AC9 | 判定诱饵数 ≠ `expected_decoys` → 清单含「告警」且结论不变；相等 → 「数量与预期一致」 | `ListGenTests.test_render_mismatch_warning` / `test_render_match` |
| AC10 | 启用 `--evidence-dir` 时每条判定产出一份片段，三件套由共享收集器生成；strict 且缺截图 → 返回失败 | `test_decoy_detect_evidence_contract.DecoyEvidenceContractTests.test_emit_produces_three_piece` / `test_emit_nonstrict_without_screenshot` / `test_writer_delegates_shared_collector`；`CliTests.test_cli_evidence_dir` |
| AC11 | 输入不可读 / 非 JSON / 缺 `hosts` → 退出码 2，且不产出清单 | `CliTests.test_cli_bad_inventory_exit2` |
| AC12 | 源码无 `pyrit` / `*Orchestrator` 引用 | `grep -rn "pyrit\|Orchestrator" tools/decoy_detect/` → 0 |
| AC13 | `validate_skill.py`、`check_glossary.py`、`check_token_budget.py --check` 均 PASS；`check_tools_compile.py` 失败 0 | 命令 |
| AC14 | `python -m unittest discover -s tests/decoy_detect -t . -q` 退出码 0 | 命令（59 例） |
| AC15 | `python scripts/measure_coverage.py --target decoy-detect --min 80` 退出码 0 | 命令（实测 95.3%，482/506） |

## 2. 测试决策

- **只测外部行为**：`features.extract` / `classify_dimensions`、`policy.decide`、`listgen.render_markdown`、`validate.validate_quality_gate`、`cli.main` 的退出码；不断言私有字段。
- **确定性**：`TimeBoxTracker(clock=...)` 注入假时钟；`runner.run_scan(timestamp_fn=...)` 注入固定时间戳。
- **夹具与隔离**：`tests/fixtures/decoy_scan.json` 驱动端到端；证据契约用临时目录与替身收集器隔离子进程。
- **模块口径**：manifest 登记 2 个测试模块、9 个实现模块；当前实跑 59 例。
- **不做**：不 mock 业务函数、不以 sleep 计时、不做真实 exam 主机实跑（本次未发生）、不引入 LLM judge。

## 3. 门禁映射

| 门禁 | 覆盖 AC | 命令 |
|---|---|---|
| CI S1（编译 + 静态） | AC12、AC13 | `check_tools_compile.py`、`validate_skill.py`、`check_glossary.py` |
| CI S2（测试 + 覆盖率） | AC14、AC15 | `unittest discover -s tests/decoy_detect -t . -q`、`measure_coverage --target decoy-detect` |
| 证据契约 | AC10 | `python scripts/check_evidence_contract.py` |
| C4 产物预算 | AC13 | `python scripts/check_token_budget.py --check` |
| 术语一致性 | AC13 | `python scripts/check_glossary.py` |

## 4. 证据与可观测性

- **证据 seam**：`evidence.EvidenceWriter` 以子进程调用 `tools/collect_evidence.py --step <id> --strict`；片段路径 `<evidence-dir>/<step>.md`，三件套为命令 + 输出 + 截图，AI 交互日志由共享收集器维护。
- **退出码可观测**：0 通过；1 质量门或证据违规；2 用法/输入错误。
- **机读摘要**：`RunReport.to_dict()` 暴露 `decoy_count` / `uncertain_count` / `scored_count` / `expected_decoys` / `violations` / `passed` / `count_matches` / `judgments`。
- **复现**：`python tools/decoy_detect/cli.py run --inventory <输入.json> --out <清单.md>`；不带 `--evidence-dir` 时不落证据。
- 片段不写 flag 明文；flag 双通道与访问证明归 `report-exam` 与共享收集器。

## 5. 风险与待验证

| 风险 | 现状 | 待验证 |
|---|---|---|
| `cli.py` 分支覆盖偏低 | 89.7%（96/107），未覆盖主要为例外/帮助分支 | 补 CLI 用例可提升，不改 AC 语义 |
| 预期诱饵数写为常量 2 | 由输入 `expected_decoys` 注入，默认 2 | 真实考试规模变化时需输入端覆盖 |
| 证据截图可选 | 非 strict 时缺截图仍产出片段 | 评分场景应启用 `--strict-evidence` |
| 输入信号依赖 recon-ai 完整度 | 缺省按「有面/有价值」保守处理 | 字段缺失时偏漏判而非误杀；需真实枚举样本验证 |
| 测试为夹具驱动 | 无真实 exam 主机实跑记录（本次未发生） | 上线前补一次真实环境演练 |

> 覆盖率与用例数为本次复跑口径：`95.3%（482/506）`、`59 例 / 2 模块`；历史审查记录为 95.2%。
