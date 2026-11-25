# OSAI AI300 对齐优化：评估、实施与后续规划（演练态 · 非提交件）

> 规格源：issue #446（v1/v2）；实现 PR：#451；门禁记录：`docs/operations/osai-exam-readiness-gates.md`
> 本文件不含真实 flag、OSID、截图或考试环境事实。

## 1. 优化目标（按考试杠杆排序）

| 目标 | 官方依据 | 分值/条款 |
|---|---|---|
| G1 消除证据误报 | 快照 §4 取消资格条款 | 直接决定目标是否得分；最高优先 |
| G2 八目标单一事实源与只读证据链 | 快照 §2 计分模型 | 4×15 + 15 + 2×10 + 5 = 100；及格 75、工程目标 ≥85 |
| G3 阶段首尾衔接可判定 | 快照 §1 每阶段截图与复现 | 报告完整度是给分条件 |
| G4 报告与提交件本地预检 | 快照 §6/§7 | PDF/.7z 命名、无密码、≤100MB、MD5；错即不予计分 |
| G5 治理收口与可发现性 | GOVERNANCE §8.2 / AGENTS C1–C8 | 不增分但防回归与并发冲突 |

## 2. 关键改动范围

- 修改：`tools/collect_evidence.py`、`docs/contracts/collect_evidence.contract.md`、`docs/contracts/consumers.md`、`scripts/tools_manifest.json`、`scripts/measure_coverage.py`、`tests/shared_tools/test_collect_evidence.py`。
- 新增：`tools/evidence_pipeline.py`、`tools/osai_orchestrator/exam_flow.py`、`tools/report_exam/preflight.py`、`scripts/validate_skill_mainline.py`；对应四个测试模块；规格/调研/设计/门禁/状态/目标映射六类文档。
- 本轮追加改动：17 份 `SKILL.md` 主线指针、24 份根层影子规格归档、两份幽灵技能 `SKILL.md` 与规范路径规格/门禁、报告回填模块、CI 独立校验步骤。
- 未改：`GLOSSARY.md`、CI 工作流并发长行、官方报告模板、既有演练证据。

## 3. 实施清单（需求 → 动作 → 验证 → 预期 → 实际）

| 需求项 | 实施动作 | 验证方法 | 预期结果 | 实际状态 |
|---|---|---|---|---|
| R1 截图必需件不得由钩子满足 | `collect_evidence.py` 增 `--exam`，`_is_real_screenshot` 校验 PNG(IEND)/JPEG(EOI)；`shot_status` 考试态三值一致 | `test_exam_mode_*` 3 例 + golden 解析 | 钩子-only `complete=false`、strict 退出 1；演练模式不变 | 已完成；9 例通过 |
| R2 计分目标双通道 | 增 `--scored-target`，双通道不一致不计完整 | `test_scored_target_requires_flag_dual` | 缺双通道 BLOCKED，`--flag` 单值兼容 | 已完成 |
| R3 八目标映射单一事实源 | 新增 `docs/operations/osai-target-map.md`（8 行 / 100 分） | `check_targets` 行数与分值断言 | 无真实 flag；缺项可定位 | 已完成；实测 BLOCKED 8 项 |
| R4 只读证据管线 | 新增 `tools/evidence_pipeline.py`，解析片段 + 真实截图 + 双通道 | 3 例单测 + CLI 实跑 | 不写证据；缺件输出路径 | 已完成；CLI 退出 1 |
| R5 阶段首尾衔接 | 新增 `exam_flow.py`，固定 9 阶段，消费 `handoff.all_checks` H1–H6 | 6 例单测（含全绿/中途失败） | 交接失败停留当前阶段 | 已完成 |
| R6 报告占位发现 | 新增 `scan_report_placeholders`，输出文件:行号 | 2 例单测 | 占位符含文件与行号 | 已完成 |
| R7 提交规则与 MD5 | 新增 `check_submission`：命名/无密码/≤100MB/仅 PDF/本地 MD5 | 6 例单测（probe 注入） | 违反任一规则 BLOCKED | 已完成 |
| R8 主线与孤儿规格可发现 | 新增 `validate_skill_mainline.py --strict` | 4 例单测 + 全仓实跑 | 17 技能指针缺口、24 根影子规格可见 | 已完成 |
| R9 契约同步 | 契约 v5、新增开关/语义/`missing` 标签；消费者登记新行 | 契约清单 + 消费者断言 | PASS | 已完成 |
| R10 覆盖率门禁覆盖新代码 | `tools_manifest.json` + `measure_coverage.py` 注册新目标 | `--target osai-exam-readiness --min 80` | ≥80% | 已完成；86.6% |

## 4. 需求对齐矩阵

| 需求项 | 现状差距 | 对应改动 | 验证依据 | 得分优先级 | 结果说明 |
|---|---|---|---|---|---|
| 面板+截图双通道（§4） | 钩子被当截图，片段误报齐全 | R1/R2 | `tests/shared_tools/test_collect_evidence.py` | P0-最高 | 已消除误报；正式考试仍须真实截图 |
| 每步命令/输出/截图（§1） | 仅片段层满足，PNG 未落盘 | R1/R4 | `test_evidence_pipeline.py` | P0 | 管线只读报缺口；不代填 |
| 8 目标 100 分（§2） | 无单一事实源，仅散落登记簿 | R3 | 8 行 / 100 分断言 | P0 | 已建表，全部未就绪 |
| 报告可复现（§1） | 骨架含占位文本 | R6 | `test_preflight.py` | P0 | 可发现并定位，回填须人工 |
| PDF/.7z/MD5（§6/§7） | 无实现、无提交件 | R7 | `test_preflight.py` | P0 | 本地门禁就绪；未生成伪提交件 |
| 阶段衔接（§1） | 编排器只被动校验 | R5 | `test_exam_flow.py` | P1 | 状态机就绪，仍需真实 handoff 输入 |
| 技能主线（AGENTS/GOVERNANCE） | 0/17 引用唯一可信源；24 影子规格 | R8 | `validate_skill_mainline.py` 实跑 | P1 | 可发现；未批量改技能正文 |
| 24h+24h 时间窗（§5） | 无时间锚实测 | 本轮未改 | `preflight.py` 仅预留 submission 三元组 | P2 | 待考试窗口验证 |
| AI 交互日志入报告（S1+§7） | 片段层已有，报告回填未自动化 | 本轮未改 | `report-exam` 既有契约 | P1 | 列为后续规划 |

## 5. 验证标准

| 门禁 | 命令 | 判定 |
|---|---|---|
| 全量测试 | `python -m unittest discover -s tests -t .` | Ran 1472，OK (skipped=3) |
| 覆盖率 | `python scripts/measure_coverage.py --target osai-exam-readiness --min 80` | 369/426 = 86.6%，PASS |
| 术语 | `python scripts/check_glossary.py` | PASS（66 废弃术语） |
| 预算 | `python scripts/check_token_budget.py --check` | PASS |
| 技能 | `python scripts/validate_skill.py` | 17/17 PASS |
| 契约 | `check_contract_manifest.py --check` + `check_contract_consumers.py --check` | 双 PASS |
| 证据链实况 | `python tools/evidence_pipeline.py --target-map docs/operations/osai-target-map.md --root .` | BLOCKED 8 项（如实） |

## 6. 风险控制

| 风险 | 规避动作 | 状态 |
|---|---|---|
| 既有 17 技能回归 | 考试模式 opt-in；默认语义与节标题不变 | 已验证：1472 测试通过 |
| 契约漂移 | v5 同步签名/语义/consumers；golden 解析回归 | 已验证 |
| 并发会话共享文件冲突 | 隔离 worktree + 分支；仅新增独立脚本与少量行；推送前锁检查 PASS | 已验证 |
| 证据伪造 | 管线只读；不生成 PNG/flag/PDF/.7z；状态文档标「演练」 | 已验证 |
| CI 检查 | S1/S2/AC-12 pass；S3/S4 因 `ci.yml:138,179` 仅 main 触发而 skipping（预期） | 已验证：PR #451 共 10 条检查无失败；S3/S4 待合入 main 后实跑 |
| 真实考试事实缺口 | 6 项 U 类待核实保持开放 | 待考试窗口 |

## 7. 按得分优先级的可执行建议

1. **P0（立即）**：考试窗口内按 `osai-target-map.md` 逐目标填真实证据；每步用 `--exam --scored-target --strict` 生成片段；任一 BLOCKED 不得进入报告。
2. **P0**：用 `preflight.py` 扫描报告占位文本并在导出 PDF 前清零；提交件命名/MD5 按官方规则复核。
3. **P1**：为 AI 向量 4 台（60 分）与独立机（15 分）优先跑通 recon→证据→report，确保 75 分最小组合；再补传统/DC 25 分冲击 ≥85。
4. **P1**：补齐幽灵技能 `attack-jailbreak` / `attack-multimodal` 的 `SKILL.md` 与主线留痕；迁移 24 份影子规格。
5. **P2**：为剩余 11 技能补齐规范路径规格与阶段门禁记录（本轮只补了指针，不伪造历史结论）；在真实环境中执行 CI S3/S4。

## 8. 后续规划（进入/退出条件）

| 阶段 | 进入条件 | 动作 | 退出条件 |
|---|---|---|---|
| A 阻断清除 | 本 PR 合入 | 真实截图与双通道门禁启用 | 任一目标片段不再误报齐全 |
| B 链路打通 | A 完成 | 用真实 handoff 输入驱动状态机；报告回填自动化 | 单目标从 recon 到 PDF/.7z 端到端通过 |
| C 治理收口 | B 完成 | 幽灵技能、影子规格、技能指针归位 | `validate_skill_mainline.py --strict` 退出 0 |
| D 全量演练 | C 完成 + 真实环境可用 | 8 目标 24h+24h 演练 | 得分 ≥85，提交件 MD5 一致 |

## 9. 假设与信息缺口

- A-1 真实考试环境、OSID、flag、截图不可得；本轮只交付判定与编排能力。
- A-2 现有 `evidence/` / `loot/` 为演练夹具；正式与演练以 `--exam` 区分。
- A-3 共享文件存在并发会话；新增校验为独立脚本/步骤。
- A-4 优先级按 GOVERNANCE §2.3 与技能矩阵 P0→P2。
- A-5 演练语义保留；考试语义 opt-in。
- U-1..U-6 见 `docs/research/osai-exam-readiness-canonical.md` §2，须在考试窗口取证。

## 10. 阶段 11 状态

PR #451 已创建，SSH 推送成功；`gh pr checks 451` 显示 S1/S2/AC-12 pass，S3/S4 按 `ci.yml` 仅 main 触发的设计 skipping。PR OPEN / MERGEABLE，10 条检查无失败；阶段 11 结论 **PASS**，S3/S4 待合入 main 后实跑。
