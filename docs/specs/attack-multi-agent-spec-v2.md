# attack-multi-agent — 工程规格 v2（历史留痕回填）

> v1 → v2：补布尔验收条件、测试决策与门禁映射；v1 全文保留不改。
> 整理日期：2026-11-27　状态：定稿（v2）

## 0. v1 → v2 差异清单

| # | v1 表述（行为） | v2 收敛（可判定） |
|---|---|---|
| D1 | 每步须先落盘证据再过门 | AC-09/AC-10/AC-11 以「恰好 8 次证据调用 + strict 失败即抛错」机判 |
| D2 | 生效判定不得只看状态码 | AC-16 以「否定式回执不判生效」用例机判 |
| D3 | 效果等级四值互斥、不得夸大 | AC-12 以纯函数四值 + 封顶用例机判 |
| D4 | 截图缺失须标待补录 | AC-13 以空捕获路径单测机判 |
| D5 | 单 agent 回退 | AC-14 以能力缺失分支单测机判 |
| D6 | 术语须符合术语表 | AC-15 以禁用词扫描 + 术语检查器机判 |
| D7 | 命令可复制执行 | AC-17 以 5 个薄壳 dry-run 用例机判 |
| D8 | flag 双通道一致 | AC-08 增补「离线对照组才可启用预言机等价通道」边界（AC-18） |

## 1. 验收条件（AC-01…AC-22，布尔）

| AC | 布尔验收条件 | 测试证据（`tests.attack_multi_agent.*`） |
|---|---|---|
| AC-01 | a2a-01 证据含总线/记忆端点清单与正常协作基线 | `runner.RunnerTests.test_full_run_all_eight_evidence` |
| AC-02 | a2a-02 命令可原样执行且输出含注入后响应原文 | `units.A2AClientTests.test_bus_actions` |
| AC-03 | a2a-03 命令含冒充身份参数且输出含冒充生效响应 | `units.A2AClientTests.test_bus_actions` |
| AC-04 | a2a-04 证据含投毒前后记忆值对照 | `units.A2AClientTests.test_memory_and_orchestrator`；`runner.RunnerTests.test_a2a_04_write_rejected_is_uneffective` |
| AC-05 | a2a-05 证据含注入前后共享上下文差异 | `units.A2AClientTests.test_memory_and_orchestrator` |
| AC-06 | a2a-06 证据含伪造任务与编排偏离响应 | `units.A2AClientTests.test_memory_and_orchestrator` |
| AC-07 | a2a-07 证据含 trace 差异与 AI 交互日志引用 | `runner.RunnerTests.test_full_run_all_eight_evidence` |
| AC-08 | flag 取证含访问身份证明且双通道取同源值 | `runner.RunnerTests.test_a2a08_panel_channel_gated_by_local_only` |
| AC-09 | strict 校验缺件套时抛错而非静默通过 | `runner.RunnerTests.test_evidence_gate_failure_raises` |
| AC-10 | 全路径运行恰好产生 8 次证据调用 | `evidence_contract.AttackMultiAgentEvidenceContractTests.test_exactly_eight_evidence_calls` |
| AC-11 | 8 个步骤 ID 均声明且有证据调用 | `evidence_contract.*.test_all_eight_steps_declared_with_evidence_calls` |
| AC-12 | 效果等级四值互斥且本地自证封顶 | `units.GradeTests.test_four_levels`／`test_caps`／`test_derive_all_steps` |
| AC-13 | 无截图环境标记待补录且不生成伪造文件 | `units.EvidenceShotTests.test_captures` |
| AC-14 | 目标无协同面时判跳过并建议回退技能 | `runner.RunnerTests.test_capability_missing_single_agent` |
| AC-15 | 技能文本与模型层不含废弃术语 | `evidence_contract.*.test_no_avoid_terms_in_skill`；`units.ModelTests` |
| AC-16 | 仅状态码或否定式回执不判生效 | `units.ModelTests.test_message_accepted_rejects_negated_receipt` |
| AC-17 | 5 个顶层示意脚本可离线渲染同源命令 | `tools.DryRunTests`（5 个 dry-run 用例） |
| AC-18 | 预言机等价通道仅在离线对照组启用 | `runner.RunnerTests.test_local_only_capped` |
| AC-19 | 对象图声明外部基准为主、PyRIT 仅补位且懒导入 | `units.PyritSeamTests.test_lazy_import_error`；`runner.RunnerTests.test_use_pyrit_passthrough` |
| AC-20 | 单步与路径切片只跑所选步骤且未知步骤报错 | `units.StepsTests`；`runner.RunnerTests.test_paths_override_branch` |
| AC-21 | 业务代码行覆盖率不低于 80% | `measure_coverage --target attack-multi-agent` → 89.4% |
| AC-22 | 关闭证据输出时不产生落盘副作用 | `runner.RunnerTests.test_emit_false_no_evidence` |

## 2. 测试决策

- 只断言外部行为：证据片段字段、退出码、判定标签，不断言私有函数调用序列。
- 外部依赖一律走注入点替身：假 HTTP 客户端、记录型证据写入器、空截图捕获、内建扫描器，保证全目录离线可跑。
- 证据契约单独成模块，锁定步骤数与每步调用形态，防止新增步骤时静默破坏契约。
- 顶层示意脚本以 dry-run 覆盖命令渲染一致性，真实网络路径只测可达/不可达两类退出码。
- 覆盖率口径按技能目录统一统计，阈值 80%，实测值随复跑记录，不用历史数字替代。
- PyRIT 路径只验懒导入报错与开关透传，成功路径依赖真实环境，按设计留作带取证方式的人工核实。

## 3. 门禁映射

| 门禁基线 | 覆盖的 AC |
|---|---|
| B1 技能解剖结构 | AC-11、AC-15 |
| B2 术语与决策一致 | AC-15 |
| B3 语法与构建 | AC-17、AC-21 |
| B4 证据契约 | AC-01…AC-11、AC-22 |
| B5 证据与 flag | AC-07、AC-08、AC-18 |
| B6 CI 门禁 | AC-21 |
| B7 PyRIT 版本与对象图 | AC-19 |
| B8 可追溯性 | AC-10、AC-11 |
| B9 框架选型合规 | AC-19 |

## 4. 证据与可观测性

- 每步证据统一经共享证据工具落盘，结构为命令、输出、截图，A2A 步骤追加 AI 交互日志。
- 运行期输出与落盘内容同源，避免「报告写的」与「实际跑的」分叉。
- 判定标签与效果等级进入结构化报告，报告与测试断言使用同一枚举，避免两套口径。
- 失败分支可观测：证据门失败、扫描器异常、目标不可达分别映射为不同退出码与错误类型。
- 覆盖率与用例数为可复跑指标，记录命令而非结论快照。

## 5. 风险与待验证

- R1 外部基准与扫描器为可选依赖，默认内建实现保证离线可跑；实测适配器未在 CI 覆盖。
- R2 PyRIT 成功路径未在 CI 验证，仅在真实环境按人工核实流程补证。
- R3 真实目标的 AI 交互日志需实测响应替换离线构造串，属取证环境约束。
- R4 高价值目标可能启用消息签名或注册认证，本技能按豁免记录，不评估绕过。
- R5 覆盖率随模块增长可能回落，需在每次新增模块后复跑而非沿用历史值。
