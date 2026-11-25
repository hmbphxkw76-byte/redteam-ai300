# [spec-v1] attack-jailbreak — 越狱与护栏绕过（PyRIT 1.1.0 原生）

> 阶段 2 `to-spec` ① · 行为规格 v1（What）· 本 issue 为行为唯一来源，SKILL.md 不改写
> 上游：调研 `docs/research/attack-jailbreak-multimodal-canonical.md`（M1–M8）；权威索引 `pyrit-canonical-references.md`
> 标签：ready-for-agent

## 1. Problem Statement

OSAI AI300 考试中 AI 向量机占 75/100，是绝对主分面。当前项目虽在 `attack-ai-agent` 中以 technique 级覆盖"目标劫持/多轮 crescendo"（路径 A-4），并在权威索引登记了 PyRIT 的越狱策略类，但**没有独立的越狱/护栏绕过 skill**：无稳定的步骤契约、无单一 seam 承载多轮越狱策略、无专用评分与证据回灌。面对仅启用护栏加固、需要系统性越狱的 AI 向量机，缺少可复用、可 copy/paste 复现的执行链，影响 attack 阶段得分覆盖。

## 2. Solution

定义一个独立 skill，把"越狱与护栏绕过"行为固化为可验证的多阶段闭环：以 PyRIT 1.1.0 的多轮攻击策略为执行核心，确定性评分器优先、LLM 评分器补充，每步经共享证据工具产出三/五件套并回灌报告。skill 只定义行为/证据/验收，不含实现代码；实现经单一真实 seam 承载，测试经同协议假后端保持零依赖。

## 3. User Stories（行为清单）

- US-01 作为 red teamer，我能枚举目标护栏行为基线（输入过滤/输出审查/拒绝话术），作为越狱效果对照。
- US-02 我能用单轮显式越狱（直接目标劫持）建立 naive 基线并记录触发日志。
- US-03 我能用多轮渐进策略（crescendo 风格）把意图拆到多条无害消息，维持 session 连续性。
- US-04 我能用对抗式多轮策略（PAIR 风格）让攻击模型自动生成越狱提示。
- US-05 我能用树搜索剪枝策略（TAP 风格）在分支中搜索有效越狱路径。
- US-06 我能用重定目标策略（red teaming 风格）驱动多轮对话向越狱目标收敛。
- US-07 我能对越狱载荷做编码/字符变换（base64/ROT13/leetspeak/翻译）绕过关键词过滤。
- US-08 我能以确定性子串评分快速判定越狱是否达成目标；无法确定时转 LLM 评分判定。
- US-09 我能记录每步的确切命令、关键输出、截图，满足三件套。
- US-10 我能记录 AI 交互日志（prompt、模型、输出、采纳/修改），满足五件套。
- US-11 我能对每步产出 `jailbreak-NN` 稳定步骤标识并可 copy/paste 逐步复现。
- US-12 我能把越狱产物 flag 以"面板提交值 + 截图/报告正文"双通道一致回灌。
- US-13 我能对护栏加固目标如实记录"部分生效/未生效"，不夸大判定等级。
- US-14 我能对评分器不确定结果标记 `UNDETERMINED` 而非臆断成功。
- US-15 我能在未安装 PyRIT 的 CI 环境用测试替身验证全部外部行为。
- US-16 我能保证全过程不触发 C8 不可豁免条款的删减。

## 4. Implementation Decisions

- 决策 D1：采用单一真实 seam 承载全部 PyRIT 调用，测试以同协议替身注入，保持 CI 零依赖（C6）。
- 决策 D2：对象图统一采用 1.1.0 的 `pyrit.executor.attack` 多轮策略与执行器，禁用 0.x 编排器名；不引入 1.2.x 新增符号。
- 决策 D3：评分采用"确定性优先、LLM 补充"的分级策略，遵循 C6 运行时纪律。
- 决策 D4：证据逻辑复用共享证据工具，不新造证据契约；步骤标识为稳定契约。
- 决策 D5：越狱策略选择可按目标护栏类型配置，默认从单轮基线起步，逐级升级到多轮。
- seam 提案：唯一真实 seam = BackendFactory 协议下的 RealPyRITBackend；测试替身 = FakePyRITBackend；证据复用共享工具。**已与用户核对采纳。**

## 5. Testing Decisions

- 只测外部行为：步骤标识存在性、策略调用可达性、评分分级正确性、证据字段完整性、确定性输出。
- 测试替身验证不依赖 PyRIT 安装；真实 seam 的 PyRIT 调用以接口断言覆盖，不做真实目标攻击。
- 既有参考测试：`tests/attack_ai_agent/` 的后端/适配器/证据契约测试模式。

## 6. Out of Scope

- 不做 PyRIT 版本升级（本任务全程锁定 1.1.0）。
- 不含 handbook 的高风险代码（C2/后门/主动扫描/社工钓鱼模板）。
- 不含对真实考试目标的利用动作；产物为演练/仿真性质。
- 不新造证据契约、不改 collect_evidence 语义。

## 7. Further Notes

- 框架矩阵偏离：现有矩阵无 jailbreak 条目，按 B9/GOVERNANCE §8.3 显式声明并在阶段 7 补条目。
- 待核实项 Q1/Q2（多模态 target 消息片构造、endpoint 可达性）见调研 §5，属 multimodal；本 skill 不阻塞。
- 版本排除声明：任何 1.2.x 符号不得进入对象图。

## G0 收尾（阶段 2 · B1/B2/B8）

| 检查 | 依据 | 结论 |
|---|---|---|
| 七节齐全 | §2 | PASS |
| US 覆盖全部路径与质量门 | §3 | PASS（16 条） |
| Implementation Decisions 无路径/代码 | §4 | PASS |
| 术语符合 GLOSSARY | B2 | PASS（check_glossary 已过） |
| seam 已与用户核对 | G0 | PASS |
| B8 可追溯（每条附来源） | 全文 | PASS |

阶段 2 结论：PASS（不符合项 0）。
---
