# OSAI AI300 统一优化架构与解决方案：Python 编排为主 + PyRIT 有边界升级

> **性质**：统一权威方案与执行结果确认，非考试提交件。合并同主题材料为单一事实源；
> 未跟踪输入文档 `osai-ai300-hybrid-optimization-solution.md`、`osai-ai300-curated-payloads.md`
> 只读、保持原样，本文件覆盖结论。
> **事实源**：考试规则快照、`GOVERNANCE.md`、`pyrit-integration-verification-2026-11-26.md`、
> `data/strategies.json`、`tools/attack_ai_agent/hybrid.py`、`tests/attack_ai_agent/test_hybrid.py`。
> **边界**：实测来自 DVAA / AIVP 演练目标，非 OSAI 正式考试；`proven` 仅指可复现出现；
> 命中率带分子分母，不作通过承诺。

## 1. 架构与边界

### 1.1 核心判定与三条不变式

**Python 编排是执行主干，PyRIT 只是有边界的可选升级。** 成功率不由载荷本身保证，
而由三条不变式保证：

| 不变式 | 含义 | 落点 |
|---|---|---|
| 双通道 | 面板校验值与截图/正文值同时留痕且一致，缺一即失分或取消资格 | `collect_evidence.py --exam --scored-target --strict` |
| 边打边写 | 命中即固化片段、截图、面板值与 AI 交互日志，不留到对话上下文过夜 | `run_hybrid()` 命中即返回，`fallback=成功即固化` |
| 三态输出 | 区分「未启用 / 启用但不可用 / 已执行带命中数」，禁止布尔值概括 | `HybridResult.escalation` + `executed` + `escalation_result` |

### 1.2 四层结构

| 层 | 组成 | 职责 | 不做 |
|---|---|---|---|
| L0 事实层 | 考试快照、GOVERNANCE、策略库、证据片段 | 提供可追溯事实与命中率口径 | 不推断未实测结论 |
| L1 Python 编排层 | `hybrid.run_hybrid()`、`ChatSpec`、`strategies`、`negation`、`dialogue_cli.py` | 形态适配、策略选择、两次执行、双闸判定、证据落盘 | 不声明 PyRIT 已执行 |
| L2 PyRIT 升级层 | `escalation_gate` → `pyrit_multiturn.run_multiturn`、`--semantic`、`--pyrit` | 默认关闭；显式开启只做多轮与评分补充，输出三态 | 不做首轮主判据；只否决不认定 |
| L3 证据报告层 | `loot-manage`、`verify-evidence`、`report-exam` | 登记、五维校验、四章报告与提交格式 | 不补写考后证据、不伪造 flag/截图 |

数据流：画像 → 策略选择 → L1 → 双闸判定 → 证据落盘 → L3；失败下探 L2 后回流同一证据链。
依赖单向：`hybrid → (dialogue, strategies, negation)`、`hybrid → pyrit_multiturn → pyrit_semantic → pyrit`；
顶层零 pyrit 导入。GOVERNANCE §4.5 流水线不变，只优化对话面执行段。

### 1.3 PyRIT 调用边界

1. **默认不调用**：首轮与常规重试走 L1；`pyrit_executed=false` 且 reason 说明未启用。
2. **显式开启**：仅在 `--pyrit` / `--semantic` / `--multiturn` 或 `user_opt_in=True` 时加载；缺包给版本诊断，不抛异常。
3. **只否决不认定**：语义层仅在确定性命中且非否定语境后触发；返回 False 才覆盖，True/None 维持原判。
   实测对真实泄露误否决 0/3，但认婉拒、不认「我拒绝陈述 X」，故默认关闭。
4. **多轮为最后手段**：四个攻击类在 1.2.1 实测可构造；对加固目标 `RedTeamingAttack`
   三轮 `AttackOutcome.FAILURE`（92.7 秒），不作常规路径。
5. **事实三态**：未启用 / 缺包不可用 / 已执行带命中数，禁止布尔值概括。

### 1.4 升级触发、禁止与冲突裁决

**应触发（缺一不可）**：对话形态（`chat`/`agent_chat`）；objective 非空且单一；tier1 已试且无生效；
即时生成或 tier2 已完成；pyrit 可用且双模型凭据齐；`user_opt_in=True`；
`1≤max_turns≤3`、`1≤timeout≤600`、`prior_escalations<1`。

**不应触发（任一命中即拒，reason 必填）**：非对话形态（工具面/检索面/传统向量）；已有生效载荷；
objective 空；明确拒绝或规则检测；凭据缺失或 pyrit 不可用；未显式启用；tier1 未执行或无补位；轮次/超时/次数越界。

**冲突裁决（优先级高到低，已固化测试）**：硬阻断（凭据、越界、拒绝、检测、已有生效）> opt-in；
tier1 未试完 > opt-in；无 opt-in 一律不升级；opt-in 但 pyrit 不可用则降级为 Python 补位、不报错；
多条冲突全量记入 `conflicts`，不合并。

### 1.5 调用方与被调用边界

| 项 | 约定 |
|---|---|
| 调用方 | 仅 `hybrid.run_hybrid()`；技能脚本不直接 `import pyrit` |
| 被调用范围 | 仅 `pyrit_multiturn.run_multiturn()`；不直接调 `pyrit_semantic.make_*` 或原生类 |
| 输入 | objective、策略 ID、注入载荷、base_url、spec、sender/escalator 替身、pyrit/凭据可用性、opt_in、轮次与超时 |
| 输出 | `HybridResult.as_dict()`：executed/effective/steps/escalation/escalation_result/fallback/diagnostics |
| 异常与回退 | sender 异常记「发送失败」、escalator 异常记「升级执行异常」且结果为空，均不外抛；生效即固化、未生效转下一目标、不伪称成功 |

## 2. 端到端流程

### 2.1 考前准备与硬门禁

固化清单分子分母与 refuted 黑名单；确认策略库可读、证据脚本可执行、PyRIT 状态已知、
凭据经环境变量注入不落盘；备齐证据模板（命令、输出、截图、脚本来源、AI 交互四字段、
面板与截图值）；通过 `capstone-rehearse` 门禁，未 PASS 不入场。

### 2.2 时间预算

| 时段 | 任务 | 硬约束 |
|---|---|---|
| 0–4h | 侦察、立足点、诱饵机识别 | 不提前消耗载荷预算 |
| 4–16h | 链式推进与 AI 向量利用 | 边打边写，命中即固化 |
| 16–20h | 收敛、证据补录、报告初稿 | 初稿须在缓冲内完成 |
| 20–24h | ≥4h 缓冲 | 不留到提交窗口补写 |

考后另有 24h 报告上传窗口，但证据须在考试窗口内落盘；提交为 PDF 加无密码 `.7z`，≤100MB。

### 2.3 单目标循环

```text
判形态 → 第一梯队 1–3 条（各 ≤2 次）→ 命中即停并固化
  → 第二梯队（各 1 次）→ 即时生成 → PyRIT 多轮（最后手段）→ 记未生效 → 下一目标
```

命令入口：`dialogue_cli --list-strategies` 列清单；`--target <TARGET> --endpoint-template chat
--strategy S-VERBATIM --repeat 2 --out <FRAGMENT>` 执行首轮；升级加 `--multiturn auto --turns 3`。
形态不符只改画像、不改载荷文本；响应字段缺失退回整段、不判空。

### 2.4 证据落盘与校验

`collect_evidence.py` 用 `--step --cmd --out --output --screenshot --flag-panel --flag-shot
--ai-log --target --exam --scored-target --strict` 固化；`verify_evidence.py --from-loot --report
--appendix --summary` 校验。双通道一致性是取消资格风险主源：面板值与截图/正文值必须一致；
AI 交互日志与其它工具同等标准入附录。

## 3. 策略与成功率管理

### 3.1 三梯队加工具面速查

| 级别 | 条目 | 命中 | 调度 |
|---|---|---|---|
| proven | S-VERBATIM、S-SYS-NOTICE、S-MEM-DUMP、S-MEM-SELFREP | 2/2 | 按题型选 1–3 条优先 |
| proven | S-ANCHOR、S-RAG-TRIGGER | 1/2 | 凭据类与检索类首选 |
| unstable | S-ROLEPLAY、S-DUAL-CLAIM、S-MEM-OVERRIDE | 1/2、0/2、0/2 | 第一梯队耗尽后限一轮 |
| refuted | S-CONTEXT-PAD、S-HEADING-ASK | 0/2 | 直接跳过 |
| 工具面 | mcp-01/05 完全生效；mcp-07 4/8；mcp-08 4/6；mcp-06 0/4 | 见实测 | 按题型调度 |

载荷原文见 `data/strategies.json`，本文件只给分级口径。

### 3.2 三重约束

1. **两次上限**：同一载荷最多 2 次；明确拒绝或触发检测即停，第 3 次必须换变体。
2. **双闸判定**：正则命中仅为候选，须过否定语境守卫；凭据类还须实值断言；拒绝句不算命中。
3. **层级下探**：第一梯队 → 第二梯队 → 即时生成 → 多轮 → 记未生效，不得跨级跳到高成本路径。

### 3.3 命中率口径与退化管理

每条重复 2 次、报数带分子分母；`proven` 区间 50%–100%，读作可复现而非稳定成功；
定版一致性 8/8，3 条 unstable 不计入判定。策略会退化：`S-ANCHOR` 2/2→1/2、
`S-DUAL-CLAIM`→0/2、`S-ROLEPLAY` 由 refuted 改判 unstable；目标或模型变更后重跑更新。
即时生成经双闸命中则考后回填策略库，证明无效登记 refuted。仅在两梯队耗尽后启用，
带格式锚点或场景框架、避开 refuted、仍过双闸、AI 交互入日志；载荷由调用方注入。

## 4. 效率权衡

### 4.1 六维对照

| 维度 | 清单优先 | 即时生成 | 混合取值 |
|---|---|---|---|
| 执行耗时 | 低、可批量 | 高、每题重做 | 主干取低，补位验证 |
| 命中率 | 50%–100% 基线 | 无基线、易落 0% | 基线定首轮，补位覆盖例外 |
| 试错次数 | 层级与黑名单约束 | 易重复无效 | 两次上限加黑名单 |
| 认知负担 | 决策外化 | 占用高 | 清单承载决策 |
| 维护成本 | 需重跑更新 | 重复发明 | 一次性维护、考后回填 |
| 风险可控性 | 已复核、证据绑定 | 未验证、易漂移 | 双闸+三态+双通道 |

### 4.2 时间与得分对齐

清单把「分析—措辞—验证」压缩为「选择—执行—判定」，节省时间投入证据与初稿；
多轮 92.7 秒且对加固目标失败，只在无其它路径时调用；≥4h 缓冲完成初稿对冲波动。
及格 75/100；最小组合之一为 4 台 AI 向量机加独立机，AI 向量为最高杠杆；
每台 AI 向量 15 分、传统 10 分、域控 5 分仅提交一次；工程标准 ≥85 留折损余量。

### 4.3 增量

Python 编排承担确定性工作，零依赖可审计；PyRIT 只在首轮失败后补充，三态防止「声明即执行」。
解耦后换目标改画像、换打法改策略数据、换判据改守卫。

## 5. 验收口径

### 5.1 门禁命令表

| 检查 | 命令 | 通过口径 |
|---|---|---|
| 术语 | `python scripts/check_glossary.py` | PASS，废弃术语零命中 |
| 预算 | `python scripts/check_token_budget.py --check` | 单文件不超上限 |
| 格式 | `npx markdownlint-cli2 <文档>` | 0 issues |
| 编译 | `python scripts/check_tools_compile.py --check-missing` | 失败 0 |
| 版本映射 | `python -m tools.pyrit_compat.checker check --root . --target 1.2.1` | 33/33、0 error |
| 场景 | `python -m unittest tests.attack_ai_agent.test_hybrid` | 21 例全绿 |
| 全量 | `python -m unittest discover -s tests -t .` | 全绿，跳过数已知 |
| 证据契约 | `--strict` 落盘加 `verify_evidence.py` | 片段齐全、双通道一致 |

### 5.2 回归集与双数并报

回归集为 DVAA 22 条。策略变更后须同时报「目标侧 captured」与「语义复核真实利用」两数，
后者不得下降；以 `completedAt` 为准，不以字段存在为准。单条通过须同时满足确定性证据
（实值或遥测）与非拒绝语义，缺一记未生效。否定语境守卫回看 140 字符且不跨子句。

### 5.3 三态输出与残留缺口

对象图须区分未启用、缺包不可用、已执行带命中数，事实不得由布尔字段单独表达。
残留：语义层认婉拒不认「我拒绝陈述 X」；`CrescendoAttack`/`TAPAttack` 仅可构造未实跑；
本地拒绝分类器需下载模型；未做卸载与复装往返实验。缺口不阻断方案，但须如实登记。

## 6. 风险清单

| 风险 | 依据 | 缓解 | 门禁落点 |
|---|---|---|---|
| 假阳性误判攻破 | DVAA 22 条中 5 条系拒绝句命中关键词 | 否定守卫 + 实值断言，拒绝句不算命中 | 双闸 |
| 命中率非确定 | 同策略跨轮 0%–100% 摆动 | 两次上限 + 分子分母 + 层级下探 | §3.2、§3.3 |
| 演练环境外推 | 演练目标不等于考试环境 | 先判形态护栏，命中率只作相对排序 | §2.3、§5.2 |
| 双通道缺失或文档不足 | 官方明示可致零分 | 边打边写；面板与截图值一致；AI 日志入附录 | §2.4 |
| PyRIT 依赖链重 | 装包受网络与 Python 版本约束 | 延迟导入、显式开启、缺包给版本诊断 | 三态 |
| 时间超支 | 24h 考试 + 24h 提交 | ≥4h 缓冲完成初稿；多轮仅最后手段 | §2.2、§4.2 |
| AI 使用合规 | 官方开卷且 OSEE/OSAI 并列允许 LLM | 记录提示、模型、输出、采纳，不照搬结论 | GOVERNANCE §5.5 |
| 明文凭据入报告 | 凭据只应产指纹 | 只留指纹与形态，不落明文值 | GOVERNANCE §6.2 |

**执行判定**：把成功率拆解为可控得分条件——优先高杠杆目标、命中即固化证据、
升级路径可审计且默认关闭。命中率只用于排序与预算，不作通过承诺。

## 7. 实施清单

| 阶段 | 目标 | 改动文件 | 验收 | 状态 |
|---|---|---|---|---|
| P0 规则对齐 | 计分与证据约束转选型依据 | 无（只读） | 75/100、双通道、24h 有出处 | 完成 |
| P1 能力盘点 | 定零重写边界 | 无（只读） | 四层结构与依赖方向确认 | 完成 |
| P2 门控实现 | 触发/禁止/冲突固化 | `hybrid.py` | `escalation_gate()` 纯函数 | 完成 #460 |
| P3 编排实现 | 唯一 seam、事实层 | 同上 | 顶层零 pyrit 导入 | 完成 #460 |
| P4 场景验证 | 典型/边界/误触发 | `test_hybrid.py` | 21 例全绿 | 完成 #460 |
| P5 方案统一 | 合并为单一事实源 | 本文档 | 七项输出齐全、术语 PASS | 本轮完成 |
| P6 门禁复测 | 静态与全量重跑 | 无 | 见 §8.3 | 本轮完成 |
| P7 提交合并 | PR、CI、main 同步 | 无 | CI 全绿、同步 0/0 | 进行中 |
| P8 考试窗口 | 真实取证与报告 | 不入库 | 只在正式窗口填写 | 未开始 |

## 8. 验证与对齐方案

### 8.1 场景验证矩阵（21 例离线）

| 类别 | 场景 | 期望 |
|---|---|---|
| 典型 | 条件全满足 / 无 opt-in / 放行传参 / 命中即停 | 放行、停 Python 层、参数入库、停在首轮 |
| 边界 | 非对话拒绝、`agent_chat` 允许、空 objective、轮次 0/4、超时 0/601、次数用尽、拒绝即停 | 按 §1.4 拒绝或允许 |
| 误触发 | opt-in 叠加凭据缺失 / 已有生效 / pyrit 不可用 / 多冲突 | 硬阻断优先、降级不报错、冲突全记录 |
| 异常契约 | escalator 抛错、sender 抛错、结果字段 | 收敛未生效、记发送失败、三态齐全 |

### 8.2 与既有资产对齐

`strategies.json` 11 条、`negation.judge`、`dialogue.score`、`pyrit_multiturn.run_multiturn`
只被调用未改写；新增模块无新 PyRIT import 符号，S1 覆盖率维持 33/33；
顶层无 pyrit 导入，L0–L3 可在无包环境执行；`executed` 沿用 #458「声明与执行分离」。

### 8.3 本轮实测（不照抄输入文档）

| 验证项 | 本轮实测 | 状态 |
|---|---|---|
| 术语一致 | PASS，检查 66 个废弃术语 | PASS |
| 产物预算 | 结论 PASS；本文 16,957B / 17,000 上限 | PASS |
| 格式 | 三文档 markdownlint 0 issues | PASS |
| 编译 | 309 文件、失败 0 | PASS |
| 版本映射 | 33/33、0 error、4 warn | PASS |
| 场景测试 | Ran 21 tests、OK | PASS |
| 全量回归 | Ran 1657 tests、OK (skipped=2) | PASS |
| 敏感信息扫描 | 正则扫目标地址与明文凭据，无命中 | PASS |
| 跨文档重复 | 检查器 258 字符，位于两份输入文档之间；本文未新增 | 信息级 |
| CI | PR #461 全绿 + main CI `45749806632` success | PASS |

重复块说明：检查器 `MIN_DUP_CHARS=240` 默认只告警不阻断；258 字符来自输入文档的相同命令模板，已合并为单一事实源。

### 8.4 与进攻方最佳实践的对应

| 原则 | 落实 | 限制 |
|---|---|---|
| MITRE ATLAS 侦察先行、按适用性选手法 | `target_profile` 驱动形态；门控限定对话面 | 资产发现依赖上游 |
| OWASP LLM 注入/泄露/过度代理 | 判据 + 否定守卫 + 实值断言；工具面独立八步 | 不承诺成功率 |
| NIST AI RMF 可审计、风险分级 | 步骤/冲突/决策留痕；限 1 次 3 轮 600s | 报告由考生完成 |
| OffSec OSAI 鼓励用 AI 但重文档 | AI 用于编排判定；双通道出口 | 截图值只在窗口产生 |
| 进攻方纪律拒绝即停、成功即固化 | 遇拒绝停、命中即返回、回填由调用方 | 拒绝标记是字符串启发式 |

### 8.5 执行结果确认

**已落地**：`hybrid.py` 唯一 seam、纯函数门控、三类值类型、顶层零 pyrit 导入；
`test_hybrid.py` 21 例（典型 4 / 边界 6 / 误触发 4 / 异常 2 / 契约 1）；本文件为权威方案。

**停留在设计**：即时生成载荷由调用方注入；refuted 回填由调用方写库；截图与面板值由考试窗口产生；
工具面/检索面/传统向量走既有技能，不纳入 L2。

**待正式窗口验证**：正式目标命中率与 `FAILURE` 分布；`CrescendoAttack`/`TAPAttack` 未实跑，不列入基线。
