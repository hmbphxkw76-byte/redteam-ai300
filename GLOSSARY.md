# OSAI AI-300 红队工程

本项目围绕 OffSec AI Red Teamer（OSAI）认证构建「agent + skill」红队工程能力；本表为《治理规范》与全部技能的唯一词汇基准。

## Language

采用「中文主词 + 英文规范词」并列；正文保留英文原样，避免与官方材料歧义。

## 考试与评分

**OSAI**:
OffSec AI Red Teamer 认证，考核 AI 化企业环境的实战红队能力。
_Avoid_: OSAI+、AI-300

**AI-300**:
OffSec 的 AI 红队训练课程（Advanced AI Red Teaming），11 个模块大纲。
_Avoid_: OSAI（认证）

**攻击链 (attack chain)**:
由单一公网入口起始、贯穿 3 台主机的路径；共 2 条，汇聚于域控。

**独立主机 (standalone host)**:
取得任一链内网立足点后方可达的 AI 向量主机，单独计 15 分。

**域控 (Domain Controller, DC)**:
两条链共同汇聚的共享主机，持有 `proof.txt`；其 flag 仅可提交一次。

**AI 向量 (AI vector)**:
针对 AI 组件（agent、RAG、MCP、embedding 等）的攻击路径，每台 15 分。
_Avoid_: AI 攻击向量

**传统向量 (traditional vector)**:
经典网络渗透路径（服务利用、横向、提权等），每台 10 分。

**诱饵机 (decoy)**:
「故意不设漏洞」的主机（0 分），用于增加真实性；共 2 台。
_Avoid_: rabbit hole、蜜罐

**计分目标 (scored target)**:
8 个计分主机之一（6 台链式 + 1 独立 + 1 域控）。

**flag**:
证明已攻陷的证据文件：`trad_vector.txt`、`ai_vector.txt`、`proof.txt`。

**及格线 (pass threshold)**:
75/100 分，达到方可获得 OSAI 认证。

## 攻击面

**RAG (Retrieval-Augmented Generation)**:
检索增强生成流水线，可被知识库投毒与检索层操纵。

**MCP (Model Context Protocol)**:
模型上下文协议与工具集成面，可被滥用以提权或执行非预期动作。

**工具面 (tool surface)**:
一次会话内 agent 可调用的全部 MCP 工具及元信息，每条含 server、工具名、描述、权限范围与信任级别；是 `attack-mcp-tool` 的枚举单元，来源为 MCP 规范 `tools/list`。
_Avoid_: 工具清单面

**工具投毒 (tool poisoning)**:
攻击者控制或篡改 MCP server 返回的工具描述、注解或输出，向模型注入误导性上下文以改变其调用决策（OWASP MCP Top 10 `MCP03:2025`）。
_Avoid_: 工具描述投毒

**调用劫持 (call hijacking)**:
以伪造调用块或返回值替代真实请求/响应，使 agent 基于被篡改结果继续行动（OWASP MCP Top 10 `MCP06:2025`）。
_Avoid_: 工具劫持

**信任级别 (trust level)**:
目标侧对 MCP server 的可信度标注（已观察 `trusted` / `untrusted` / `shadow`），决定客户端是否采信其工具描述与返回；是投毒效果定级的输入。
_Avoid_: 信任等级

**工具遥测 (tool telemetry)**:
目标侧随工具调用结果下发的结构化判定数据（被调工具、所需权限、策略决定、影响半径、是否成功）；本仓库以其为确定性评分信号替代 LLM 判定。
_Avoid_: MCP 遥测、调用遥测

**校验预言机 (validation oracle)**:
以「标识 + 答案」为输入的判定接口；目标无 `ai_vector.txt` 时，以「提交成功 + 值原文同屏」构成等价 flag 双通道。
_Avoid_: 答案校验器

**A2A (Agent-to-Agent)**:
多智能体间的通信协议与信任关系，可被消息操纵、冒充或破坏工作流。

**Embedding**:
嵌入向量，可经反演/信息提取泄露敏感数据。

**AI 资产 (AI asset)**:
目标环境中承担推理/检索/编排/工具调用的可识别组件实例（LLM 引擎、模型服务、RAG、向量库、agent、MCP 工具面、护栏），是 `recon-ai` 的输出单元。
_Avoid_: AI 靶标、AI 组件资产

**资产清单 (asset inventory)**:
`recon-ai` 产出的结构化资产集合，每条含资产ID、类别、产品/引擎、版本、暴露端点、凭证指纹、关联证据 step_id 七字段，可被下游按资产ID引用。
_Avoid_: 资产报表

**证据清单 (evidence manifest)**:
按步骤逐行登记证据片段的 JSONL 记录，含 step_id、命令、产物哈希、时间戳、执行分级、留存入径与件套状态，用于整份证据集独立复核。
_Avoid_: 证据目录、证据汇总表

**演练目标 (drill target)**:
经授权用于演练的目标主机或入口（如 AIVP 实例），非 OSAI 正式考试环境，结论不外推。
_Avoid_: 靶机、靶标

## PyRIT 实现层

实现框架为 PyRIT，版本锁定 `pyrit==1.1.0`（ADR-0004）。下列为 v1.1.0 原生对象的规范称谓；来源见 `docs/research/pyrit-canonical-references.md`。

**攻击策略 (attack strategy)**:
PyRIT v1.1.0 中封装单一攻击手法的可复用组件（`pyrit.executor.attack` 的 `*Attack`，如 `PromptSendingAttack`、`RedTeamingAttack`）。
_Avoid_: 攻击编排器（v1.1.0 前称 orchestrator，已弃用）

**XPIA 工作流 (XPIA workflow)**:
承担间接提示注入（跨域提示注入）的工作流策略，位于 `pyrit.executor.workflow`（`XPIATestWorkflow` / `XPIAWorkflow`）；**不是** `*Attack` 攻击策略。`XpiaAttack` 在 v1.1.0 不存在。
_Avoid_: 跨域注入攻击策略、间接注入编排器

**执行器 (AttackExecutor)**:
驱动并执行一个攻击策略的运行时组件（`AttackExecutor().execute_attack_async`），负责策略、目标、转换器与评分器的协同。
_Avoid_: 攻击执行器

**目标 (Target)**:
接收提示并返回模型响应的 endpoint 抽象（如 `OpenAIChatTarget`、`HTTPTarget`），是攻击策略发力的对象。
_Avoid_: 靶机、靶标（指红队计分主机，非 PyRIT Target）

**转换器 (Converter)**:
对提示做编码/混淆/格式变换的组件（经 `AttackConverterConfig` 链式组合），用于绕过护栏或构造载荷。
_Avoid_: 转译器、转换器链

**评分器 (Scorer)**:
判定攻击是否生效的组件（如 `SelfAskTrueFalseScorer`、`SubStringScorer`），提供线索或决定性证据。
_Avoid_: 评判器、评测器

**记忆 (Memory)**:
跨步骤或跨会话暂存对话与状态的存储后端（`pyrit.memory` 的 `SQLiteMemory` / `AzureSQLMemory`），经 `initialize_pyrit_async(memory_db_type=...)` 选择；跨会话验证须用 `SQLite` 文件型后端。
_Avoid_: 记忆库、记忆体

**对象图 (object graph)**:
一次攻击的代码装配形态 = 攻击策略 + 目标 + 转换器 + 评分器 + 记忆 的组合实例，由单一公开入口运行时构造。
_Avoid_: 装配图

**证据片段 (evidence fragment)**:
一次攻击步骤经 `collect_evidence.py` 落盘的原子证据单元（三件套、AI 交互日志、flag 双通道），是评分与复核的基本单位。
_Avoid_: 证据切片

## 工程治理

**能力域 (capability domain)**:
大纲中的 11 个模块之一，是技能映射与分层的对齐基准。

**技能 (skill)**:
符合《治理规范》§4「技能工程规范」的自包含能力包（元信息 + 执行体 + 质量门 + 校验标准）。

**智能体 (agent)**:
运行时执行技能的载体，负责编排技能完成任务。

**质量基线 (quality baseline)**:
对证据、可复现性、AI 工具记录与报告提交的可度量下限。

**证据 (evidence)**:
一次攻击动作的完整记录 = 确切命令 + 输出 + 截图（+ AI 交互日志）。

**TTP**:
Tactics, Techniques, and Procedures（战术、技术与流程），描述攻击者的行为组合。

## 报告工程

**报告组装器 (report assembler)**:
把 `collect_evidence.py` 片段与 `loot` 登记簿组装为对齐 S1 的考试报告 PDF/`.7z`（即 `report-exam`），复用既有证据管线，不重新取证。
_Avoid_: 报告生成器（易与模板引擎混淆）

**双版 (dual-version)**:
同一次考试产出 EN 官方版（提交候选）与 ZH 内部镜像；两版事实逐字一致，ZH 不上交。
_Avoid_: 双语（易被误解为单文档中英混排）

**证据归属 (evidence attribution)**:
报告每段标注来源片段路径（如 `（证据：evidence/.../aia-0X.md）`），使读者可回溯至 `collect_evidence` 原子单元。
_Avoid_: 证据溯源（与审计溯源混淆）

**五段式 (five-section host format)**:
report-exam 中每台计分主机固定五段：枚举 / 漏洞描述与完整利用 / 提权（如适用）/ flag 取证 / 证据归属，对齐 S1 §7.2。
_Avoid_: 五节格式

## CI/CD 治理

**流水线 (pipeline)**:
由若干阶段门禁串联的自动化质量与交付链路，强制实施《治理规范》§8 的校验。

**阶段门禁 (stage gate)**:
流水线中「进入下一阶段前必须通过」的判定点，未过即阻断，不得带病推进。

**合规校验器 (compliance validator)**:
对技能/文档执行 §4.2、§8.2 客观判据的自动化脚本（如 `validate_skill`、`check_glossary`）。

**纳管 (onboarding)**:
将新增 agent/skill 组件登记入流水线与 §4.4 流程，含 PR 门禁与验收。
