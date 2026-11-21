# A2A Ch4 对齐全量主线：阶段 6/7 设计与术语记录

> 对应父工单 #292、规格 v2 #294。本文同时承载阶段 6 `codebase-design` 与阶段 7 `domain-modeling` 的交付物与 G0 记录。

## 1. 设计目标与边界

- 目标：把 Ch4 C1–C20 落入三技能既有结构，不新增 skill、不新增 step_id、不改 `collect_evidence.py` 共享契约。
- 框架组合按矩阵：threat-model=方法论/文档/许可 AI（§⑬）；recon-ai=garak+Kali+许可 AI（§⑥，本轮 garak 偏离见 V4）；attack-multi-agent=A2ASecBench+a2a-scanner+PyRIT HTTPTarget（非主演）+A2A SDK（§⑩），与既有 `attack-multi-agent-design.md` 一致。
- 不引入 `pyrit.orchestrator` 等 B7 禁用对象；PyRIT 仍为 `pyrit==1.1.0`，`HTTPTarget` 仅作深度补位与懒导入。

## 2. Seam 清单（新增数量 0）

| Seam | 状态 | 职责 | 注入点 | 说明 |
|---|---|---|---|---|
| `transport.Transport` | 复用 | recon-ai 唯一网络出口 | `UrllibTransport` / `FakeTransport` | Agent Card 探针复用该 seam，不新增网络层 |
| `probes.RequestSpec` | 复用 | 声明式只读请求 | `recon-05.requests` | 新增 `/.well-known/agent.json` 请求，仍属 recon-05 |
| `scanner`（attack-multi-agent） | 复用 | A2ASecBench/a2a-scanner 外部适配 | `BuiltinAnalyzer` / 适配器 | 本轮不改 |
| `pyrit_attack`（attack-multi-agent） | 复用 | PyRIT HTTPTarget 懒导入补位 | `--pyrit` | 本轮不改，保持非主演 |
| `loot-manage` / `report-exam` 索引 | 复用 | 战利品与报告证据消费 | 既有字段契约 | 本轮不改 |

结论：新增 seam 数量为 0；V1 的最小实现完全落在既有 `transport` 与 `probes` seam 内，符合阶段 2 seam 提案。

## 3. 公开接口与错误行为

### 3.1 recon-05 Agent Card 探针（阶段 8 实现位置）

| 接口 | 职责 | 输入 | 输出 | 错误行为 |
|---|---|---|---|---|
| `probes.STEP_SPECS['recon-05']` | 声明 agent 系统识别请求序列 | 无 | 含 Agent Card GET 的 `StepSpec` | 不改变既有两条请求顺序；追加在末尾 |
| `probes._agent_card(results)`（新增纯函数） | 从 recon-05 结果识别合法 Agent Card | `Sequence[ProbeResult]` | `(dict, ProbeResult)` 或 `(None, None)` | JSON 解析失败、404、缺 `name`/`description`/`skills` 均返回 `(None, None)`，不推断存在 |
| `probes.judge_agent(results, ctx)` | 现有 recon-05 判据 | 结果序列 + 上下文 | `Judgement` | 优先既有 `/agents`、`/health`、request_id 判据；仅无上述信号且 Card 合法时返回 PRESENT |

依赖方向不变：`cli → runner → {discovery, probes, inventory, evidence, policy, verifier, shot} → {transport, fingerprint, model}`。

### 3.2 SKILL.md 规格槽（无运行时接口）

| 技能 | 规格槽 | 输入 | 输出 | 错误行为 |
|---|---|---|---|---|
| threat-model | 信任边界节第 4 点 | 资产清单中的 A2A 线索 | 四模式/框架风险/四类向量补标 | 无线索记 `UNDETERMINED`，不虚构拓扑 |
| recon-ai | recon-05/07 补录 | Agent Card/OpenAPI/SIEM 可见性 | 证据片段字段补录 | null/404→`ABSENT`；SIEM 不可读→`UNDETERMINED` |
| attack-multi-agent | A2A 协议专项攻击面表 | 枚举产物与合法 workflow 基线 | 六类攻击面的触发/命令/判据/异常 | 认证不足、无主机名、无可写端点分别跳过；失败不夸大 |

## 4. 测试替身策略

- `FakeTransport` 增加一条确定性路由：GET `/.well-known/agent.json` → 合法 card JSON；另设 404/坏 JSON 用例验证 `ABSENT`/`None`。
- recon-ai 既有 `FakeShot`、`EvidenceWriter` 复用；C1–C9 门禁不得因多一条证据命令失败。
- attack-multi-agent 不改 `a2a-01..a2a-08` 步数；证据契约夹具继续断言 8 次调用。
- threat-model 无运行时代码，测试为文本标记与非空 diff 检查。

## 5. 被否决方案

| 方案 | 否决理由 |
|---|---|
| 新增 `recon-08` Agent Card 步骤 | 会破坏七步契约和下游资产 ID 复用，违反最小补全 |
| 在 attack-multi-agent 新增 PoC 脚本包 | V2 定为命令级规格；新增脚本会扩张实现面并需新测试契约 |
| 改 `collect_evidence.py` 增字段 | 共享契约，PR #250/#254 漂移风险高，本轮无需 |
| 在 GLOSSARY 新增 Agent Card 术语 | 现有 A2A 与「智能体冒充」条目已覆盖该协议专名；GLOSSARY 17491/17500B 接近上限 |

## 6. 阶段 6 G0（B2/B7/B8）

| 项 | 结果 | 证据 |
|---|---|---|
| B2 术语一致 | 符合 | 设计仅使用 GLOSSARY 既有词 |
| B7 对象图 | 符合 | 未引入禁用对象；PyRIT 版本锚点不变 |
| B8 可追溯 | 符合 | 矩阵 §⑥/§⑩/§⑬ 与 Ch4 章节均注明 |
| S1 接口完整 | 符合 | §3 每个接口含职责/输入/输出/错误行为 |
| S2 依赖单向 | 符合 | §3.1 明确依赖方向不变 |
| S3 冲突标注 | 符合 | V4 偏离显式登记 |

**阶段 6 G0：PASS**。

## 7. 阶段 7 术语映射表

| SKILL 概念 | GLOSSARY 规范词 | 代码 / 字段标识 | 来源 |
|---|---|---|---|
| 多智能体协同 | A2A (Agent-to-Agent) | `a2a-*`、`Category.AGENT` | GLOSSARY:105；Ch4 §4.1 |
| 目标内角色/连接关系 | 多智能体拓扑 | `agent_inventory`、`a2a-01` | GLOSSARY:108；Ch4 §4.2 |
| Agent 间消息篡改 | 消息操纵 | `msg_inject.py`、`a2a-02` | GLOSSARY:111；Ch4 §4.4 |
| 伪造 Agent Card/身份 | 智能体冒充 | `agent_impersonate.py`、`a2a-03` | GLOSSARY:114；Ch4 §4.5/§4.6 |
| 共享存储条目改写 | 共享记忆投毒 | `memory_poison.py`、`a2a-04` | GLOSSARY:117；Ch4 §4.7 |
| 共享上下文污染 | 上下文投毒 | `context_poison.py`、`a2a-05` | GLOSSARY:120；Ch4 §4.4/§4.7 |
| 不同权限组件间数据流 | 信任边界 | threat-model 术语 | GLOSSARY:155；Ch4 §4.1 |

无新增术语；`python scripts/check_glossary.py` 须 PASS。

## 8. 阶段 7 G0（B1/B2/B8）

| 项 | 结果 | 证据 |
|---|---|---|
| B1 | 符合 | 不新增 skill / 不改五要素结构 |
| B2 | 符合 | `check_glossary.py` PASS（阶段 9 复跑） |
| B8 | 符合 | 映射表逐条附 GLOSSARY 行号与 Ch4 章节 |
| 映射覆盖 | 符合 | 规格与设计中的 7 个核心概念全部覆盖 |

**阶段 7 G0：PASS**。进入阶段 8 `implement-spec`。
