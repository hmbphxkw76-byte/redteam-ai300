# loot-manage — 工程规格 v2（历史留痕回填）

> 回溯整理：依据 `skills/loot-manage/SKILL.md` 与既有实现、测试归纳；**不代表原流程按序执行**。
> 整理日期：2026-11-27　状态：定稿（v2）

## 1. v1 → v2 差异清单

- 新增 AC-01…AC-23 布尔验收条件，逐条取自 SKILL.md「质量门」「校验标准」「失败与豁免」与 loot-01..05。
- 新增测试决策：只测外部行为、临时目录夹具、零网络、零框架依赖、不触真实目标。
- 新增门禁映射：每条 AC 指向真实测试模块或用例名，或指向门禁脚本。
- 新增证据与可观测性：八项检查、flag 清单、空态原因、覆盖率口径。
- 新增风险与待验证：历史口径与当前复跑的差异、PR 无正式评审记录、Ch9 覆盖率需双脚本并看。
- v1 七节行为定义不改；冲突时以 v1 为准。

## 2. 验收条件（AC-01…AC-23，布尔）

| AC | 验收条件（必须 / 不得） | 测试模块 |
|---|---|---|
| AC-01 | 登记簿必须含八列且按列名集合匹配；缺任一列不得通过 | `tests.loot_manage.test_loot_manage.test_bad_columns_fail` |
| AC-02 | 列序调整后仍必须通过；不得因列位置变化误判 | `tests.loot_manage.test_loot_manage.test_column_order_permutation_still_passes` |
| AC-03 | 类型必须限于凭据/会话/flag，状态必须与类型匹配；错配不得通过 | `tests.loot_manage.test_loot_manage.test_status_must_match_type` |
| AC-04 | 编号必须为 `L-<n>` 且唯一；重复或非法格式不得通过 | `tests.loot_manage.test_loot_manage.test_bad_id_and_duplicate` |
| AC-05 | 来源主机不得为空或占位符；缺主机不得通过 | `tests.loot_manage.test_loot_manage.test_empty_host_blocked` |
| AC-06 | 证据片段路径必须真实存在；悬空引用不得通过 | `tests.loot_manage.test_loot_manage.test_evidence_missing_fails` |
| AC-07 | 三件套校验必须可按需开启；片段缺命令/输出/截图任一项不得通过 | `tests.loot_manage.test_loot_manage.test_fragment_pieces`、`tests.loot_manage.test_loot_manage_evidence_contract` |
| AC-08 | flag 行必须同时含面板值与截图路径；缺一不得登记 | `tests.loot_manage.test_loot_manage.test_flag_dual_channel`、`test_register_flag_requires_both_channels` |
| AC-09 | 域控 flag 必须提示「仅可提交一次」；重复登记须告警 | `tests.loot_manage.test_loot_manage.test_proof_single_warning` |
| AC-10 | 有登记行时攻击路径小节不得为空 | `tests.loot_manage.test_loot_manage.test_attack_path_required_when_rows` |
| AC-11 | 攻击路径小节必须兼容 `##` 与 `###` 两种模板层级 | `tests.loot_manage.test_loot_manage.test_attack_path_h3_template_parsed` |
| AC-12 | 失效必须原位改状态并保留原行；不得删除记录 | `tests.loot_manage.test_loot_manage.test_update_status_in_place` |
| AC-13 | 复用查询必须只返回有效凭据与存活会话 | `tests.loot_manage.test_loot_manage.test_query_and_reusable` |
| AC-14 | 空态必须可记录且判有效；`--require-loot` 仍须阻断并回显原因 | `tests.loot_manage.test_loot_manage.test_empty_state_recorded_and_passes`、`test_empty_state_require_loot_still_blocks` |
| AC-15 | 登记簿初始化必须幂等；重复初始化不得清空既有行 | `tests.loot_manage.test_loot_manage.test_init_and_idempotent` |
| AC-16 | 校验输出必须提供稳定 JSON 形状与区分退出码 | `tests.loot_manage.test_loot_manage.test_validate_json_shape`、`test_validate_missing_registry_exit2` |
| AC-17 | 定格式问答必须按 OS build 与 LLM 地址两类正则机读校验 | `tests.loot_manage.test_quiz_chain.test_ac2_format_regex` |
| AC-18 | 凭据串链必须复用攻击路径字段，不得另立平行存储 | `tests.loot_manage.test_quiz_chain.test_ac3_credential_chain_reuses_attack_paths` |
| AC-19 | 问答格式校验必须作为 vrf-09 进入校验项集合 | `tests.loot_manage.test_quiz_chain.test_ac4_vrf09_in_checks` |
| AC-20 | 云凭据必须只登记脱敏指纹；裸值、单双引号包裹的明文一律拒绝 | `test_loot_manage_ch9.test_ac02_no_plaintext`、`test_loot_manage_b5_hardening.test_ac02_plaintext_three_forms` |
| AC-21 | 下游必须能经登记簿无损还原编号、主机、证据与三件套 | `test_loot_manage_b5_hardening.test_ac06_lossless_from_loot`、`test_ac07_downstream_no_schema_drift` |
| AC-22 | 实现不得依赖 PyRIT 或任意攻击框架 | `test_loot_manage_b5_hardening.test_ac09_no_framework`、`test_loot_manage_ch9.test_ac07_no_framework` |
| AC-23 | 术语必须符合 `GLOSSARY.md`；出现废弃术语不得通过 | `scripts/check_glossary.py` |

## 3. 测试决策

- 只断言外部行为：解析结果、校验 checks、退出码、JSON 形状、文本变换；不测内部函数调用次序。
- 夹具使用 `tempfile` 临时登记簿与临时证据文件，不写产品登记簿 `loot/registry.md`。
- 真实 seam 仅涉及本地文件系统与标准输出；CI 不联网、不读取真实凭据、不打真实目标。
- 证据三件套断言以共享证据工具产物为契约，不用自造夹具替代契约。
- 历史留痕口径为 manifest 3 个测试模块、36 例；全目录实跑 5 个模块、55 例，差异见 §6。
- 覆盖率以 `scripts/measure_coverage.py --target loot-manage` 为准，门槛 80%。

## 4. 门禁映射

| 验收范围 | 基线 | 命令 | 判定口径 |
|---|---|---|---|
| AC-01 / 02 / 03 / 04 / 05 / 06 / 07 / 10 / 11 / 12 / 13 / 14 / 15 / 16 | B3 / B4 | `python -m unittest tests.loot_manage.test_loot_manage -q` | 30 例全过 |
| AC-07 / 08 / 09 / 16 | B4 / B5 | `python -m unittest tests.loot_manage.test_loot_manage_evidence_contract -q` | 2 例全过，双通道与三件套 |
| AC-17 / 18 / 19 | B3 / B8 | `python -m unittest tests.loot_manage.test_quiz_chain -q` | 4 例全过 |
| AC-20 / 21 / 22 | B3 / B8 | `python -m unittest tests.loot_manage.test_loot_manage_ch9 tests.loot_manage.test_loot_manage_b5_hardening -q`；`python scripts/verify_lm_b5_coverage.py --min 90` | 19 例全过；112/122 = 91.8% |
| AC-23 与 B1 / B2 | B1 / B2 | `python scripts/validate_skill.py`、`python scripts/check_glossary.py` | 两条均 PASS |
| 全量回归 | B3 / B6 | `python -m unittest discover -s tests/loot_manage -t . -q`；`python scripts/measure_coverage.py --target loot-manage` | 55 例 OK；469/512 = 91.6% |

## 5. 证据与可观测性

- 每次校验输出九项检查（columns/rows/types/statuses/ids/hosts/evidence/dual_channel/attack_path）与 flag 清单。
- 覆盖率：469/512 = 91.6%（registry 92.9%、cli 88.9%）；Ch9 三模块另计 112/122 = 91.8%。
- 空态原因随 `validate --json` 输出，兼作缺口信号。
- 校验失败以 blocking 列表表达，退出码区分参数错误与校验失败。
- 不引入额外遥测；登记簿与校验输出即唯一可观测载体。

## 6. 风险与待验证

- 历史记录 19 例、93.4% 与当前 30 例、91.6% 口径不同，历史值取自 PR #198 时点，未在当前树复测。
- Ch9 三模块不在 `loot-manage` target 的 modules 列表内，单看该 target 会低估覆盖面，需与 B5 覆盖率脚本并看。
- 四个 PR（#198/#219/#360/#391/#422）均无正式 review 记录；阶段 10 审查以 `docs/operations/loot-manage-code-review.md` 为唯一留痕。
- 阶段 5 仅见 `ready-for-agent` 标签，无 needs-triage 往返记录，分类定级过程不可回溯。
- 真实战利品取得依赖演练环境，CI 不复现该链路。
