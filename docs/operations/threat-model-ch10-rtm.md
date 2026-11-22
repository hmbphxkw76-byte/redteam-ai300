# Ch10 对齐需求追踪矩阵（RTM · 阶段 8/11 交付物）

> 版本 v1 · 日期 2026-11-22 · 规格源 issue #324（v1/v2）· 事实源 `docs/research/threat-model-ch10-canonical.md`（R-01..R-26）· 差距报告 `docs/research/threat-model-ch10-gap.md`（M1–M18）
> 判据：每行【Ch10 锚点 | 实施项 | 实现位置 | 验证命令/用例 | PASS|FAIL】；无"未落地"项。

## 1. M1–M18 逐项追踪

| M# | Ch10 锚点 | 实施项 | 实现位置（file#symbol） | 验证（命令/用例） | 结论 |
|---|---|---|---|---|---|
| M1 活体模型 | §10 L10–17；R-01 | A5 | `model.py#ThreatModel.revision/decision_log`；`__init__.py#build_threat_model(prior=)` | `test_threat_model_ch10.BriefTests.test_ac07_decision_log_is_version_history` | PASS |
| M2 迭代节奏 | §10.3 L1103–1112；R-03 | A5 | `__init__.py#new_intel→decision_log`；`brief.py#version history` | 同上 + full suite OK | PASS |
| M3 碎片重建 | §10.1 L50–121；R-01 | A6 | `classify.py#enrich(observations=)`；`model.py#AssetView.observations` | `test_threat_model.BoundaryPathTests` + `classify` 90.4% 覆盖 | PASS |
| M4 假设登记册六字段 | §10.1 Table 1；R-04 | A1 | `model.py#Assumption`；`assumptions.py#to_register` | `test_ac01_register_six_fields` | PASS |
| M5 置信度语义/缺证 | §10.1 L188–200；R-06/07 | A1 | `assumptions.py#bucket`；`render.py#§5 verification_task` | `test_ac02_low_and_absence_go_to_verification` | PASS |
| M6 皇冠珠宝进攻价值 | §10.1 Table 5；R-23 | A7 | `model.py#AssetView.offensive_value/access_status`；`render.py#§7` | `render` 84.6% + 示例输出含 §7 节 | PASS |
| M7 ATLAS 映射+前置 | §10.1 Table 6；R-24/25 | A7 | `atlas.py#map_techniques` + `model.py#ATLAS_IDS` | `test_ac13_*`（3 例）七 ID 集合 + 两分支 | PASS |
| M8 低垂果实/检测规则 | §10.1 L556–619；R-26 | A8 | `classify.py#classification_detection_rules`；`assumptions.py#derive_from_detections` | `test_ac14_derive_from_detections_medium_and_incomplete` | PASS |
| M9 信任边界分类+推理 | §10.2 Table 8；R-11/12 | A2 | `model.py#TrustBoundary`；`boundaries.py#build_trust_boundaries`；`render.py#§6` | `test_ac15_trust_gap_and_identity_collapse_fields` + 渲染五列表头 | PASS |
| M10 信任区三态图 | §10.2 Figure 4；R-15 | A2 | `model.py#VALIDATION_STATUSES`；`boundaries.py` is_gap | `render.py#§6 gap/collapse 标注` + 示例输出 | PASS |
| M11 跨边界路径+门 | §10.2 Path1/2/3；R-17/18 | A5 | `model.py#AttackPath.gates/boundary_crossings/gate_decision`；`decision.py#evaluate_gates` | `test_ac08_*`（3 例 GO/HOLD/BLOCKED） | PASS |
| M12 RoE 硬过滤双轨 | §10.1 L286–305；R-19 | A3 | `roe.py#apply_roe`；`cli.py#--roe` | `test_ac06_*`（3 例双轨/报告/无条件放行） | PASS |
| M13 Go/No-Go 矩阵 | §10.2 Table 9；R-20 | A5 | `decision.py#go_no_go`；`render.py#§8` | `test_ac09_*`（2 例四列/时间压力） | PASS |
| M14 六段版本化简报 | §10.2 Listing 8；R-21/22 | A4 | `brief.py#render_brief`；`cli.py#--brief-out` | `test_ac07_six_sections_and_fields` | PASS |
| M15 证伪派生/重规划 | §10.2 L1021–1057；R-10 | A1 | `assumptions.py#transition` 派生新假设 | `test_ac03_*`（2 例派生/非法迁移拒绝） | PASS |
| M16 检测规则派生 | §10.1 L570–619；R-26 | A8 | `assumptions.py#derive_from_detections`（规则集不完整标注） | `test_ac14_*` | PASS |
| M17 身份塌缩/归属 | §10.2 TB-5；R-14 | A8 | `model.py#TrustBoundary.identity_collapse`；`render.py#§6` | `test_ac15_*` | PASS |
| M18 信任缺口 TRUST_GAP | §10.3 L1113–1121；R-16 | A8 | `boundaries.py#is_gap`（enforcement 缺失） | `test_ac15_*` + 示例输出含 TRUST_GAP | PASS |

## 2. A1–A8 对齐验证总结（阶段 11 门槛）

| 实施项 | 覆盖 M | 实现锚点 | 验证证据 | 结论 |
|---|---|---|---|---|
| A1 假设登记册 | M4/M5/M15 | `assumptions.py` + `model.py#Assumption` | 5 例单测 PASS | **PASS** |
| A2 边界实体化 | M9/M10 | `model.py#TrustBoundary` + `boundaries.py` | 渲染五列 + gap 标注 PASS | **PASS** |
| A3 RoE 双轨 | M12 | `roe.py` + `cli.py#--roe` | 3 例单测 PASS | **PASS** |
| A4 六段简报 | M14 | `brief.py` + `cli.py#--brief-out` | 2 例单测 PASS | **PASS** |
| A5 路径门/矩阵/增量 | M1/M2/M11/M13 | `decision.py` + `AttackPath` + `build_threat_model(prior=)` | 7 例单测 PASS | **PASS** |
| A6 观察来源链 | M3 | `classify.py#observations` | 既有回归 + classify 90.4% | **PASS** |
| A7 皇冠珠宝/ATLAS | M6/M7 | `render.py#§7` + `atlas.py` | 3 例单测 + 七 ID 断言 PASS | **PASS** |
| A8 检测规则/塌缩/缺口 | M8/M16/M17/M18 | `assumptions.py#derive...` + `TrustBoundary` | 2 例单测 PASS | **PASS** |

## 3. 回归硬门槛（AC-18）

| 检查 | 命令 | 结果 |
|---|---|---|
| 语法 | `python -m py_compile tools/threat_model/*.py` | PASS |
| 技能结构 | `python scripts/validate_skill.py` | PASS（16/16） |
| 术语 | `python scripts/check_glossary.py` | PASS（66 废弃术语） |
| 预算 | `python scripts/check_token_budget.py --check` | PASS |
| Markdown | `npx markdownlint-cli2 docs/research/threat-model-ch10-*.md docs/operations/threat-model-ch10-design.md` | 0 issues |
| 单测（技能） | `python -m unittest discover -s tests/threat_model -t .` | 53 tests OK |
| 全量单测 | `python -m unittest discover -s tests -t .` | 1014 tests OK (skipped=3) |
| 覆盖率 | `python scripts/measure_coverage.py --target threat-model --min 80` | 87.3%（基线 85.7%，不降） |
| 证据契约 | `tests/threat_model/test_threat_model_evidence_contract.py`（7 例，含于 53） | PASS |
| flag 段兼容 | `report_exam.index.parse_fragment` 未改段落结构；既有证据契约测试 PASS | PASS |

## 4. 结论
- M1–M18 全部有实现对应与验证证据，无"仅规划未落地"或"无对应实现"项。
- A1–A8 全部 PASS；AC-01..AC-18 全部满足。
- 覆盖率不下降（85.7% → 87.3%），既有 32 例 + 全量 1014 例全绿，无回归。
- **对齐验证结论：全部通过。**
