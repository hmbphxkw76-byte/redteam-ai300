# OSAI (AI-300) 实现框架评估与适配决策

> **性质**：研究/决策文档（非规范正文），供 `redteam-ai300` 技能库落地选型参考。
> **评审对象**：`D:\下载\osai-ai300-skill-coverage-decision.md`（考前演练目标+工具精选）所列候选框架，结合 OffSec OSAI AI-300 考试真实场景与要求，给出最优选择与理由。
> **核验日期**：2026-11-15（GMT+8）。一手源：OSAI Exam Guide（`help.offsec.com`，S3 快照见 `docs/governance/references/OSAI-Exam-Guide-snapshot.md`）；框架版本取自各官方仓库/文档（2026-11 实测）。
> **结论先行**：**不采用单一框架，采用"最佳组合（best-of-breed）分层工具栈 + 个人方法论/笔记系统为统一层"**。PyRIT 保留为规范内核（AI 向量深度利用 + 证据留痕），但明确**降级为多层栈中的一层**，由 garak / promptfoo / 自定义脚本 + Kali 工具链 / 许可 AI 助手补足其覆盖盲区。

---

## 1. 考试真实场景与硬约束（决策前提）

OSAI 不是"纯 AI 攻防"考试，而是 **OSCP 风格的企业级实战红队 + AI 层叠加**：

| 维度 | 事实（一手源核实） |
|---|---|
| 形态 | 24h 监考，经 **Tailscale VPN** 在本地 **Kali VM** 接入 AI 赋能企业环境；2 条独立攻击链，各 3 台机，汇聚到同一域控（DC）；1 台独立 AI 主机；2 台故意不脆弱（无分）。 |
| 计分 | 8 台计分 = 100 分；**75 分及格**。推导：链内 4×AI(15) + 2×传统(10) = 80，+ 独立 AI(15) = 95，+ DC(5, 仅一次) = 100。→ **AI 向量占 75/100，是绝对主分面**。 |
| 工具政策 | **完全开卷，无工具限制**（"any tooling, framework, or technique"）。**AI 聊天机器人被明确允许**（OSAI 与 OSEE 并列为例外），且官方"strongly encourage"全程使用 AI。 |
| 报告门槛 | **极严**：每步命令/输出/脚本/修改说明 + 截图 + **可 copy/paste 逐步复现**；PDF 入 `.7z`（无密码、≤100MB），上传后 MD5 校验、不可修改。文档缺失 = 扣分或零分（首要失分风险）。 |
| 课程映射 | 11 模块覆盖：AI agent、multi-agent/A2A、RAG、embeddings、MCP/tool surfaces、供应链、AI 基础设施/云、威胁建模、capstone。与文档所列 10 考纲场景一致。 |

**对框架选型的直接含义**：
1. 考试环境是**离线/半离线的 Kali + VPN 企业网**，不是 Azure。任何重度云依赖、或会把数据外发到托管服务的工具，在考试实操中存在合规与可用性风险。
2. 计分主面是 **AI 向量（75 分）**，但交付链（链内传统向量、DC、企业内网横向、云/K8s）需要 OSCP 级能力——**没有任何单一 AI 红队框架能覆盖这部分**。
3. 报告门槛把"可复现 + 证据留痕"变成硬指标，框架必须能产出**结构化、可逐步复现**的证据。

---

## 2. 候选框架画像（2026-11 现行版本）

| 框架 | 版本/许可 | 本质定位 | 核心强项 | 核心弱项（考试视角） |
|---|---|---|---|---|
| **PyRIT**（Microsoft） | v1.1.0（2026-09-04）/ MIT | 多轮攻击**编排框架**（人主导战役） | 多轮编排（Crescendo/PAIR/TAP）、converter/scorer/目标抽象、SQLiteMemory 证据库 + 漂亮打印机 → **直接服务报告证据留痕** | 需手搓 target/attack/scorer（Python）；**无原生 MCP 攻击策略**（v1.1.0 仅靠 `HTTPTarget`+回调）；评分常需 LLM judge；作为无人值守 CI 检查最弱；重依赖。 |
| **garak**（NVIDIA） | v0.17.1（2026-10-16）/ Apache-2.0 | LLM **漏洞扫描器**（"LLM 的 nmap/Metasploit"） | 120+ 探针、内置检测器**可离线打分（无需 judge）**、首扫极快、CLI 友好 | 偏模型/对话层；**agent/MCP 弱**（AgentBreaker 默认关闭、Tier3）；企业内权限/基础设施无覆盖。 |
| **promptfoo**（OpenAI 旗下，2026-03 收购，仍开源） | 0.125.1（2026-10-25）/ MIT | **声明式红队评估套件**（YAML 驱动、CI 友好） | agent/MCP 攻击目录最广（BOLA/BFLA/RBAC/excessive-agency/MCP/cross-session/memory-poisoning/SSRF…）；用例可随代码版本化、复跑 | **部分插件（间接注入/授权/SSRF）走托管服务（现属 OpenAI）→ 数据外发**，考试离线/保密场景是硬伤；默认用托管生成与评分，须自配 provider。 |
| 专项点解（A2ASecBench / mcp-scan / agentic-radar / AgentPoison / vec2text / ModelScan / IBM ART） | 见源文档 | 单场景原子能力 | 各自在 MA/MCP/RAG/Emb/SC 上深度领先 | 互不打通，需人工编排进统一流程。 |

> **冲突提示**：二手博客（lazyhackers 等）称 ChatGPT/Claude/DeepSeek 在考试"禁用、瞬时零分"。但 **官方 S3 + AI Usage Policy 明确将 OSAI 与 OSEE 并列为例外，允许 AI 聊天机器人且强烈建议**。本项目已在一手源层面消解该冲突。考前仍须以 `help.offsec.com` 最新原文复核，不作为决策依据引用二手说法。

---

## 3. 四维度对比

### 3.1 技能覆盖度（10 考纲场景 × 框架原生能力）

| 场景 | garak | PyRIT | promptfoo | 专项点解 | 结论 |
|---|:--:|:--:|:--:|:--:|---|
| LLM | ● | ● | ● | — | 三家全覆盖 |
| Agt（agent） | ◐ | ● | ● | — | PyRIT(深)+promptfoo(广) 双保险 |
| MA / A2A | — | ◐(HTTPTarget) | ◐(插件) | ● A2ASecBench | 专项点解主导 |
| RAG | ◐ | ● | ◐ | ● PoisonedRAG | PyRIT+PoisonedRAG |
| Emb | — | ◐ | — | ● vec2text | 专项点解主导 |
| MCP / tool | — | ◐(弱) | ●(插件) | ● mcp-scan/agentic-radar | **PyRIT 明确最弱**，promptfoo+专项主导 |
| SC（供应链） | — | ◐ | — | ● ModelScan/ART | 专项点解主导 |
| Infra / Cloud | — | ◐ | — | ● MS AIRT + Kali | **框架普遍缺席**，Kali 工具链 |
| Rep（报告/证据） | — | ●(memory) | ●(report) | — | PyRIT+promptfoo+手动截图 |
| **传统向量/链内横向/DC** | — | — | — | — | **任何 AI 框架都覆盖不了** → 标准 Kali 工具 |

**覆盖结论**：**不存在单一框架覆盖全部 10 场景**。MCP、MA、Emb、SC、Infra、Cloud 以及整个企业横向/DC 面，必须靠专项点解 + 自定义脚本 + Kali 工具链补位。PyRIT 在 LLM/Agt/RAG/Emb/SC/Rep 强，但在 MCP-native、MA-native、Infra、Cloud 与"企业落地"上缺席——而这些合起来是考试范围的很大一块。

### 3.2 考试实操需求（离线 Kali + VPN + 保密 + 可复现）

- **离线/数据保密**：garak 内置检测器**纯离线打分**，最契合；PyRIT 可离线跑但需自配 LLM scorer（可用考试许可的 AI 聊天机器人兜底）；**promptfoo 默认把生成/评分发往托管服务（现 OpenAI）→ 考试环境是明确劣势**，须强制 `--provider` 自托管且关闭联网插件，否则不建议在考试内网启用其联网插件。
- **重型依赖**：PyRIT 依赖最重、最"框架化"，在赶时间与需逐步文档化的考试里，从零手搓 target/attack 成本高；garak/promptfoo 是 CLI 即开即用，更适合"先扫一遍"。
- **可复现 + 证据**：PyRIT 的 `SQLiteMemory` + `PrettyAttackResultMemoryPrinter` 天然产出结构化证据，与报告门槛高度契合；promptfoo 的 YAML 用例"版本化复跑"也契合"copy/paste 复现"；garak 偏快照、需自行整理。

### 3.3 框架灵活性（配置驱动 vs 代码驱动 / 适配新变种）

- **garak**：模块化探针，加探针即扩展；但偏"已知攻击库"，对新变种需写新 probe。
- **PyRIT**：代码驱动、抽象最深，可对任意 HTTP/WebSocket/自定义目标编排多轮；**最灵活但最费工**，适配新变种能力强但门槛高。
- **promptfoo**：**声明式 YAML**，"描述目标→选插件→复跑"，对已知 agent/MCP 攻击开箱即用、改配置即可适配；但对"描述质量"敏感，描述差则攻击泛化差。
- **自定义脚本 + Kali 工具**：**灵活性上限最高**，考试最不可预测的"企业落地 + 新变种"只能靠它。

### 3.4 考试实战效果（是否真能拿分 + 过报告关）

- **拿分主面（AI 向量 75 分）**：garak 首扫快速定位薄弱点 → PyRIT 深度多轮利用并留证 → promptfoo 把已知 agent/MCP 用例固化复现。三者组合对 AI 主分面覆盖最稳。
- **拿分副面（传统/DC/云）**：完全靠 OSCP 级 Kali 工具链（nmap、burp、impacket、云 CLI）+ 自定义脚本；AI 框架在此零贡献。
- **过报告关**：PyRIT 证据库 + promptfoo 结构化报告 + 手动截图，是降低"文档缺失零分"风险的最稳组合。
- **AI 助手杠杆**：OSAI 允许且强烈建议用 AI 聊天机器人。**将许可 AI 用作 payload 编写、故障排查、结果判读 co-pilot，本身是一项"框架级"能力**，应纳入工具栈统一层。

---

## 4. 最优选择及理由

### 选择：**分层最佳组合（best-of-breed）+ 个人方法论统一层**

```
统一层：个人笔记/速查 + 本仓库 skills/*/SKILL.md（方法论与可复用 attack 流程）
  ├─ 首扫层：  garak        —— LLM/模型层快速漏洞扫描（离线、无需 judge）
  ├─ 深度层：  PyRIT(v1.1.0) —— AI 向量多轮编排 + SQLiteMemory 证据留痕（规范内核）
  ├─ 固化层：  promptfoo    —— agent/MCP 声明式用例（须自托管 provider、禁用联网插件）
  ├─ 适配层：  自定义 Py/Bash + 专项点解（A2ASecBench/mcp-scan/agentic-radar/
  │            AgentPoison/vec2text/ModelScan/IBM ART）—— MCP/MA/Emb/SC 原子能力
  ├─ 落地层：  Kali 工具链（nmap/burp/impacket/云CLI）—— 传统向量/横向/DC/云
  └─ 协作层：  许可 AI 聊天机器人 —— payload 编写/排障/判读 co-pilot
```

### 为什么不纯用 PyRIT（尽管本仓库已将其设为规范）
1. **覆盖硬缺口**：PyRIT v1.1.0 **无原生 MCP 攻击策略**（仅 `HTTPTarget`+回调），而 MCP 是 15 分场景类；MA/Emb/SC/Infra/Cloud 与整个企业横向也缺席。单靠 PyRIT 留白过大。
2. **考试时间/文档压力**：PyRIT 需手搓 target/attack/scorer，对"广度 + 逐步文档化"不友好；garak 首扫 + promptfoo 声明式在"先扫后固化"上更快。
3. **离线/保密**：promptfoo 托管插件数据外发是考试硬伤，garak 纯离线打分更契合；需明确边界而非默认全用。

### 为什么保留 PyRIT 为规范内核
1. **深度无可替代**：多轮编排（Crescendo/PAIR/TAP）对 agentic/LLM 深度利用仍是最佳；本仓库已建成经一手源核实的 `pyrit==1.1.0` 集成（见 `docs/research/pyrit-canonical-references.md`），推倒重来浪费投资。
2. **证据留痕直击报告门槛**：`SQLiteMemory` + `PrettyAttackResultMemoryPrinter` 产出结构化、可逐步复现证据，正是"文档缺失即零分"风险的对症解药。
3. **AI 向量是主分面（75/100）**：PyRIT 在 LLM/Agt/RAG 的深度利用与留证，是拿满主分的最稳路径。

### 一句话理由
> 考试是"企业实战红队 + AI 层"，没有单框架能同时覆盖 AI 主分面、MCP/MA/供应链/云、以及传统横向/DC；**PyRIT 做深、garak 做快、promptfoo 做固、自定义+Kali 做落地、许可 AI 做协作**的分层栈，在覆盖度、离线可用性、灵活性、实战拿分与过报告关五项上同时最优。

---

## 5. 对本仓库技能的适配落地建议

1. **明确角色边界**（写入 `GOVERNANCE`/技能 SKILL 头部）：PyRIT = AI 向量深度利用+证据；garak = 首扫；promptfoo = agent/MCP 固化用例（自托管）；专项点解 = 原子能力；Kali 工具链 = 落地。
2. **PyRIT 接 MCP/MA**：因 v1.1.0 无原生策略，复用现有 `attack-mcp-tool` 双形态 seam + `HTTPTarget` 回调，避免在 PyRIT 内重造轮子。
3. **保留 `pyrit-canonical-references.md` 单一可信源**地位，但新增"框架分工矩阵"章节，让每个技能清楚自己归属哪一层、何时调用相邻层。
4. **考前训练序列**（对齐源文档）：AIVP 全通 → FinBot agentic → Appsecco MCP → PoisonedRAG → MS AIRT 补 Infra/Cloud；其间用 garak 首扫、PyRIT 留证、promptfoo 固化 agent/MCP 用例。
5. **报告证据工程化**：用 PyRIT memory 导出 + `report-exam` 五段式（见 `docs/research/report-exam-canonical.md`）统一收口，降低文档缺失风险。

---

## 6. 风险与待核实

- **promptfoo 托管插件**：考试内网启用其联网生成/评分插件存在数据外发与可用性风险；考前须实测自托管 provider 配置并禁用联网插件，或干脆考试内网改用 garak+PyRIT+自定义。
- **工具政策冲突**：二手源称 AI 聊天机器人禁用，与官方 S3 矛盾；**以 `help.offsec.com` 最新原文为准**复核后再固化进技能。
- **版本漂移**：PyRIT 1.1.0 破坏性重构已核实；garak/promptfoo 月级更新，考前复测其 agent/MCP 插件现状。
- **分值推导**：链内"4 AI + 2 传统"为推导（S3 未明示），不影响框架选型结论，但影响训练优先级权重。

---

## 7. 参考源（一手优先）

- OSAI Exam Guide（S3 快照）：`docs/governance/references/OSAI-Exam-Guide-snapshot.md`
- PyRIT 权威引用：`docs/research/pyrit-canonical-references.md`；API 核实：`docs/research/pyrit-v110-api-verification.md`
- 源工具精选文档：`D:\下载\osai-ai300-skill-coverage-decision.md`
- 框架对比（2026-11 实测）：Mindgard 博客、agentopsguide、beri.net、techiehub、cleanissue.io 关于 garak/PyRIT/promptfoo 的横向评测
- AI Usage Policy（OSAI 例外）：`help.offsec.com` 同名文章（S3 快照 §11）
