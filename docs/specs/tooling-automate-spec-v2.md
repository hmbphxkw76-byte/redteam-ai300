# tooling-automate — 工程规格 v2（定稿 · 可验证性收敛）

> **阶段**：主线 阶段 3 `to-spec` ②（工程规格定稿）
> **输入**：v1 全文（`docs/specs/tooling-automate-spec-v1.md` / issue #240 正文）；阶段 1 待核实项取证（VG-1…VG-4）
> **性质**：v1 保留全文不动，本文件只做「可验证 / 可拆解 / 可交接」收敛；活版本见 issue #240 的 `## 工程规格定稿 (v2)` 评论。

---

## 1. 布尔验收条件（AC-01…AC-20）

| AC | 对应 US | 布尔验收条件 | 判定方式 |
|---|---|---|---|
| AC-01 | 01,05,12 | 任务清单为声明式，含类别/目标/step/输入/输出/触发/分类 7 字段，且全部任务登记 | `unittest` `TaskManifestTests.test_fields` → OK |
| AC-02 | 04,20,27 | 人工判读任务（flag 值级真伪、访问证明同屏）标为 `manual`；不产生自动判定结果 | `test_manual_classification`；手动清单逐条给原因 |
| AC-03 | 18,19 | 覆盖率 = 已脚本化 / 可脚本化总数；手动任务不计入分母，结果 ∈ [0,1] | `test_coverage_denominator` → OK |
| AC-04 | 01,02,03,11 | 一次编排批量执行枚举/证据/校验多步，按 step 标识顺序执行，无漏步 | `test_batch_sequence` → OK；`--dry-run` 输出步骤可比对 |
| AC-05 | 06,07 | 每步证据由既有证据收集工具落盘且带严格模式；三件套或双通道不一致即失败 | `test_strict_evidence` + `python tools/collect_evidence.py --step X --strict` → 退出 1 |
| AC-06 | 08,09,21,26 | 解剖/术语/预算/覆盖率判定调用既有校验脚本，编排层无等价实现 | `test_reuse_only`（注入替身断言调用序列）；`grep -rn "def validate_skill" tools/` 空 |
| AC-07 | 12 | 目标与 step 标识可参数化，标识符匹配 `<prefix>-01..0N` | `test_step_namespace` → OK |
| AC-08 | 13,14,22 | S-1 统一编排入口：CLI 与库调用共用同一公开入口；外部命令执行器可注入替身 | `test_public_entrypoint` + `test_injected_runner` → OK |
| AC-09 | 09,14,23,25 | 产出为 markdown 表格含路径指针，可被 `verify-evidence` 直调消费，免二次转换 | `test_markdown_summary` → OK；与战利品管理索引列结构对齐 |
| AC-10 | 15,21,28 | 每件自动化输出含「复用既有共享工具 / 零新增 seam」或「新增 seam 理由与影响」声明 | `test_reuse_declaration` → OK |
| AC-11 | 17,18 | 汇总含自动化覆盖率与剩余手动清单，证据收集后可直接进入八项检查单 | `test_summary_consumable` → OK |
| AC-12 | 23 | 证据片段按 `<prefix>-01..0N` 归档，与战利品管理索引衔接 | `test_artifact_naming` → OK |
| AC-13 | 30 | 退出码三值固定：全通过 0 / 门禁失败 1 / 用法错误 2；不依赖文本输出 | `test_exit_codes` 三态夹具 → OK |
| AC-14 | 30 | 非法输入或 step 标识冲突 → 退出码 2 且 stdout 无 `passed` 字段 | `test_usage_error` → OK |
| AC-15 | 16 | 仅标准库，零第三方运行时依赖 | `py_compile` 全过；`grep -rn "import requests" tools/tooling_automate` 空 |
| AC-16 | 10,16 | 编排层只串联既有门禁脚本，S1/S2 不退化 | `test_no_gate_redefinition`；CI S1/S2 通过 |
| AC-17 | — | 只读编排：不改证据本体、不回写登记簿、不改写报告 | `test_readonly` 断言无副作用调用 |
| AC-18 | 29 | 不含攻击逻辑、不调用 PyRIT 对象图 | `grep -rn "from pyrit\|import pyrit" tools/tooling_automate` 空 |
| AC-19 | — | 全量 `unittest` 通过（0 失败 0 错误） | `python -m unittest discover -s tests -t .` |
| AC-20 | — | 业务代码行覆盖率 ≥80% | `scripts/measure_coverage.py`，门限 80 |

**冲突处理**：AC 之间无互斥；AC-03 与 AC-11 的覆盖率语义一致（手动单列不充数）。

## 2. Testing Decisions

1. **只测外部行为**：断言单位是「任务清单 → 调用序列 / 汇总结果 / 退出码」，不断言内部私有结构。AC-06 的替身调用计数是唯一例外，理由为「单一事实源」本身是验收对象。
2. **替身边界**：外部命令执行器、文件系统、各校验脚本经 S-1 注入点替换；不 mock 标准库 `json`/`subprocess` 的合法调用。
3. **夹具组织**：以 `TemporaryDirectory` 造任务清单与输出路径；外部命令经 S-1 注入替身，不依赖真实演练目标；另留真实脚本串联用例证明可跑性。
4. **红—绿—重构**：每条 AC 先写失败用例（红）并保留输出摘要，再最小改动转绿，最后重构复跑。
5. **参考测试**：证据收集工具自测（断言三件套、严格模式）、各校验器自测（合规/不合规夹具）；标准库 `unittest`。
6. **US-24（复现）**：任务清单与调用序列均为文本，CI 与本地同一份，`--dry-run` 输出可供人工 copy/paste 复现。

## 3. CI 门禁映射

| AC | CI 阶段 | 落地检查 |
|---|---|---|
| AC-01…AC-14,17,18 | S2 | `python -m unittest discover -s tests -t .` |
| AC-15,16,18 | S1 | `py_compile` + `grep` 依赖/pyrit 检查 |
| AC-19 | S1+S2 | `unittest` 全量 |
| AC-20 | S2 | `scripts/measure_coverage.py`（门限 80） |
| 全 AC | S1 | `validate_skill.py`、`check_glossary.py`、`check_token_budget.py --check` |

## 4. 收敛决策（对象图与 seam）

- **seam 定案**：仅 **S-1 统一编排入口** 1 处（v1 §4 已与用户核对）。v2 固定其形状：CLI 与库调用共用同一公开入口；外部命令执行器作为可注入参数挂在入口，接收 `(task, runner) → result`，使测试替身替换真实脚本调用。
- **既有接缝复用**：证据收集工具 `--step/--strict` 命令行边界、各校验脚本退出码边界均为现成接缝，不另立证据实现与判据。
- **模块边界**：实现于 `tools/tooling_automate/`（单包路径），内部按「清单解析 / 编排执行 / 汇总输出」分层，不为分层新增包目录（避免改动 CI 接线）。
- **零第三方依赖**：仅标准库 `argparse`/`subprocess`/`pathlib`/`unittest`，不改动既有门禁脚本行为。
- **PyRIT**：零依赖不变（B7 判定形式为「无 `pyrit` import」）。

## 5. v1 → v2 差异清单

| # | v1 表述 | v2 收敛 | 理由 |
|---|---|---|---|
| 1 | US-30 合并「非法输入 / 标识冲突」 | 拆为 AC-13（退出码三值）与 AC-14（用法错误无 `passed`） | 静默通过是质量红线，须独立判定 |
| 2 | 「复用既有工具」（软表述） | AC-06：替身断言被调用 | 让「单一事实源」可验证 |
| 3 | 未定义输出结构 | AC-09/AC-11：markdown 表格 + 覆盖率/手动清单 | CI 与 verify-evidence 消费需稳定契约 |
| 4 | 覆盖率口径文字描述 | AC-03：分母=可脚本化全集，手动单列 | 防指标虚高 |
| 5 | seam 提案 | §4：S-1 定案且固定形状 | 供阶段 6/8 直接落地 |
| 6 | 未规定入口形态 | AC-08：CLI 与库共用入口、可注入替身 | 直调可跑性（VG-3） |
| 7 | 未规定只读边界 | AC-17：无副作用调用断言 | 防编排层越权改写 |

## 6. 风险与核实闸

| 编号 | 风险 | 处置 |
|---|---|---|
| VG-1 | 覆盖率分母口径可能被误解 | AC-03 固定分母=可脚本化全集；手动单列不充数（承接阶段 1） |
| VG-2 | 新增 S-1 是否真必要 | AC-08 证明 CLI 与库共用入口且可注入替身；缺它将无法直调与替身测试 |
| VG-3 | 被攻击子技能直调的可跑性 | AC-08 + 真实脚本串联用例；阶段 8 实跑证明 |
| VG-4 | 目标环境约束（演练目标 IP） | 编排不依赖真实目标；外部命令经 S-1 注入替身，CI 全绿即可 |

> 版本：v2 · 2026-11-15 · 取代 v1 作为下游（阶段 4/6/8/9/10/11）唯一判据；v1 保留全文于 issue #240 与本目录 `-spec-v1.md`。
