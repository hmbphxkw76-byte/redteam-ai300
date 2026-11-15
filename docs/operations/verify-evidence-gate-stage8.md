# 阶段 8 门禁记录 — `implement-spec`

- 交付物：`tools/verify_evidence.py`（重写为 S-1…S-4 四层，203 → 564 行）；`skills/verify-evidence/SKILL.md` 增补「执行入口」段；`scripts/measure_coverage.py` 注册 `verify-evidence` 目标
- 工单对应：T1–T5（#206–#210）；变更清单与 AC 对应见 v2 §1

| 编号 | 检查项 | 依据 | 实测结果（命令 + 摘要） | 判定 | 不符合项 | 修正要求 | 复验 | 结论 |
|---|---|---|---|---|---|---|---|---|
| B1 | 技能解剖结构 | §4.2 | `validate_skill.py` → PASS（16 技能） | 符合 | — | — | — | PASS |
| B2 | 术语一致 | §1.3 | `check_glossary.py` → PASS（48 术语） | 符合 | — | — | — | PASS |
| B3 | 语法与构建 | B3 | `python -m py_compile tools/verify_evidence.py tests/test_verify_evidence.py tests/test_report_exam.py` → COMPILE OK；`check_token_budget.py --check` → 无超限、14 锚点齐 | 符合 | — | — | — | PASS |
| B4 | 证据契约 | §6.1 | 本技能 S1-only 不产 per-step 片段；判据以 `tests.test_verify_evidence` 28 用例断言（详见阶段 9） | 符合（豁免理由：SKILL「失败与豁免」末段声明不新增 S2 夹具） | — | — | — | PASS |
| B5 | 证据与 flag | §6.2 | 双通道与访问证明均实现为布尔判据（AC-06/AC-07）；无 mock 掉 flag 比对 | 符合 | — | — | — | PASS |
| B7 | 零 PyRIT 依赖 | ADR-0004 | `grep -c "pyrit" tools/verify_evidence.py` → 0 | 符合 | — | — | — | PASS |
| B8 | 可追溯性 | B8 | 每个 `check_*` 的 docstring 标 §条款；缺口 G1–G7 均在实现中对位 | 符合 | — | — | — | PASS |
| AC 对位 | 每条 AC 有实现位置 | §3.8 | AC-01→`from_loot`；AC-03→`check_vrf01`；AC-04→`check_vrf02`；AC-05/17→`_pieces`；AC-07→`_access_proof`；AC-11→`_check_window`；AC-14→`check_proof_single`；AC-15→`verify` 返回字典 | 符合 | — | — | — | PASS |
| 无硬编码凭据 | §3.8 | B5 | 全文无 token/密码字面量 | 符合 | — | — | — | PASS |

**变异说明（诚实记录）**：`check_proof_single` 由「flag 值子串匹配」改为「按 `domain-controller` 目标键判定」（AC-14），导致 2 个既有用例夹具失配；按 v2 §1 AC-14 语义修正夹具（`tests/test_verify_evidence.py`、`tests/test_report_exam.py`），断言未放宽。

**阶段 10 追加更正**：B5 一行原述「已执行」过强——本技能不产生 per-step 片段，B5 的实际形式是「判据实现 + 用例断言」，已在阶段 10 记录更正；实现与测试在阶段 10 修复后行数/用例数变化（`tools/verify_evidence.py` 551 行、`tests/test_verify_evidence.py` 29 用例），不影响本阶段判定。

**结论：PASS**（不符合项 0），进入阶段 9。
