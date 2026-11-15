# decoy-detect 双轴代码审查（code-review）

> 依据 `docs/operations/skill-mainline-workflow.md` §3.10。基线：`merge-base origin/main HEAD` 之工作变更（decoy-detect 文件集）。
> 两轴分离、不合并、不重排。硬违规阻断，判断项记录为改进项。

## 轴一：Standards（编码规范）

| # | 发现 | 分类 | 处置 |
|---|---|---|---|
| S1 | 全部模块 `py_compile` 通过；仅标准库；无硬编码凭据 | — | 通过 |
| S2 | 依赖方向单向无环（`model.py` 为叶子，其余单向 import） | — | 通过 |
| S3 | 业务逻辑为纯函数/纯类，IO 仅在 `cli.py`/`evidence.py`（可纯单测） | — | 通过 |
| S4 | `model.coerce_host` 当前仅在测试使用，属防御性工具函数 | 判断项 | 保留（有测试覆盖，供输入归一复用） |
| S5 | `cli._emit_evidence` 返回的 writer 未被调用方使用（以 `_writer` 命名） | 判断项 | 可接受（保留扩展位） |

发现数 5；硬违规 0。

## 轴二：Spec（规格忠实度，v2 AC1–AC13）

| AC | 实现位置 | 测试 | 判定 |
|---|---|---|---|
| AC1 行为特征 | `features.classify_dimensions` | `test_classify_behavior_only` | 符合 |
| AC2 漏洞缺失 | 同上（三项皆缺） | `test_classify_leak_requires_all_three` | 符合 |
| AC3 无价值 | 同上 | `test_classify_no_value_variants` | 符合 |
| AC4 ≥2→诱饵 | `policy.decide` | `test_two_dims_decoy` | 符合 |
| AC5 单维度须交叉验证 | `policy.decide` | `test_one_dim_*` | 符合 |
| AC6 时间盒 | `timebox.TimeBoxTracker` + runner 强制 | `test_start_stop_with_clock`、`test_run_scan_fixture` | 符合 |
| AC7 五字段清单 | `listgen.render_markdown` | `test_render_basic` | 符合 |
| AC8 质量门 | `validate.validate_quality_gate` | `test_*_violation` ×4 | 符合 |
| AC9 ≈2 对账 | `listgen` 全局对账 | `test_render_mismatch_warning` | 符合 |
| AC10 证据 seam + e2e | `evidence.EvidenceWriter`、`cli` | `test_emit_produces_three_piece`、`test_cli_evidence_dir` | 符合 |
| AC11 S1 | validate_skill/check_glossary/token_budget | 干净工作树实测 PASS | 符合 |
| AC12 覆盖率 | `measure_coverage --target decoy-detect` | 95.2% ≥80% | 符合 |
| AC13 无 PyRIT | 源码无 `import pyrit`/`*Orchestrator` | grep 实测 | 符合 |

发现数 0；硬违规 0；规格覆盖矩阵无空格。

## 复跑（§2.3 上游复核）

- `python scripts/validate_skill.py` → PASS（16 技能）
- `python scripts/check_glossary.py` → PASS（39 废弃术语）
- `python scripts/check_token_budget.py --check` → 结论 PASS（14 契约）
- `python -m unittest discover -s tests -p "test_decoy_detect*.py"` → 59 tests OK
- `python scripts/measure_coverage.py --target decoy-detect --min 80` → 95.2%

> 复核均在「干净工作树」（HEAD + decoy 变更集，排除并行未提交改动）执行，等价 CI 判定。

## 结论

两轴硬违规均为 0；门禁套件全绿。**PASS**。
