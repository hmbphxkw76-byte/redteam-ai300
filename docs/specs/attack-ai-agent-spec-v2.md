# attack-ai-agent — 工程规格 v2（历史留痕回填）

> v1 → v2：补布尔验收条件、测试决策与门禁映射；v1 全文保留不改。
> 整理日期：2026-11-27　状态：定稿（v2）

## 0. v1 → v2 差异清单

- 新增 AC-01…AC-22，均为布尔判定，来源为 SKILL.md 的「质量门」「校验标准」「失败与豁免」。
- 新增测试决策：只测外部行为、假后端零依赖、真实 seam 不在 CI 打真实目标。
- 新增门禁映射：每条 AC 指向真实测试模块或门禁脚本。
- 新增证据与可观测性：证据片段、步骤标识、AI 日志、覆盖率记录口径。
- 新增风险与待验证：历史记录与当前复跑的差异、缺失的历史留痕。
- v1 七节内容不改，冲突时以 v1 的行为定义为准。

## 1. 验收条件（AC-01…AC-22，布尔）

| AC | 验收条件（必须 / 不得 / 至少） | 测试模块 |
|---|---|---|
| AC-01 | 每个攻击步骤必须完成枚举、朴素攻击、检测、规避、确认五环；缺任一环不得判完成 | `tests.attack_ai_agent.test_attack_ai_agent_ch3_contract` |
| AC-02 | 每步必须给出可直接 copy/paste 的确切命令；含未加引号占位符的命令不得入库 | `tests.attack_ai_agent.test_attack_ai_agent_evidence_contract` |
| AC-03 | 每步必须记录关键输出，含生效或越权响应原文；不得只记录状态码 | `tests.attack_ai_agent.test_attack_ai_agent_runner` |
| AC-04 | 每步必须有访问证明截图，含目标标识与时间戳；不得以空文件或占位图冒充 | `tests.attack_ai_agent.test_attack_ai_agent_evidence_contract` |
| AC-05 | 检测证据必须同时含触发规则名、规避盲点、无新告警确认；缺一不得判通过 | `tests.attack_ai_agent.test_attack_ai_agent_ch3_contract` |
| AC-06 | 检测通道不可达时必须记 `UNDETERMINED` 并注明无法验证告警；不得推断无告警 | `tests.attack_ai_agent.test_attack_ai_agent_ch3_contract` |
| AC-07 | 越权或跨会话读取必须在输出中回显他人实体内容；仅 200 空响应、仅成功字样、仅自身会话变化不得判生效 | `tests.attack_ai_agent.test_attack_ai_agent_runner` |
| AC-08 | AI 交互日志必须含提示、模型名、输出、采纳或修改四项 | `tests.attack_ai_agent.test_attack_ai_agent_adapters` |
| AC-09 | flag 必须面板提交值与截图双通道一致，且截图同屏含 `whoami`/`id` 与 flag | `tests.attack_ai_agent.test_attack_ai_agent_evidence_contract` |
| AC-10 | 每步证据必须经共享证据工具以严格模式产出，且结构兼容报告模板 | `tests.attack_ai_agent.test_attack_ai_agent_evidence_contract` |
| AC-11 | 12 个稳定步骤标识必须与可执行步骤一一对应，且各出现一次 | `tests.attack_ai_agent.test_attack_ai_agent_evidence_contract` |
| AC-12 | 效果分级必须区分完全生效、部分生效、未生效、已跳过；不得夸大 | `tests.attack_ai_agent.test_attack_ai_agent_runner` |
| AC-13 | 无持久化记忆或无可调用工具时，必须记录依据并跳过对应路径，不得阻塞其余路径 | `tests.attack_ai_agent.test_attack_ai_agent_runner` |
| AC-14 | 朴素攻击触发规则后不得跳过检测与规避；必须换新手法复验无告警，不得原样重放 | `tests.attack_ai_agent.test_attack_ai_agent_ch3_contract` |
| AC-15 | 单一规避格式被拒时不得判向量无效；必须记录各格式接受情况并换用其它格式 | `tests.attack_ai_agent.test_strategies`（模式库间接） |
| AC-16 | 记忆投毒必须验证跨会话存活并影响自身会话之外对象；仅自身会话变化不得判有效 | `tests.attack_ai_agent.test_attack_ai_agent_adapters`（持久化断言间接） |
| AC-17 | 工具校验落差必须三态判定（有落差、无落差、`UNDETERMINED`）；证据不足不得臆断 | `tests.attack_ai_agent.test_validation_gap` |
| AC-18 | SQL→OS 升级必须标注命令来源、回显真实输出；不得伪造回显 | `tests.attack_ai_agent.test_validation_gap` |
| AC-19 | 未安装 PyRIT 时必须能由同协议假后端验证外部行为；顶层导入不得依赖 PyRIT | `tests.attack_ai_agent.test_attack_ai_agent_adapters` |
| AC-20 | Capstone 五环链必须完整；缺任一环不得判通过 | `tests.attack_ai_agent.test_attack_ai_agent_ch3_contract`（五环锚点间接） |
| AC-21 | 多轮渐进攻击必须保持同一会话标识；不得跨会话拼接意图 | `tests.attack_ai_agent.test_dialogue` |
| AC-22 | 证据与实现术语必须符合 `GLOSSARY.md`；出现废弃术语不得通过 | `tests.attack_ai_agent.test_attack_ai_agent_evidence_contract` |

## 2. 测试决策

- 只断言外部行为：步骤标识、对象图形态、分级结果、证据字段、命令安全性，不测 PyRIT 内部实现。
- 单一真实 seam 由真实后端承载；测试注入同协议假后端，未装 PyRIT 也可全量运行。
- 真实 PyRIT 路径只做接口与延迟导入断言，CI 不连接真实目标、不读取凭据。
- 证据断言以共享证据工具的严格模式为准，不用自造夹具替代契约。
- 单步模式用于复现与定位，批量模式用于全路径回归。
- 历史留痕口径为 6 个测试模块、66 例；当前树复跑为 8 个模块、93 例，差异见 §5。

## 3. 门禁映射

| 验收范围 | 基线 | 命令 | 判定口径 |
|---|---|---|---|
| AC-01 / 05 / 06 / 14 / 20 | B1 / B4 | `python -m unittest tests.attack_ai_agent.test_attack_ai_agent_ch3_contract -q` | 五环、检测证据、未确定语义、五环锚点均存在 |
| AC-02 / 04 / 09 / 10 / 11 / 22 | B4 / B5 | `python -m unittest tests.attack_ai_agent.test_attack_ai_agent_evidence_contract -q` | 12 标识、严格模式、双通道、无废弃术语 |
| AC-03 / 07 / 12 / 13 | B3 / B4 | `python -m unittest tests.attack_ai_agent.test_attack_ai_agent_runner -q` | 分级、跳过、越权输出回显 |
| AC-17 / 18 | B3 | `python -m unittest tests.attack_ai_agent.test_validation_gap -q` | 三态、升级步骤、不臆断 |
| AC-08 / 16 / 19 | B3 / B6 | `python -m unittest tests.attack_ai_agent.test_attack_ai_agent_adapters -q` | 零依赖导入、假后端、持久化记忆 |
| AC-15 / 21 | B2 / B3 | `python -m unittest tests.attack_ai_agent.test_strategies tests.attack_ai_agent.test_dialogue -q` | 模式库可加载、会话标识保持 |
| 全量 | B1 / B2 / B3 | `python scripts/validate_skill.py`、`python scripts/check_glossary.py`、`python scripts/check_tools_compile.py` | 三条脚本均 PASS |

## 4. 证据与可观测性

- 证据片段按步骤标识一一落盘，含命令、输出、截图钩子、AI 日志与 flag 载荷。
- 严格模式失败即中止该步，不产出通过结论。
- 检测结论以规则名与告警前后对比表达；不可达时以 `UNDETERMINED` 表达。
- 覆盖率历史记录为 86.1%（747/868 行）；当前树未复测，仓库内无覆盖率产物。
- 测试复跑以 `unittest discover` 输出为准；门禁脚本输出摘要留痕于阶段记录。
- 不引入额外遥测；证据片段即唯一可观测载体。

## 5. 风险与待验证

- 历史口径 66 例 / 6 模块无法在当前树复现：当前为 8 个模块、93 例；本文保留记录值并标注复跑值。
- 覆盖率 86.1%（747/868）无仓库内产物支撑，属记录值，未在本次复测。
- 阶段 4 / 5 未实际开工单，未执行标签与分派；工作项由实现提交承载。
- 阶段 10 无历史双轴审查记录；本次以静态复核与既有测试替代，不等价于原流程审查。
- 阶段 11 未单独开 PR；提交直接入库，缺少 PR 评审与检查名证据。
- 真实 PyRIT 路径依赖外部模型与端点，CI 未实跑；真实目标行为仍需演练环境验证。
- 检测通道可达性与规则命中依赖考试环境，无法在本地自动化复验。
