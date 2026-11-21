# Ch3「Attacking AI Agents」一手源核实记录（attack-ai-agent 主线阶段 1）

> **一手源**：`D:\视频\OffSec   AI-300 Advanced AI Red Teaming\Ch3-Attacking-AI-Agents.html`（OffSec AI-300 课程模块 3，本地 HTML）。
> **提取副本**：`.workbuddy/ch3-source.txt`（运行时提取，不入 repo）。
> **核实日期**：2026-11-21 · **主题**：attack-ai-agent 的 Ch3 对齐全量主线落地。
> **性质**：事实核实记录（非规格 / 非门禁）。规格引用本文件用 `路径#章节锚点`，不复述正文（AGENTS.md C1）。

## 1. 已核实（结论 → 一手源锚点）

### 1.1 贯穿方法论：五步闭环

| 事实 | 锚点 |
|---|---|
| 每个攻击遵循同一循环：enumerate → naive attack → observe detection → evade → confirm | Ch3 模块引言（"Every attack follows the same cycle"）；§3.1「five-step methodology」 |
| 五步定义：Enumerate / Attack(naive) / Detect / Evade / Confirm，每步有明确判据 | §3.1「Every walkthrough in this Module follows the same five-step methodology」 |
| 拒绝式回应（"not authorized to share"）反证内容存在；真否定（"don't have information"）才是空 | §3.1 Enumerate 段；§3.1 复习题 3 |
| Detect 查 Kibana（ELK SIEM），日志索引 `aim3-agent-*`；登录凭据属 Lab 专有，不入规格（用 `<SIEM_CREDS>` 占位） | §3.1 Info 框 |
| Evade 各护栏盲点：编码载荷绕关键词、CSS 隐藏绕内容扫描、描述性措辞绕祈使命令检测 | §3.1 Evade 段；§3.2/§3.3/§3.4 各 walkthrough |
| 成功判据 = 达成目标 + 无告警；嘈杂攻击致 agent 被关停 | §3.1 结尾；§3.5 Capstone 第 4 条 |

### 1.2 Agent 架构与信任模型

| 事实 | 锚点 |
|---|---|
| 五组件：LLM core / system prompt / tools / memory(短期+长期) / guardrails | §3.1「five core components」 |
| ReAct（Reason+Act）循环，工具输出回灌 LLM，每步是注入点 | §3.1 Figure 1 后「Our lab agents use the ReAct pattern」 |
| LLM 在系统提示/用户输入/工具输出/记忆间无信任边界（同一 token 流） | §3.1「The Agent Trust Model」 |
| 输入通道表：直接输入/摄取数据/工具响应/记忆检索 → 四类攻击 | §3.1 Table 1 |
| 输出通道表：文本响应/工具调用/记忆写入 → 外泄/未授权动作/持久后门 | §3.1 Table 2 |
| 最强攻击 = 输入通道 + 输出通道组合 | §3.1 Table 2 后段 |
| `/health` 端点常免鉴权、暴露 agent 名与端口 | §3.1 Listing 2 / §3.2 Listing 5 |

### 1.3 直接提示注入（ASI01）

| 事实 | 锚点 |
|---|---|
| 系统提示含内部 URL/DB 凭据/API key/过滤词表/安全规则，泄露=内网地图+防御路线图 | §3.2「System prompts often contain sensitive configuration」 |
| 朴素直取触发两条规则（Prompt Injection Keywords in Agent Input / System Prompt Content in Agent Output） | §3.2 Listing 9 后 Kibana 段 |
| 输出过滤绕过：字符间插空格、ROT13、反转、翻译、base64/hex；模型接受度因目标而异 | §3.2 Tip 框；Listing 10/12 |
| 场景化框架（troubleshooting framing）让取值自然输出，避开标签匹配 | §3.2 Listing 11→12 对比段 |
| 凭据真实性须用提取值实际登录验证（DB/API） | §3.2 Listing 13/14 |
| 目标劫持避开显式重定向短语与敏感词堆砌；用单次干净重构（单关键词）或多轮 crescendo | §3.2 Listing 17→19→20；Listing 21-23（crescendo，同 session_id） |
| 逐条分析失败原因：crescendo 每条消息单独看均正常 | §3.2「Why Per-Message Analysis Fails」框 |

### 1.4 间接提示注入（跨域注入）

| 事实 | 锚点 |
|---|---|
| 投毒数据源（文档/网页/DB 条目/代码文件），载荷持久、触发他人、难归因 | §3.3 开篇 |
| 跨文档分片：逐文件扫描各自通过，多文档进入同一上下文才拼接生效 | §3.3 Listing 29/30；「Cross-Document Fragmentation」框 |
| CSS 视觉隐藏（font-size:0/color:transparent/display:none/visibility:hidden）：提取管线剥离但 LLM 处理原始 HTML，注入短语不进日志 | §3.3 Listing 35→36；「The Extraction Pipeline Gap」框 |
| Unicode 隐藏载荷于代码文件 | §3.3 学习目标第 4 条 |
| 导入解析外泄：提交正常代码（`from config import Config`），审查工作流读取并披露硬编码凭据，载荷为零注入短语 | §3.3 Listing 39/40 及分析段 |
| OpenAPI 规范（`/openapi.json`）用于发现摄取端点 | §3.3 Listing 26 |
| 凭据权限域（scoped）： stolen key 仅可访问授权 bucket | §3.3 Listing 31/32 |

### 1.5 记忆攻击（ASI06）

| 事实 | 锚点 |
|---|---|
| 记忆攻击须影响自身会话之外（其他用户/流水线/全局行为）才有作战价值；等价 agent 版 stored XSS | §3.4「key principle」段；Listing 46 后分析 |
| 共享数据存储投毒：写权限 → 植入条目 → 其他会话触发 | §3.4 Listing 44/45/46 |
| 描述性措辞（"has migrated"/"should now use"）绕过祈使命令检测规则 | §3.4 Listing 45 后「AIM3: Imperative Commands in Stored Memory」未触发分析 |
| recency bias：更近日期 + (UPDATED) 标题优先采信；混入合法细节增强权威性 | §3.4 Listing 45 前置说明 + Listing 46 后分析「Exploiting Recency Bias」框 |
| 会话枚举：可预测 session_id（前缀+日期+自增）→ 遍历 → 空/活跃响应差异判命中 → 关键词过滤 | §3.4 Listing 47/48/49/50/51 |
| 会话枚举请求经正常 `/chat`，与普通流量不可区分，无规则触发 | §3.4 Listing 51 后段 |

### 1.6 Capstone 端到端验收（§3.5）

枚举全部服务识别 agent 能力 → 无告警提取凭据/配置 → 投毒 agent 读取的数据存储并植入重定向条目 → 以员工身份查询验证攻击者 URL 出现 → 复核全程无 ELK 规则触发（§3.5 四条 bullet）。

## 2. 待核实（取证方式逐条给出）

| 待核实项 | 取证方式 | 影响 |
|---|---|---|
| 本仓库 `tools/attack_ai_agent/` 是否已覆盖五步闭环的可验证判据 | 阶段 8 静态检索 + 测试断言（D3-DETECT/EVADE/CONFIRM 验收条件） | 决定是否需新增最小实现切片 |
| 各护栏盲点在目标环境的实际规则名 | 演练时查 Kibana（`aim3-agent-*`）；规格中按「规则名+盲点」占位，不臆造 | 证据字段设计 |
| 课程所列实验 IP/凭据与演练目标（AIVP）不一致 | 属 Lab 专有值，不入规格；实现用 `<TARGET>` / `<SIEM_CREDS>` 占位 | 避免硬编码 |

## 3. 已排除（不作为规格输入）

- 课程 Lab 专有凭据/URL 字面值（§3.1 Info、Listing 中 elastic、DB、MinIO、Slack、JIRA 凭据）——违反 C1/无硬编码凭据约束。
- 演练目标 IP 与课程 IP 的映射关系——由 `recon-ai` 资产清单提供，不属本技能规格。
- Ch4 多智能体 / A2A 内容——不在本模块范围（属 `attack-multi-agent`）。

## 4. 框架选型核实（B9）

矩阵条目①（osai-skill-framework-matrix.md §2①）：PyRIT v1.1.0 内核 + promptfoo agent 插件 + 自定义脚本。本主线增量聚焦「五步闭环 + 技法细化」，属于自定义脚本/行为规格层；不改 PyRIT seam（`aia-01..12` 冻结）。与框架决策文档 §8「沿用既有 pyrit==1.1.0 集成」一致，无偏离。

## 5. 阶段 1 G0 门禁记录（增量，T2/T3）

| 检查项（基线编号） | 判定 | 证据命令 / 锚点 |
|---|---|---|
| B7 版本与对象图 | 符合 | 本记录 §4：PyRIT 1.1.0 内核，无旧名；锚点 `pyrit-canonical-references.md` |
| B8 可追溯性 | 符合 | 每条结论附 Ch3 §x/Listing N；三类清单齐全（§1/§2/§3） |
| B9 框架合规 | 符合 | §4 对照矩阵条目①，无偏离 |
| 验收①一手源可定位 | 符合 | §1 表全列锚点 |
| 验收②版本明确 | 符合 | §4 pyrit==1.1.0 |
| 验收③攻击路径映射 | 符合 | §1.3/1.4/1.5 分别映射 ASI01/间接注入/ASI06 |
| 验收④待核实命名+取证 | 符合 | §2 三行各含取证方式 |
| 验收⑤落盘 docs/research/ | 符合 | 本文件路径 |

**不符合项数**：0。**G0 结论**：`PASS`。
