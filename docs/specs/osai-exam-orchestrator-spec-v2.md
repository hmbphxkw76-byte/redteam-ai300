# osai-exam-orchestrator 工程规格 v2（可验证性收敛）

> 回溯整理：依据 `skills/osai-exam-orchestrator/SKILL.md` 与既有实现、测试归纳；**不代表原流程按序执行**。
> 整理日期：2026-11-27　状态：定稿（v2）

## 1 v1→v2 差异清单

1. 五域行为描述改写为 18 条布尔验收条件（AC-01～AC-18），每条指向 `tests.osai_orchestrator.*` 的具体模块。
2. 「有失败用例与通过用例」细化为按能力域计数：manifest 口径 120 例 / 8 模块；全目录实跑 127 例 / 9 文件。
3. 增加工程约束的可机读判据：第三方 import 白名单、既有技能文件未被修改、证据契约原文未变。
4. 覆盖率由「≥80%」细化为目标名 `osai-orchestrator` 的实测值，并登记逐模块行覆盖率。
5. 补充交接/网关与考试流水的验收条件（AC-16～AC-18），并说明其测试归属另一覆盖率目标。
6. 风险清单新增命名三处不一致、模块数随交付增长（7→10）、原阶段 11 未推送与现存 PR 的差异。

层次关系：本规格为技能级全量定稿；`osai-exam-readiness` 与 `osai-handoff-gateway` 规格是后续变更域收敛，只作补充证据，AC-16/AC-17 仅覆盖其在本技能实现包内的交接与网关能力，不扩张其变更域范围。

## 2 布尔验收条件

| ID | 验收条件（真/假可判定） | 测试模块 |
|---|---|---|
| AC-01 | 同工具达 5 次或总数达 10 次时监控返回提示；未达阈值返回继续 | `test_supervision` |
| AC-02 | 连续失败 3 次且无恢复动作时反思判定为终止 | `test_supervision` |
| AC-03 | 通用配额 100 / 受限 20；超限返回 `BLOCKED`；负数入参抛 `ValueError` | `test_supervision` |
| AC-04 | 栅栏四条件未全满足时返回 `ask`，全满足才返回 `done` | `test_supervision` |
| AC-05 | 计划步数落在 3–7、`step_id` 唯一、缺验证点被拒；`wrap` 产出包裹文本 | `test_planning` |
| AC-06 | 精化四类操作均生效，已完成步骤的修改被拒 | `test_planning` |
| AC-07 | 人环五类控制均可用，状态查询先于变更、单次只接受一动作 | `test_planning` |
| AC-08 | 摘要被标记为历史；检索片段中的指令式文本只被标记、不被执行 | `test_governance` |
| AC-09 | 压缩结果保留 IP、证据路径、步骤标识，且不新增建议 | `test_governance` |
| AC-10 | 地址/域名/凭据/令牌被替换为占位符；白名单拒绝非方法论内容 | `test_governance` |
| AC-11 | 独立复核逐条对照原始要求，只引用报告位置，不引用执行者结论 | `test_governance` |
| AC-12 | 模板缺变量返回 `BLOCKED`；本体自造词被拒 | `test_governance` |
| AC-13 | 类型/角色外的工具被拒；调用 ID 归一化并可修复残缺参数 | `test_tooling` |
| AC-14 | 确定性错误零重试，瞬时错误按策略重试 | `test_tooling` |
| AC-15 | 检索命中含目标标识或非本地来源被拒，上限 5 | `test_tooling` |
| AC-16 | 六段交接各返回 PASS/BLOCKED 与理由；D11 网关结果与逐段判定一致 | `test_handoff`、`test_d11_gateway` |
| AC-17 | 考试阶段流水线在阶段门禁未通过时不推进 | `test_exam_flow` |
| AC-18 | 模块零第三方 import；既有技能/工具/证据契约原文未被修改 | `test_orchestrator_evidence_contract` |

## 3 测试决策

- 全部使用标准库 `unittest`；每域含通过用例与失败用例，失败用例以「拒绝/`BLOCKED`/抛错」为断言，不断言内部实现细节。
- 外部命令不真跑：`CommandRunner` 以 `FakeRunner` 替换；`SubprocessRunner` 只在 CLI 路径使用。
- 复验命令：`python -m unittest discover -s tests/osai_orchestrator -t . -q` → 127 例 OK；manifest 口径 120 例 / 8 模块（`test_exam_flow` 计入 `osai-exam-readiness` 目标）。
- 红→绿历史：阶段 9 记录为「红：2 例失败（导入错误 + 缺校验）→ 绿：90 例通过」，该数字为首次合入时的切片，不是当前值。
- 覆盖率：`python scripts/measure_coverage.py --target osai-orchestrator` → 767/824 = 93.1%（门槛 80%）。

## 4 门禁映射

| 验收条件 | G0 基线 | 判据命令 / 人工判据 |
|---|---|---|
| AC-01～AC-04 | B3、B6 | `test_supervision` 全绿 |
| AC-05～AC-07 | B3、B6 | `test_planning` 全绿 |
| AC-08～AC-12 | B2、B3 | `test_governance` 全绿；`check_glossary.py` PASS |
| AC-13～AC-15 | B3、B7 | `test_tooling` 全绿；零 PyRIT import |
| AC-16 | B4、B5 | `test_handoff`、`test_d11_gateway` 全绿 |
| AC-17 | B3 | `test_exam_flow` 全绿 |
| AC-18 | B1、B4、B8 | `test_orchestrator_evidence_contract` 全绿；`py_compile` 通过 |
| 覆盖率 | B6 | `measure_coverage --target osai-orchestrator --min 80` |

## 5 证据与可观测性

- 逐模块行覆盖率（同次复跑）：models 88.6%、supervision 98.1%、planning 92.6%、governance 98.2%、tooling 95.7%、runner 95.0%、cli 88.9%、handoff 89.4%、d11_gateway 84.4%；合计 767/824。
- 可观测入口：`python -m tools.osai_orchestrator --plan` 列出能力域；`--anonymize` 返回占位符化结果，两者均无副作用。
- 留痕指针：`docs/research/osai-orchestrator-canonical.md`（一手源）、`docs/operations/osai-orchestrator-design.md`（seam）、`docs/operations/osai-orchestrator-gates/stage-gates.md`（11 阶段）、PR #441、提交 `4ec49d8`。
- 不落盘目标地址、凭据或 flag 明文；证据以路径引用。

## 6 风险与待验证

- 命名三处不一致（技能目录 / 实现包 / 覆盖率目标）：已在本规格显式登记，未做重命名；消费方检索时需同时匹配三者。
- 模块数随交付增长：首次合入 7 模块，现状 10 模块（新增 handoff、d11_gateway、exam_flow）；门禁记录中的旧数字是历史切片，非当前事实。
- `exam_flow` 位于实现包内但计入 `osai-exam-readiness` 覆盖率目标；按目录统计覆盖率会与按目标统计产生差异。
- 原阶段 11 留痕记为推送/PR 为 N/A（用户指令不推送），现存 PR #441 为后续合入载体，二者非同一动作，不可互证。
- 阈值（5/10/3/100/20/5）目前为默认常量；CLI 的 `--config` 仅做 JSON 载入与形态校验，未接入阈值应用，配置化能力未验证。
- 未验证项：压缩后语义等价、跨模型调用 ID 的全部形态、并行调用下的监控计数一致性。
