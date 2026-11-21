# attack-ai-agent Ch3 对齐 · 设计记录（主线阶段 6）

> 输入：规格 #295 v2 · 工单 #301/#302-306 · 既有 `tools/attack_ai_agent/` 与 `tools/collect_evidence.py` 契约 v3。
> 性质：设计记录（模块边界与 seam）。依据 `codebase-design` 深层模块词汇。

## 1. seam 清单（零新增）

| seam | 位置 | 职责 | 注入点 |
|---|---|---|---|
| `BackendFactory`（既有） | `tools/attack_ai_agent/backends.py` | 承载 PyRIT 调用；Real/Fake 双实现 | `run_attack(backend_factory=...)` |
| `emitter`（既有） | `runner.py` `emit_evidence` | 证据发送，强制 `--strict` | `run_attack(emitter=...)` |

**结论**：Ch3 增量全部落在行为规格（SKILL.md）与测试契约层，无需新增 seam、无需改动 PyRIT 对象图、`aia-01..12` 冻结不变。与 v1 Implementation Decisions / 矩阵条目①一致。

## 2. 模块职责与依赖方向

| 模块 | 本主线动作 | 输入 | 输出 |
|---|---|---|---|
| `skills/attack-ai-agent/SKILL.md` | 行为规格纳入 Ch3 六组能力（本主线阶段 8 实现并核验） | Ch3 research §1 | 五步闭环 + 技法 + 检测证据 + 无告警验收 |
| `tests/attack_ai_agent/test_attack_ai_agent_ch3_contract.py`（新增） | 文本契约断言：五步闭环五环关键字、六组技法锚点、UNDETERMINED、Ch3 章节锚点存在性 | SKILL.md 文本 | unittest 通过/失败（外部行为，不断言实现细节） |
| `tests/attack_ai_agent/test_attack_ai_agent_evidence_contract.py`（既有，不改） | 12 标识 1:1、三件套、flag 双通道 | steps.py / runner.py / 证据片段 | 既有保证 |

依赖方向：`test_ch3_contract → SKILL.md`（只读文本）；无新增运行时依赖；无环。

## 3. 公开接口 / 错误行为

- 新增测试文件不暴露公开 API；无运行时接口变更。
- 错误行为：断言失败时 unittest 退出码 1，定位到缺失的 Ch3 锚点（如缺 `UNDETERMINED`）。

## 4. 权衡与被否决方案

| 方案 | 结论 | 理由 |
|---|---|---|
| 在 runner.grade() 增 detect/evade/confirm 字段 | 否决 | 触碰冻结契约的语义、需改 12 步证据与 S2 夹具，成本高且超出「行为规格对齐」范围 |
| 新增 aia-13..17 步骤 | 否决 | 违反 aia-01..12 冻结契约，破坏 S2 1:1 断言 |
| 仅靠人工核对、不加测试 | 否决 | AC-11/13 需可自动化判据（CI S1/S2），无测试则 v2 不可判定 |
| 新增独立文本契约测试（采纳） | 采纳 | 只测外部行为、零 seam、零运行时改动、可 CI 复现，最小切片 |

## 5. 对象图（B7）

不变：`pyrit.executor.attack.*Attack` + `OpenAIChatTarget` + `SQLiteMemory`；无 `pyrit.orchestrator` 等旧名；版本锁 `pyrit==1.1.0`。

## 阶段 6 G0

B2 check_glossary PASS（设计无废弃术语）；B7 无旧名（§5）；B8 设计落盘 + issue 互链。上游复核：v1/v2 未被破坏。**不符合项 0，结论 PASS**。

## 阶段 9 `tdd` 红—绿—重构记录（增量）

| 轮次 | 动作 | 实测输出 |
|---|---|---|
| 红 | 临时把 SKILL.md 的 `Attack, naive` → `攻击（naive）`、目标劫持→目标重定向，模拟规格回退 | `FAILED (failures=1)`；`AssertionError: 'Attack, naive' not found`；6 用例中 `test_five_step_loop_all_stages_present` 失败 |
| 绿 | 恢复 SKILL.md（从 /tmp/SKILL_green.md），复跑新契约测试 | `Ran 6 tests ... OK` |
| 重构 | 清理 demo 冒烟产生的 gitignored 运行时证据片段 `evidence/attack-ai-agent/`（仅 aia-02，触发 `test_twelve_fragments_complete` 的目录存在即校验 12 份逻辑） | 全量 `Ran 898 tests ... OK (skipped=3)`；覆盖率 85.0% ≥80% |

**说明**：红阶段用临时副本改 SKILL.md 后即恢复，`git diff` 确认 SKILL.md 未被污染（11977B）。测试环境副作用（冒烟产物）已清理，非代码缺陷。

**阶段 9 G0**：B3 py_compile OK / B4 证据契约 898 OK / B6 覆盖率 85.0%≥80% / B8 红输出留痕。**不符合项 0，PASS**。

## 阶段 10 `code-review` 双轴报告（增量）

固定点：`git merge-base origin/main HEAD` = `831df49`；diff 非空（5 文件）。两轴并行独立审查，不合并。

| 轴 | 硬违规 | 判断项 | 最严重项 |
|---|---|---|---|
| Standards | 2 | 5 | H-1：research 文档含真实 Lab 凭据（S0 secret-scan 违规） |
| Spec | 1 | 4 | H1：同上（新引入字面值，违反 v1 Out-of-Scope 占位符要求） |

**硬违规修复（全部清零）**：
- H-1/H1：research §1.1 Detect 行删除 `elastic/...` 字面值，改 `<SIEM_CREDS>` 占位；§2 待核实行 IP 泛化。复验 `grep -rniE 'yfo60|192\.168\.50\.|192\.168\.40\.189'` 无命中。
- H-2：GLOSSARY「任务清单」恢复七字段枚举（指针目标 tooling-automate SKILL.md 不含该事实，违反 C1）；压缩「编排层」腾出 21B，复验 17470/17500 OK。

**判断项（改进项，不阻断）**：J1 测试内 12000 常量硬编码（建议改用 checker 常量）；J2 预算余量临界（SKILL.md 23B / GLOSSARY 30B）；J3 v2 判据文件引用与新测试文件名的差异（设计 §2 已说明）；J4 IP 已按 H1 一并泛化；J5 红阶段记录依赖临时副本（设计文档已注明恢复机制）。

**复跑结果**：validate_skill / check_glossary / check_token_budget --check / py_compile / ch3-contract 6 例 / markdownlint 全 exit 0。

**阶段 10 G0**：两轴报告并列、硬违规 0、规格覆盖矩阵 13/13 无遗漏、门禁全绿。**结论 PASS**。
