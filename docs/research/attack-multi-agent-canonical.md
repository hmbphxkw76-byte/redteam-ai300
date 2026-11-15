# attack-multi-agent 一手源调研（A2A / 多智能体操纵）

> **性质**：阶段 1 `research` 交付物（唯一事实源，C1）。供 §3 规格 v2、§6 设计、§8 实现消费。
> **核验日期**：2026-11-15（GMT+8）。一手源优先：A2A 官方规范、A2ASecBench（ICLR'26）、Cisco a2a-scanner、PyRIT 权威索引。
> **框架组合（强制对齐矩阵 §⑩，B9）**：A2ASecBench（协议感知基准，主演）+ Cisco a2a-scanner（Agent Card 分析）+ **PyRIT HTTPTarget（深度补位，非主演）** + A2A Python SDK（演练目标基座与 recon）。
> **冲突优先级**：官方考试事实（S1/S2/S3）> GOVERNANCE > CI-CD > `skill-mainline-workflow.md` > 本文件。

---

## 1. 版本锁定

| 组件 | 版本 / 标识 | 说明 |
|---|---|---|
| A2A 协议 | `latest`（a2a-protocol.org；历史 0.1.0 / 0.2.5，v1.0 已 GA） | 传输 HTTP(S)+JSON-RPC 2.0；SSE 流式；**版本漂移**：0.x 与 1.0 方法名不同（见 §7 T-A2A-1） |
| A2ASecBench | ICLR 2026（OpenReview `LfdFnakqGJ`），repo `safo-lab/a2asecbench` | 六类协议感知攻击；基于公开 `a2a-sdk` 实现 |
| Cisco a2a-scanner | `cisco-ai-defense/a2a-scanner`，PyPI `cisco-ai-a2a-scanner`（1.x） | 五类分析器：YARA / spec / heuristic / LLM / endpoint |
| A2A Python SDK | `a2a-sdk`（官方 5 SDK 之一：Python/Go/JS/Java/.NET） | 演练目标基座与 recon |
| PyRIT | `pyrit==1.1.0`（2026-09-04） | 仅 `HTTPTarget` + `PromptSendingAttack` + `SubStringScorer` + `SQLiteMemory` 做深度补位 |

---

## 2. A2A 协议事实（一手源：`a2a-protocol.org/latest/specification`）

- **Agent Card**：A2A Server 在 `{base}/.well-known/agent-card.json` 发布的 JSON 元数据，声明 identity / capabilities / skills / endpoint / auth。**能力发现**入口，也是冒充/夸大权限（capability inflation）的攻击面。
- **任务生命周期**：`submitted → working → input-required → completed / failed / cancelled`，Task 由唯一 ID 标识；支撑「工作流破坏 / 任务洪泛」类攻击。
- **消息与内容单元**：Message（role=user|agent）由 Part（TextPart / FilePart / DataPart）组成；Artifact 为任务输出，同样由 Part 组成。Artifact 预览/渲染是「脚本注入」攻击面。
- **传输**：HTTP(S) + **JSON-RPC 2.0**；`Content-Type: application/json`。流式用 SSE（`text/event-stream`），每个 `data` 为一条 JSON-RPC 响应。
- **推送通知**：服务端向客户端 webhook 发起 HTTP POST（长任务/断连场景）。
- **上下文**：可选 server 生成的 `contextId` 逻辑分组相关任务——共享上下文的投毒面。
- **身份**：A2A 不在 JSON-RPC 载荷内传身份，身份在 HTTP 层处理——**消息信任缺失**的根因：接收方难以独立验证「声称的发送者」。

---

## 3. A2ASecBench 六类攻击（一手源：ICLR'26 `LfdFnakqGJ` / `safo-lab/a2asecbench`）

威胁分类两大族：**supply-chain manipulations** 与 **protocol-logic weaknesses**；六类攻击跨准入→编排→执行：

| 代号 | 攻击 | 对应本技能步骤 |
|---|---|---|
| AS | AgentCard Spoofing（伪造相似卡诱导选择） | a2a-03 智能体冒充 |
| CC（white/black） | Capability Cloaking（声明与后端能力不符） | a2a-01 拓扑 + scanner 夸大权限检测 |
| ASRF | Agent-Side Request Forgery（不安全的对端资源引用） | a2a-02 消息操纵（注入资源引用） |
| ATSI | Artifact Triggered Script Injection（预览触发执行） | a2a-02 / a2a-06（载荷带 artifact） |
| CO | Cycle Overflow（循环委派无界） | a2a-06 工作流破坏 |
| HOTF | Half-Open Task Flooding（滞留 input-required 任务） | a2a-06 工作流破坏 |

> 结论：A2ASecBench 的六类与本技能 8 步**非一一对应**，本技能按「总线/记忆/编排」三面组织；A2ASecBench 作为 scanner seam 的**主控**提供协议感知用例与判定（避免自造轮子）。

---

## 4. Cisco a2a-scanner（一手源：`cisco-ai-defense/a2a-scanner` 文档）

- **五分析器**：YARA（静态模式：冒充/注入/权限滥用/外泄/路由操纵/工具投毒）、spec（A2A 规范合规：必填字段/类型/URL/skills）、heuristic（可疑 URL、云元数据访问、命令执行、凭据收集）、LLM（语义）、endpoint（运行时：不可达/HTTP 非 HTTPS/缺 Agent Card/URL 不符/缺安全头）。
- **威胁类**：Agent Card spoofing、task replay、privilege escalation across agents、artifact tampering、indirect prompt injection via streams、capability inflation、DoS。
- **落地方式**：`a2a-scanner scan-card|scan-endpoint|scan-directory`（CLI）或 Python `Scanner(config)`。
- **对本技能**：`scanner.py` 的 `A2ASecBenchAdapter`/外部分析器即此层；默认 `BuiltinAnalyzer` 提供离线等价启发式（AC-11）。**考试内网须自托管**，避免 LLM 分析器外发（决策文档 §3.2）。

---

## 5. PyRIT 1.1.0 深度补位（一手源：`docs/research/pyrit-canonical-references.md`）

- v1.1.0 **无原生 MA 攻击策略**（与 MCP 同理），仅 `HTTPTarget` + 回调对接可达 A2A 端点做多轮。
- 可用对象：`pyrit.prompt_target.HTTPTarget`、`pyrit.executor.attack.PromptSendingAttack`、`pyrit.score.SubStringScorer`、`pyrit.memory.SQLiteMemory`、`initialize_pyrit_async(memory_db_type="SQLite")`。
- 禁用名：`pyrit.orchestrator`、`*Orchestrator`、`AzureOpenAIChatTarget`。
- **落地约束**：`python tools/attack_multi_agent/pyrit_attack.py` 顶层不 import pyrit（懒导入），未装时显式 `RuntimeError` 非静默（B7）。

---

## 6. SKILL.md 攻击路径 → 对象映射

| 步骤 | 动作 | 客户端/缝 | 对象图（PyRIT 补位时） |
|---|---|---|---|
| a2a-01 | 发现拓扑/总线 | `A2ABusClient.discover_topology` + `Scanner.analyze` | — |
| a2a-02 | 消息操纵 | `A2ABusClient.inject_message` | `HTTPTarget`→`PromptSendingAttack` |
| a2a-03 | 智能体冒充 | `A2ABusClient.impersonate` | 同上 |
| a2a-04 | 共享记忆投毒 | `MemoryStoreClient.poison_memory` | `SQLiteMemory` 留证 |
| a2a-05 | 上下文投毒 | `MemoryStoreClient.poison_context` | 同上 |
| a2a-06 | 工作流破坏 | `OrchestratorClient.disrupt_workflow` | `HTTPTarget` |
| a2a-07 | 下游决策影响取证 | `OrchestratorClient.get_trace` | `SubStringScorer` 判据 |
| a2a-08 | flag 取证 | host 层 `whoami;id;find` + 面板预言机 | — |

---

## 7. 已核实 / 待核实 / 已排除

### 已核实
- R1 A2A 用 JSON-RPC 2.0 over HTTP(S)、AgentCard、Task 生命周期、SSE、push（§2）。
- R2 A2ASecBench 六类攻击与仓库（§3）；a2a-scanner 五分析器（§4）。
- R3 PyRIT 1.1.0 对象图与禁用名（§5、权威索引）。
- R4 本技能 8 步均可映射到上述对象（§6）。

### 待核实（实现前取证，不阻塞其余路径）
- T-A2A-1：目标 A2A 实现属 0.x 还是 1.0（方法名 `message/send` vs `SendMessage`、part 结构差异）——取证：拉 `/.well-known/agent-card.json` 的 `protocolVersion`。
- T-A2A-2：目标消息总线是 Kafka/RabbitMQ/自定义（决定 `/topics` 或 `redis-cli` 探测路径）——取证：port scan + 产品指纹。
- T-A2A-3：a2a-scanner 在考试内网的 LLM 分析器是否禁用（数据外发风险）——取证：自托管 provider 配置验证。

### 已排除
- E1 单靠 PyRIT 覆盖 MA：已排除（v1.1.0 无原生策略）。
- E2 用 promptfoo 主导 MA：矩阵 §⑩ 指定 A2ASecBench/a2a-scanner 主导；promptfoo 非本技能层。
- E3 二手博客「AI 助手禁用」：与官方 S3 冲突，已排除（决策文档 §2）。

---

## 8. 框架组合合规（B9）

取自矩阵 §⑩ 原条目：**A2ASecBench + a2a-scanner + PyRIT HTTPTarget + A2A SDK**。无偏离。PyRIT 仅补位（`pyrit_attack.py` 懒导入），符合「PyRIT 非万能、MA 外挂」总原则。

---

## 9. 参考源（一手优先）

- A2A 规范：`https://a2a-protocol.org/latest/specification/`（v0.2.5 亦印证）
- A2ASecBench：`https://iclr.cc/virtual/2026/poster/10010017`、OpenReview `LfdFnakqGJ`、`https://safo-lab.github.io/A2ASecBench/`
- Cisco a2a-scanner：`https://cisco-ai-defense.github.io/docs/a2a-scanner`、`https://github.com/cisco-ai-defense/a2a-scanner`
- PyRIT 权威索引：`docs/research/pyrit-canonical-references.md`
- 框架决策 / 矩阵：`docs/research/osai-ai300-framework-decision.md`、`osai-skill-framework-matrix.md`
- 行为规格 v1：issue #63（七节）；工程规格 v2：`docs/operations/attack-multi-agent-design.md`
