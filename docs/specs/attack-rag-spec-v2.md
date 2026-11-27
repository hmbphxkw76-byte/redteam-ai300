# attack-rag — 工程规格 v2（历史留痕回填）

> v1 → v2：补布尔验收条件、测试决策与门禁映射；v1 全文保留不改。
> 整理日期：2026-11-27　状态：定稿（v2）

## 0. v1 → v2 差异清单

- 新增 AC-01…AC-23，均为布尔判定，来源为 SKILL.md 的「质量门」「校验标准」「失败与豁免」。
- 新增测试决策：只测外部行为、离线假后端、真实 PyRIT 不在 CI 连接目标。
- 新增门禁映射：每条 AC 指向真实测试模块或门禁脚本。
- 新增证据与可观测性：步骤标识、证据片段、覆盖率口径与复跑命令。
- 新增风险与待验证：历史记录与当前树的差异、无直接用例的条目。
- v1 七节内容不改，冲突时以 v1 的行为定义为准。

## 1. 验收条件（AC-01…AC-23，布尔）

| AC | 验收条件（必须 / 不得 / 至少） | 测试模块 |
|---|---|---|
| AC-01 | 每步骤必须给出可直接 copy/paste 的确切命令；含未处理占位符的命令不得入库 | `tests.attack_rag.test_attack_rag_evidence_contract` |
| AC-02 | 每步骤必须记录关键输出原文（投毒生效或 top-k 变化）；仅状态码不得判通过 | `tests.attack_rag.test_attack_rag_evidence_contract` |
| AC-03 | 每步骤必须有访问证明截图钩子，含目标标识与时间戳；不得以占位图冒充 | `tests.attack_rag.test_attack_rag_evidence_contract` |
| AC-04 | 检索层操纵必须给出 top-k before/after 对照，两表字段结构一致 | `tests.attack_rag.test_attack_rag` |
| AC-05 | 决策影响必须捕获 baseline 与 manipulated 两次结果，可逐字段比较 | `tests.attack_rag.test_attack_rag` |
| AC-06 | 决策改变必须体现他人实体内容或受害者上下文动作；仅风格或排名变化不得判影响 | `tests.attack_rag.test_attack_rag` |
| AC-07 | 每步骤检测证据必须含触发规则名、规避盲点、规避后无新告警确认；缺一不得判通过 | `tests.attack_rag.test_attack_rag_evidence_contract`（片段结构间接） |
| AC-08 | 检测通道不可达时必须记 `UNDETERMINED` 并注明无法验证告警；不得推断无告警 | `tests.attack_rag.test_ch11_evidence_contract` |
| AC-09 | flag 必须面板提交值与截图双通道一致；不一致必须阻断通过 | `tests.attack_rag.test_attack_rag`、`tests.attack_rag.test_attack_rag_evidence_contract` |
| AC-10 | flag 缺失时必须跳过或走等价校验通道；不得伪造或填占位值 | `tests.attack_rag.test_attack_rag` |
| AC-11 | 每步证据必须经共享证据工具严格模式产出，且结构兼容报告模板 | `tests.attack_rag.test_attack_rag_evidence_contract` |
| AC-12 | 稳定步骤标识必须与可执行步骤一一对应，且各出现一次 | `tests.attack_rag.test_attack_rag`、`tests.attack_rag.test_attack_rag_evidence_contract` |
| AC-13 | 证据与实现术语必须符合 `GLOSSARY.md`；出现废弃术语不得通过 | `tests.attack_rag.test_attack_rag_evidence_contract` |
| AC-14 | 命令须可实际执行；检索接口与上传通道的命令不得依赖目标外私密值 | `tests.attack_rag.test_attack_rag_ch5_evidence_contract` |
| AC-15 | 每步须「达成目标」与「无检测触发」同时成立；告警持续不得判通过 | `tests.attack_rag.test_attack_rag_evidence_contract`（结构性间接） |
| AC-16 | 上传前必须完成交战规则确认；上传动作必须登记五字段清单 | `tests.attack_rag.test_attack_rag_ch5_evidence_contract` |
| AC-17 | 只读或无写入通道时必须记录依据并改走间接投毒或降级，不得阻塞其余路径 | `tests.attack_rag.test_attack_rag` |
| AC-18 | 下游与检索解耦时必须如实记录未产生影响，不得夸大 | `tests.attack_rag.test_attack_rag` |
| AC-19 | 仅部分生效时必须记录效果等级（完全 / 部分 / 未生效 / 已跳过） | `tests.attack_rag.test_attack_rag` |
| AC-20 | 温度大于零时必须重复取证取最完整响应并记录次数，不得以单次定级 | 无直接用例（运行期人工取证，未自动化） |
| AC-21 | 上下文超限时必须按行分批读取，仅取所需区段，不得整文件读入 | `tests.attack_rag.test_attack_rag_capability` |
| AC-22 | 重传改名时必须标注混合库残留风险，不得宣称已彻底清除 | `tests.attack_rag.test_attack_rag`（摄取回执间接） |
| AC-23 | 朴素投毒触发规则后不得跳过检测与规避；必须换新手法复验，不得重放同一载荷 | `tests.attack_rag.test_attack_rag_evidence_contract`（检测段间接） |

## 2. 测试决策

- 只断言外部行为：步骤标识、top-k 形态、决策差异、证据字段、分级结果、命令安全性。
- 单一后端 seam 由真实 PyRIT 后端承载；测试注入同协议假后端，未装 PyRIT 也可全量运行。
- 真实模型路径只做接口与延迟导入断言；CI 零网络、不连接真实目标、不读取凭据。
- 证据断言以共享证据工具的严格模式为准，不用自造夹具替代契约。
- 单步模式用于复现与定位，全路径模式用于回归；Ch5/Ch11 增量各自独立步骤集合。
- 历史验证记录为 89 例、覆盖率 92.0%（1139/1238）；当前树全目录 125 例、清单口径 102 例、覆盖率 92.0%（1307/1421）。

## 3. 门禁映射

| 验收范围 | 基线 | 命令 | 判定口径 |
|---|---|---|---|
| AC-04 / 05 / 06 / 09 / 10 / 12 / 17 / 18 / 19 | B3 / B4 | `python -m unittest tests.attack_rag.test_attack_rag -q` | 80 例通过 |
| AC-01 / 02 / 03 / 07 / 11 / 13 / 15 / 23 | B4 / B5 | `python -m unittest tests.attack_rag.test_attack_rag_evidence_contract -q` | 10 例通过 |
| AC-08 | B4 | `python -m unittest tests.attack_rag.test_ch11_evidence_contract -q` | 3 例通过 |
| AC-14 / 16 | B4 | `python -m unittest tests.attack_rag.test_attack_rag_ch5_evidence_contract -q` | 5 例通过 |
| AC-21 | B3 | `python -m unittest tests.attack_rag.test_attack_rag_capability -q` | 18 例通过 |
| Ch6 适配 | B3 / B6 | `python -m unittest tests.attack_rag.test_attack_rag_ch6 -q` | 4 例通过 |
| 全量 | B1 / B2 / B3 | `python -m unittest discover -s tests/attack_rag -t . -q`；`python scripts/validate_skill.py`；`python scripts/check_glossary.py` | 125 例 OK 且两脚本 PASS |

## 4. 证据与可观测性

- 证据片段按步骤标识一一落盘，含命令、输出、截图钩子、AI 日志与 flag 载荷。
- 严格模式失败即中止该步，不产出通过结论。
- 检测结论以规则名与告警前后对比表达；不可达时以 `UNDETERMINED` 表达。
- 覆盖率以 `python scripts/measure_coverage.py --target attack-rag` 为准，当前 1307/1421 = 92.0%，门槛 80%。
- 测试复跑以 `unittest discover` 输出为准；门禁脚本输出摘要留痕于阶段记录。
- 不引入额外遥测；证据片段即唯一可观测载体。

## 5. 风险与待验证

- AC-20 无自动化用例，属运行期人工取证；不得据本文宣称已由测试覆盖。
- AC-07 / 15 / 22 / 23 为结构性间接覆盖，检测规则名与「无新告警」结论依赖考试环境 Kibana。
- 历史验证记录 89 例与当前树 125 例存在增量差异，源于 Ch5/Ch11 与能力测试的后续新增。
- 真实 PyRIT 后端依赖外部模型与端点，CI 未实跑；离线假后端不能证明真实目标行为。
- 覆盖率 92.0% 的分子分母随清单模块变化，历史记录 1139/1238 与当前 1307/1421 不可直接相减比较。
- 阶段 4 / 5 的历史工单与标签状态以 GitHub 为准，本文只引用，不重新分派。
