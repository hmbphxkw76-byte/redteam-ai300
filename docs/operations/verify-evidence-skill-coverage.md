# verify-evidence — SKILL.md 逐条实现核对（全覆盖矩阵）

> **用途**：回答「SKILL.md 规范的内容是否全部落地」。逐条列条款 → 实现位置 → 实测证据（命令 + 结果）。
> **核对时间**：2026-11-15 · 分支 `feat/verify-evidence` · 校验器 `tools/verify_evidence.py`（schema 1.0）

## 1. 元信息（front-matter 七字段）

| 条款 | 实现 | 实测 |
|---|---|---|
| name/priority/domain/scoring_unit/trigger/input/output | `skills/verify-evidence/SKILL.md#L1-L9` | `python scripts/validate_skill.py` → PASS（16 技能全合规） |

## 2. 执行体（vrf-01…vrf-08 + proof 约束）

| 条款 | 实现 | 实测证据 | 用例 |
|---|---|---|---|
| 执行入口（三入口同一判定层） | `main()` / `load_payload` / `from_loot` / `from_fragments` | `python tools/verify_evidence.py --from-loot D:/_smoke_ve/OS-12345-registry.md --report ... --no-artifacts --summary` → `结论：通过（阻断 0）`，退出码 0；`--fragments-dir` 入口同法可用 | `test_AC01*`、`test_AC16_cli_runnable_as_script` |
| vrf-01 技能五要素终检 | `check_vrf01` + `Toolchain.validate_skills` | 真实校验器路径实测 `vrf-01 = True` | `test_AC03_skill_validation_gate` |
| vrf-02 优先级与评分杠杆一致 | `check_vrf02` + `Toolchain.skill_meta`（ADR-0002：高杠杆不得 P2） | `skill_meta()` 返回 16 条；高杠杆技能 7 个，P2 失配 0 | `test_AC04_point_allocation_matrix`（含 P2 失配反例） |
| vrf-03 三件套齐全 | `check_vrf03` → `registry.fragment_pieces` | 片段缺「截图」节 → 阻断（已取分）/ 记缺失（未取分） | `test_AC05_*`、`test_AC17_*` |
| vrf-04 双通道一致 | `check_vrf04` 面板值 vs 报告值逐字 | 面板≠报告 → 阻断 | `test_AC06_*`、`test_AC01b_*` |
| vrf-04 访问证明同屏 | `_access_proof` + `_screenshot_section` | 截图节含 `id` + flag → 通过；含文本无 token → 阻断；纯图片 → `NOTE-7` | `test_AC07_access_proof_same_screen` |
| vrf-05 AI 交互入附录 | `check_vrf05`（逐字包含）+ `NOTE-9`（§5.5 人工标注） | 日志不在附录 → 阻断 | `test_AC08_ai_log_verbatim` |
| vrf-06 报告四章结构 | `check_vrf06`（`REQUIRED_ANCHORS` 8 项）+ `NOTE-10`（五段式人工） | 逐锚点删除 → 各自阻断并指明锚点 | `test_AC09_*` |
| vrf-07 命名/体积/无密码/24h | `check_vrf07` / `check_naming_and_size` / `Toolchain.archive_encrypted` / `_check_window` | 命名错、缺失、>100MB、已加密、超窗 → 阻断；无 7z → `NOTE-8`；时间缺失 → `NOTE-5` | `test_AC10_*`、`test_AC11_*` |
| vrf-08 术语合规 | `check_vrf08`（动态取 `GLOSSARY.md`，与 `check_glossary` 同源） | `load_avoid_terms()` = 50 条，与检查器同源 | `test_AC13_obsolete_term_scope` |
| 域控 proof.txt 单次 | `check_proof_single`（按 `domain-controller` 键） | 2 条记录 → 阻断；0 条 → `VG-4` 豁免记录；非域控含该子串 → 不误判 | `test_duplicate_proof_txt_is_blocking`、`test_flag_substring_does_not_count_as_proof_submission` |

## 3. 质量门（5 条「必须」）

| 条款 | 实现 | 判定方式 |
|---|---|---|
| 八项检查单全部通过（无阻断） | `verify()`：`passed = not failed_checks and not blocking` | `checks` 九键全非 False |
| proof.txt 不得超过 1 次 | `check_proof_single` | `proof-single=true/false` |
| 每个 flag 双通道一致 | `check_vrf04` | `vrf-04` |
| 每个计分目标三件套齐全 | `check_vrf03` | `vrf-03` |
| 校验通过作为 report-exam 提交前置 | `report_exam/package.py::package()` 取 `submission_ready` | `test_AC18_downstream_delegation_intact` + `report-toolchain.yml` 断言 `verify-evidence: passed` |

## 4. 校验标准（4 条）

| 条款 | 实现 |
|---|---|
| 判定客观、可机读，缺失项定位到目标/步骤/检查项 | `verify()` 返回 `checks`（9 键布尔）+ `blocking`/`missing`/`pending` 分级，条目带 `vrf-0x` / `proof-single` 前缀与 `step_id`/主机键 |
| 与 report-exam / loot-manage 衔接 | 输入消费两者产物；`from_loot` 复用 `registry.parse_dual`/`fragment_pieces`；输出被 `package()` 消费 |
| 术语符合 `GLOSSARY.md` | `check_vrf08` 动态读取，无硬编码词表 |
| 输出可被 CI 复用 | 固定 schema `1.0` + 退出码 0/1/2；`report-toolchain.yml` 已按 `verify-evidence: passed` 断言 |

## 5. 失败与豁免（4 条）

| 条款 | 实现 |
|---|---|
| 未取分目标的证据缺失属预期，不计阻断 | `check_vrf03/04`：未取分缺口进 `missing`，`passed` 不受影响；`test_three_piece_gap_is_recorded_not_blocking` |
| 双通道不一致必须回溯补正，不妥协放行 | `check_vrf04` 只判不改；不一致即 `vrf-04=false` + `blocking` |
| 24h 临近时优先保四个阻断项 | 四项（双通道/四章/命名/proof 单次）均为硬阻断；其余瑕疵落 `missing`/`NOTE`，不阻断 `passed` |
| S1-only，不新增 S2 证据契约夹具 | 未新增 `tests/test_verify_evidence_evidence_contract.py`；S2 覆盖为 AC 用例集（32 例） |

## 6. 本轮新发现并修复的缺口

1. **脚本直跑失败**：`python tools/verify_evidence.py` 报 `ModuleNotFoundError: tools`（`sys.path[0]=tools/`）——SKILL 写法的入口本身不可用。已在模块顶部补仓库根入 `sys.path`，并加回归用例 `test_AC16_cli_runnable_as_script`。
2. **vrf-02 漏判**：原实现只核报告内计分清单，未核「技能优先级与评分杠杆一致」（§4.3/ADR-0002）。已补 `Toolchain.skill_meta` + P2 失配阻断（实测 16 技能、7 个高杠杆、0 失配）。
3. **US-03 无入口**：SKILL 输入含「各技能证据片段」，原仅支持登记簿。已补 `--fragments-dir` 第三入口（主机按 `**目标**` 或文件名主干归属）。
4. **vrf-05/06 人工判据未留痕**：补 `NOTE-9`（§5.5 人工校验标注）与 `NOTE-10`（每主机五段式）。

## 7. 判定

- SKILL 执行体 8 项 + proof 约束 + 质量门 5 条 + 校验标准 4 条 + 失败与豁免 4 条：**逐条有实现位置与实测证据**。独立复核（15:20）将其中 5 条判为「部分实现」，见 §8；无「未实现」条款。
- 机器不可判的 3 处（访问证明图片、五段式、AI 人工校验标注）已在 SKILL 校验标准与 `NOTE-7/9/10` 中显式转为人工判据，不作静默放行。

## 8. 独立复核（2026-11-15 15:20，main 实测）

| 项 | 判定 | 缺失内容 |
|---|---|---|
| vrf-04 访问证明同屏 | 部分实现 | 纯图片截图无内联文本 → `NOTE-7` 人工判；无 OCR（SKILL 声明范围外） |
| vrf-05 §5.5 人工校验标注 | 部分实现 | 无机判，仅 `NOTE-9` |
| vrf-06 五段式 / copy-paste 复现 | 部分实现 | 无结构解析器，仅 `NOTE-10`（中英标题不固定） |
| proof.txt 单次 | 部分实现 | SKILL 口径由 `==1` 改为 `≤1`，0 条按未取分豁免；变更理由见 SKILL「修订记录」 |
| 校验标准①「判定客观、可机读」 | 部分实现 | 九项 boolean 全机读，但上述 3 个子项仅人工 NOTE |

- 实测：`unittest tests.shared_tools.test_verify_evidence` → 32 用例 OK；`measure_coverage.py --target verify-evidence` → 92.1%（488/530）；CLI 退出码 0/1/2 三态实跑。
- `NOTE-5/6/7/8/9/10` 回归用例以函数名锚定：`test_AC04_point_allocation_matrix` / `test_AC07_access_proof_same_screen` / `test_AC08_ai_log_verbatim` / `test_AC11_submission_window`（`tests/shared_tools/test_verify_evidence.py`），人工边界不会静默消失。
- **结论**：已实现 20 / 部分实现 5 / 未实现 0；部分实现均为已声明的人机边界，非功能缺失。
