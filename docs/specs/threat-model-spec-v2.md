# threat-model 工程规格 v2

> 回溯整理：依据 `skills/threat-model/SKILL.md` 与既有实现、测试归纳；**不代表原流程按序执行**。
> 整理日期：2026-11-27　状态：定稿（v2）

## 1. v1→v2 差异清单

| 差异 | v1（行为描述） | v2（可验证收敛） | 理由 |
|---|---|---|---|
| 表达层级 | 五节行为与产物叙述 | 逐条布尔 AC，指向测试或命令 | 阶段 3 职责：把 What 收敛为可判定判据 |
| 边界语义 | 「不虚构/待补/不可判定」文字 | AC-06/15/16 显式枚举取值 | 让豁免成为可断言分支 |
| 质量门 | 「四项齐全」定性 | AC-14 用 `quality_gate()` 空/非空判定 | 空诱饵判定清单合法需与构建未执行区分 |
| 证据复用 | 「可衔接下游」 | AC-10/11 断言 `asset_id`+`evidence_step` 锚点 | copy/paste 复现可机读验证 |
| 工程约束 | 无 | AC-21..24 补编译/覆盖率/manifest/术语 | 把 CI 门禁落到每条 AC |
| 增量能力 | Ch9/Ch10 描述 | AC-17..20 分模块布尔断言 | Ch9 身份链与 Ch10 活体建模可独立判定 |

## 2. 布尔验收条件（AC）

| AC | 验收条件（布尔） | 判定方式 / 测试锚点 |
|---|---|---|
| AC-01 | 给定完整分类层，当构建，则高价值清单按分值降序、攻击面∈D1–D11、AI向量机/独立机居前 | `test_threat_model.ScoreTests.test_score_rank_desc` / `test_ai_vector_and_standalone_tie_at_top` |
| AC-02 | 给定未知 score_class，则该资产记「不可判定」且 0 分 | `ScoreTests.test_unknown_score_class_defaults_zero` |
| AC-03 | 给定含诱饵输入，当取高价值，则诱饵被剔除 | `ScoreTests.test_high_value_only_excludes_decoys` |
| AC-04 | 给定分类信任域，当归类，则 `boundaries[zone]` 含对应 asset_id | `BoundaryPathTests.test_trust_boundaries_grouped` |
| AC-05 | 给定路径，则含起止/阶段/耗时(int)/依赖(list)/状态∈{可达,待补} | `BoundaryPathTests.test_path_fields_complete` |
| AC-06 | 给定依赖资产缺失或不可达，则路径状态为「待补」 | `test_missing_dependency_marks_待补` |
| AC-07 | 给定 AI向量机，则路径依赖含 attack-ai-agent/multi-agent/rag/embeddings/mcp-tool/infra | `test_ai_vector_subskill_coverage` |
| AC-08 | 给定诱饵三维度命中且 ≤30min，则判「诱饵机」并放弃；超 30min 则判「判定不确定」并含放弃理由+时间戳 | `DecoyTests.test_decoy_verdict_in_timebox` / `test_timebox_exceeded_forces_abandon` |
| AC-09 | 给定攻击图，则诱饵不在节点、根为高杠杆、编排首项为 AI/向量、末项为域控 | `GraphTests`（3 例） |
| AC-10 | 给定渲染 markdown，则四节+质量门齐全且含 `asset_id` 与 `evidence_step` 锚点 | `ReuseEvidenceTests.test_markdown_has_four_sections`；`test_threat_model_evidence_contract` |
| AC-11 | 给定渲染输出，则排序/路径附来源锚点（§2.2/§2.3、分类依据、路径依据） | `test_reproducibility_source_anchors` |
| AC-12 | 给定渲染输出，则除已知指纹线索外无明文凭据 | `test_no_plaintext_secret` |
| AC-13 | 给定实现源码，则不 import 攻击框架、无旧版编排器/目标对象名 | `FrameworkTests.test_no_attack_framework_imports` |
| AC-14 | 给定满模型，则 `quality_gate()==[]`；给定空模型，则列出缺失项；空诱饵判定清单合法 | `QualityGateTests`；`test_threat_model_ch10.ModelContractTests.test_ac18_empty_decoys_is_legal` |
| AC-15 | 给定 CLI，则成功=0、输入错误=1、质量门未过=1 | `CliTests`（4 例） |
| AC-16 | 给定假设登记，则六字段+置信度桶（LOW/缺证→验证任务）+状态机+证伪派生 | `test_threat_model_ch10.AssumptionRegisterTests`（5 例） |
| AC-17 | 给定 RoE 禁止路径，则从执行计划移除但仍作风险发现报告，无条件放行分支 | `RoETests`（3 例） |
| AC-18 | 给定路径依赖假设，则门判定为 GO/HOLD/BLOCKED，决策矩阵五列含时间压力 HOLD | `DecisionTests`（5 例） |
| AC-19 | 给定映射，则恰输出七个 ATLAS ID，前置未验证标 applicable if、VALIDATED 标立即适用 | `AtlasTests`（3 例） |
| AC-20 | 给定模型，则简报含六段+Classification/Engagement Day/Brief Version，决策日志即版本史 | `BriefTests`（2 例） |
| AC-21 | 给定信任边界，则五要素齐全，无强制机制标 TRUST_GAP、身份塌缩可标注 | `ModelContractTests.test_ac15_trust_gap_and_identity_collapse_fields` |
| AC-22 | 给定 IAM/K8s 身份链，则资产 ID 稳定（`iam-<role>`/`k8s-sa-<name>`）、复用 `shortest_paths`、零网络 | `test_tm_c3_hardening`（14 例）/ `test_tm_ch9`（6 例） |
| AC-23 | 当跑 `python -m unittest discover -s tests/threat_model -t . -q`，则 73 例全通过 | 目录实跑 |
| AC-24 | 当跑 `python scripts/measure_coverage.py --target threat-model`，则覆盖率 ≥80%，实测 87.3%（745/853） | 覆盖率脚本 |
| AC-25 | 当对 `tools/threat_model/*.py` 执行 `py_compile`，则全部通过 | 编译 |
| AC-26 | 当跑 `python scripts/check_glossary.py`，则 threat-model 条目零废弃术语命中 | 术语校验 |
| AC-27 | 当查 `scripts/tools_manifest.json`，则登记 13 模块 + 3 测试模块 | JSON 断言 |
| AC-28 | 当跑 `verify_tm_c3_skill_refs.py` 与 `verify_tm_c3_coverage.py --min 90`，则均 PASS（97.4%） | Ch9 复验 |

## 3. 测试决策

- 只测外部行为：输入→ThreatModel→markdown 四节/质量门/字段，不断言实现细节。
- 纯函数 + 注入时钟，无网络、无 LLM、无攻击框架（矩阵 ⑬）。
- 测试落点：`tests/threat_model/test_threat_model.py`（25）、`test_threat_model_evidence_contract.py`（7）、`test_threat_model_ch10.py`（21）为 manifest 口径 3 模块 53 例；`test_tm_ch9.py`（6）、`test_tm_c3_hardening.py`（14）为全目录增量，合计 73 例。
- 证据契约以「结构化片段可被下游按 asset_id 消费」为判据，替代逐步命令取证（规划技能无实时命令）。

## 4. 门禁映射

- AC-23/24/25 → CI S2（unittest + 覆盖率）+ B3。
- AC-10/11/12 → 证据契约测试 + B4（片段可机读）。
- AC-13/24 → B7（无旧版对象）+ B6（覆盖率 ≥80%）。
- AC-26/27 → B1（技能解剖）/ B2（术语）+ S1。
- AC-22/28 → Ch9 专项复验脚本。
- AC-28 亦为阶段 8/11 的 Ch9 回归硬门槛。

## 5. 证据与可观测性

- 可观测产物：`ThreatModel.quality_gate()`（缺失项列表，空即过门）、`render()` 四节+质量门 markdown、`render_brief()` 六段简报、`DecoyVerdict` 时间戳。
- 证据指针：`tools/threat_model/`（13 模块）；`tests/threat_model/`（5 测试文件）；设计记录 `docs/operations/threat-model-design.md`、`threat-model-ch10-design.md`；RTM `docs/operations/threat-model-ch10-rtm.md`；推送审计 `docs/operations/threat-model-ch9-push-audit.md`、`tm-c3-hardening-push-audit.md`。
- 提交基线：`9c5581d`（2026-11-22）；初始实现 PR #202（`fde51a1`），Ch10 PR #335，Ch9 加固 PR #407。

## 6. 风险与待验证

- 最短路径为基于信任域/可达性的结构化推导，非实时拓扑最短路（设计已否决 Dijkstra）；拓扑剧变时路径需由实战子技能回填校验。
- 分类层依赖分析师人工标注；标注缺失记「不可判定」，可能低估杠杆。
- Ch9 身份链仅分析、零网络，可达性未实战验证，须 attack-infra/foothold-traditional 按资产 ID 复核。
- 覆盖率 87.3%，`cli`（67.9%）与 `boundaries`（66.7%）分支偏低，属待补测试面。
- 全局 `check_glossary.py` 因 report-exam 既存文件非 0 退出，与 threat-model 条目无关；本技能条目零命中。
- A2A 无 Agent Card 时协调模式记 `UNDETERMINED`，拓扑真实性待实战确认。
