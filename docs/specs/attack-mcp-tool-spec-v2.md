# attack-mcp-tool — 工程规格 v2（历史留痕回填）

> v1 → v2：补布尔验收条件、测试决策与门禁映射；v1 全文保留不改。
> 整理日期：2026-11-27　状态：定稿（v2）

## 0. v1 → v2 差异清单

- 新增 AC-01…AC-25，均为布尔判定；来源为 SKILL.md 的「质量门」「校验标准」「失败与豁免」，并补实现侧工程约束。
- 新增测试决策：只测外部行为、假传输/假截图/本地回环 server、CI 不连真实目标。
- 新增门禁映射：每条 AC 指向真实测试模块或门禁脚本，不引用不存在的用例名。
- 新增证据与可观测性：覆盖率 94.4%（1634/1731）、manifest 口径 116 例、全目录实跑值。
- 新增风险与待验证：历史记录与当前树的差异、D-2 变更域规格的层次、AC 编号口径。
- v1 七节内容不改；冲突时以 v1 的行为定义为准。
- AC 编号为本规格自有口径；用例名中的 `test_acNN_*` 来自历史规格 issue，不保证与本表对应。

## 1. 验收条件（AC-01…AC-25，布尔）

| AC | 验收条件（必须 / 不得 / 至少） | 测试模块 |
|---|---|---|
| AC-01 | 每个攻击步骤必须给出可直接 copy/paste 的确切命令；不得残留未替换的目标占位符 | `tests.attack_mcp_tool.test_attack_mcp_tool_evidence_contract`、`..._runner` |
| AC-02 | 每步必须记录关键输出原文，含投毒生效、越权动作或代码执行回显；不得只记状态码 | `tests.attack_mcp_tool.test_attack_mcp_tool_runner`、`..._poison` |
| AC-03 | 每步必须有访问证明截图，含目标标识与时间戳；截图不可得时必须标「待补录」且不得写空 PNG | `tests.attack_mcp_tool.test_attack_mcp_tool_units`、`..._flag` |
| AC-04 | 投毒必须有前后工具清单对照，差分至少区分新增、移除、变更三类；无变化时必须为空 | `tests.attack_mcp_tool.test_attack_mcp_tool_poison` |
| AC-05 | 下游 agent/工具被操纵必须有决策差异取证，含 AI 交互日志；无提示词的步骤不得伪造日志 | `tests.attack_mcp_tool.test_attack_mcp_tool_flag`、`..._runner` |
| AC-06 | flag 必须面板提交值与同屏截图双通道一致；无 flag 文件时以校验预言机降级并注明依据 | `tests.attack_mcp_tool.test_attack_mcp_tool_flag` |
| AC-07 | 所有步骤证据必须经共享证据工具严格模式产出，结构含四节并可被报告模板复用 | `tests.attack_mcp_tool.test_attack_mcp_tool_flag`、`..._evidence_contract` |
| AC-08 | 任一步骤必须可单步复现；未知步骤标识必须报错退出，不得静默跳过 | `tests.attack_mcp_tool.test_attack_mcp_tool_runner`、`..._units` |
| AC-09 | 每步三件套必须齐全；术语必须符合 `GLOSSARY.md`，不得出现废弃术语 | `tests.attack_mcp_tool.test_attack_mcp_tool_evidence_contract` |
| AC-10 | 11 个稳定标识 mcp-01…mcp-11 必须与可执行步骤一一对应且各出现一次；新增只追加，不得改写既有八步 | `tests.attack_mcp_tool.test_attack_mcp_tool_runner`、`..._ch7_gap` |
| AC-11 | 目标无 MCP、无工具或不可达时必须判「已跳过」并附依据；不得阻塞其余路径 | `tests.attack_mcp_tool.test_attack_mcp_tool_runner` |
| AC-12 | 仅本地自证或仅部分生效时必须如实降级，不得判「完全生效」 | `tests.attack_mcp_tool.test_attack_mcp_tool_ch7_gap`、`..._runner` |
| AC-13 | 越权被护栏拦截时必须判「未生效」并记录拦截原因；不得原样重试同一动作 | `tests.attack_mcp_tool.test_attack_mcp_tool_runner` |
| AC-14 | 疑似诱饵机必须记录判定依据并在 30 分钟内结束；不得在 0 分主机空耗 | 人工判据（无自动化用例） |
| AC-15 | 四值等级必须互斥，理由必须写清目标侧信号与自有判据两侧的命中情况 | `tests.attack_mcp_tool.test_attack_mcp_tool_runner` |
| AC-16 | 定级必须为纯函数，不得依赖 IO、网络或模型框架 | `tests.attack_mcp_tool.test_attack_mcp_tool_runner` |
| AC-17 | 实现必须仅依赖标准库；未安装模型框架时必须可离线全量运行 | `tests.attack_mcp_tool.test_attack_mcp_tool_runner`、`..._units` |
| AC-18 | 对象图必须符合 ADR-0004；不得出现已废弃的编排器对象 | `tests.attack_mcp_tool.test_attack_mcp_tool_runner` |
| AC-19 | 覆盖率必须 ≥90%；记录口径为 94.4%（1634/1731 行） | `scripts/measure_coverage.py --target attack-mcp-tool --min 90` |
| AC-20 | mcp-10 必须产出合法 UI 资源 URI 与隐藏指令，并取证双层 iframe 代理的 postMessage→tools/call | `tests.attack_mcp_tool.test_attack_mcp_tool_ch7_gap` |
| AC-21 | mcp-09 必须证明前缀检查早于路径规范化，并覆盖 symlink 跟随与 realpath 修复对照 | `tests.attack_mcp_tool.test_attack_mcp_tool_ch7_gap` |
| AC-22 | mcp-11 必须串联 store→aggregate→render 三阶段，先 `{{7*7}}` 探针确认再升级命令执行 | `tests.attack_mcp_tool.test_attack_mcp_tool_ch7_gap` |
| AC-23 | shadow 工具面必须与基线 schema 全等、新增工具数为 0、来源不同 | `tests.attack_mcp_tool.test_attack_mcp_tool_ch7_gap`、`..._poison` |
| AC-24 | 本地 MCP server 启停必须幂等、状态可观测、端口独占；注入实例不得被编排层越权关闭 | `tests.attack_mcp_tool.test_attack_mcp_tool_poison`、`..._runner` |
| AC-25 | 严格模式证据写入失败必须中止并报运行错误，不得产出通过结论 | `tests.attack_mcp_tool.test_attack_mcp_tool_runner` |

## 2. 测试决策

- 测试框架为标准库 `unittest`；当前 6 个测试模块、116 个用例，全目录 `discover` 退出码 0。
- 只断言外部行为：步骤标识、结论等级与理由、证据字段、HTTP 请求计数、对象图形态；不断言私有函数。
- 传输缝以 `FakeHttpClient` 注入；证据缝以 `RecordingWriter` 记录；截图缝以 `NullCapture` / `FakeCapture` 替代；server 以本地回环实例验证。
- CI 不连接真实目标、不读取凭据；真实目标验证只作为演练记录，不进自动化门禁。
- 单步模式用于复现与定位，批量模式用于全路径回归；未知标识必须有负向用例。
- 证据契约模块锁定既有八步的严格模式调用；11 步全路径由 runner 的全量用例单独锁定，不混为同一断言。
- 历史 `-tests.md` 的 87.0%（1262/1451）为早期口径；当前以复跑 94.4% 为准。

## 3. 门禁映射

| 验收范围 | 基线 | 命令 | 判定口径 |
|---|---|---|---|
| AC-01 / 03 / 05 / 07 / 09 | B4 / B5 | `python -m unittest tests.attack_mcp_tool.test_attack_mcp_tool_evidence_contract tests.attack_mcp_tool.test_attack_mcp_tool_flag -q` | 三件套、四节结构、AI 日志、双通道、无废弃术语 |
| AC-02 / 08 / 11 / 13 / 15 / 16 / 17 / 18 / 25 | B3 / B4 / B7 | `python -m unittest tests.attack_mcp_tool.test_attack_mcp_tool_runner -q` | 单步、跳过、拦截、四级、纯函数、零依赖、对象图、严格模式失败 |
| AC-04 / 23 / 24 | B3 / B4 | `python -m unittest tests.attack_mcp_tool.test_attack_mcp_tool_poison -q` | 前后差分、shadow 全等、生命周期与端口独占 |
| AC-12 / 20 / 21 / 22 | B3 / B4 | `python -m unittest tests.attack_mcp_tool.test_attack_mcp_tool_ch7_gap -q` | 本地自证封顶、UI 资源、穿越与 symlink、三工具串联 |
| AC-19 | B6 | `python scripts/measure_coverage.py --target attack-mcp-tool --min 90` | 覆盖率 ≥90%，实测 94.4% |
| AC-10 / 全量 | B2 / B3 | `python -m unittest discover -s tests/attack_mcp_tool -t . -q` | 116 例 0 失败 0 错误 |
| 静态与术语 | B1 / B2 | `python scripts/validate_skill.py`、`python scripts/check_glossary.py`、`python scripts/check_tools_compile.py` | 三条脚本 PASS |
| AC-14 | — | 人工判据 | 诱饵机判定与 30 分钟止损仅有流程约束，无自动化 |

## 4. 证据与可观测性

- 证据片段按 `mcp-01…mcp-11` 一一落盘，含命令、输出、截图钩子、AI 日志与 flag 载荷；严格模式失败即中止该步。
- 截图不可得时保留命令与输出并写「截图待补录」，不生成空 PNG，不冒充访问证明。
- 效果等级与理由进入机读报告；理由必须同时陈述目标侧信号与自有判据，禁止只给等级。
- 覆盖率口径为 `--target attack-mcp-tool`：1634/1731 行、94.4%，门槛 90%；仓库内无长期覆盖率产物。
- 用例口径并列：manifest 登记 6 个测试模块、116 例；本次全目录实跑同为 116 例 OK（25.7s），两者统计口径不同但数值一致。
- `check_tools_compile.py` 实测 309 个文件、失败 0；`check_glossary.py` 检查 66 个废弃术语后 PASS。
- 不引入额外遥测；证据片段与机读报告即唯一可观测载体。

## 5. 风险与待验证

- 历史 11 阶段门禁记录缺失，本次为回溯整理，不表示原流程按序执行；阶段 4/5 的覆盖矩阵与 brief 未完整落盘。
- 历史演练记录只覆盖 mcp-01…mcp-08；mcp-09…mcp-11 以单测与本地回环验证为主，缺同一目标的端到端演练记录。
- D-2 规格 `-d2-spec-v1/v2` 只覆盖 server 生命周期与端口独占，不是全技能规格；引用其阶段 10 结论时仅限该变更域。
- `attack-mcp-tool-tests.md` 的 87.0% 为早期口径，与当前 94.4% 并存；阅读时须以日期与分母区分。
- U-2 未关闭：长连接后的端口重绑窗口仍以 50 次短连接近似，未覆盖长连接真实场景。
- 平台差异：Windows 与 Linux 的端口独占语义不同；Windows 全量测试 stderr 会出现 `ConnectionAbortedError` 栈噪声，但退出码为 0。
- 真实目标行为依赖考试环境与模型采样，CI 无法复验；历史验证记录中的目标地址与凭据不进入本文。
- 历史 PR #34/#143/#322 已合并；D-2 变更域无独立 PR，提交直接入库，阶段 11 的 PR 检查名证据仅对该变更域的 CI 记录成立。
