# 阶段 8 门禁记录 — `implement-spec`

- 交付物：`tools/verify_evidence.py`（S-1…S-4 四层重写）；SKILL 增补「执行入口」段；`measure_coverage.py` 注册 verify-evidence 目标
- 工单：T1–T5（#206–#210）

| 编号 | 判定 | 证据（命令 + 摘要） |
|---|---|---|
| B1 | 符合 | `validate_skill.py` → PASS（16 技能） |
| B2 | 符合 | `check_glossary.py` → PASS |
| B3 | 符合 | `py_compile` 3 文件 OK；`check_token_budget --check` 无超限 |
| B4 | 符合（豁免） | S1-only 不产 per-step 片段；以 32 用例断言（阶段 9 详列） |
| B5 | 符合 | 双通道/访问证明为布尔判据（AC-06/07），无 mock 放行 |
| B7 | 符合 | `grep -c pyrit tools/verify_evidence.py` → 0 |
| B8 | 符合 | 每个 `check_*` docstring 标 §条款；G1–G7 全对位 |
| AC 对位 | 符合 | AC-01→`from_loot`；03→`check_vrf01`；04→`check_vrf02`；05/17→`_pieces`；07→`_access_proof`；11→`_check_window`；14→`check_proof_single`；15→`verify` |
| 凭据 | 符合 | 全文无 token/密码字面量 |

**变异说明（诚实记录）**：`check_proof_single` 由 flag 子串匹配改按 `domain-controller` 键（AC-14），2 个既有夹具失配；按 v2 语义修正夹具，断言未放宽。
**阶段 10 更正**：B5 原述「已执行」过强，实际形式为「判据实现 + 用例断言」。

**结论：PASS**（不符合项 0）。
