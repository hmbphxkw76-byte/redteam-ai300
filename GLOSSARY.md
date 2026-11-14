# OSAI AI-300 红队工程

本项目围绕 OffSec AI Red Teamer（OSAI）认证构建一套「agent + skill」红队工程能力。本术语表为《治理规范》与全部技能/智能体提供唯一、稳定的词汇基准。

## Language

本术语表采用「中文主词 + 英文规范词」双语；正文中英文规范词保留原样，避免与官方材料产生歧义。

## 考试与评分

**OSAI**:
OffSec AI Red Teamer 认证，考核对 AI 化企业环境的实战红队能力。
_Avoid_: OSAI+、AI-300（见下）

**AI-300**:
OffSec 的 AI 红队训练课程（Advanced AI Red Teaming），11 个模块构成大纲。
_Avoid_: OSAI（认证本身）

**攻击链 (attack chain)**:
由单一公网入口起始、贯穿 3 台主机的独立攻击路径；环境中共 2 条，最终汇聚于域控。

**独立主机 (standalone host)**:
取得任一链的内网立足点后才可达的 AI 向量主机，单独计 15 分。

**域控 (Domain Controller, DC)**:
两条链共同汇聚的共享主机，持有 `proof.txt`；其 flag 仅可提交一次。

**AI 向量 (AI vector)**:
针对 AI 组件（agent、RAG、MCP、embedding 等）的攻击路径，每台 15 分。
_Avoid_: AI 攻击向量

**传统向量 (traditional vector)**:
经典网络渗透路径（服务利用、横向、提权等），每台 10 分。

**诱饵机 (decoy)**:
环境内「故意不设漏洞」的主机（0 分），用于增加真实性；共计 2 台，不计分。
_Avoid_: rabbit hole、蜜罐

**计分目标 (scored target)**:
8 个计分主机之一（6 台链式 + 1 独立 + 1 域控）。

**flag**:
证明已攻陷目标的证据文件：`trad_vector.txt`、`ai_vector.txt`、`proof.txt`。

**及格线 (pass threshold)**:
75/100 分，达到方可获得 OSAI 认证。

## 攻击面

**RAG (Retrieval-Augmented Generation)**:
检索增强生成流水线，可被知识库投毒与检索层操纵。

**MCP (Model Context Protocol)**:
模型上下文协议与工具集成面，可被滥用以提权或执行非预期动作。

**A2A (Agent-to-Agent)**:
多智能体间的通信协议与信任关系，可被消息操纵、冒充或工作流破坏。

**Embedding**:
嵌入向量，可经反演/信息提取泄露敏感数据。

## PyRIT 实现层

本仓库以 PyRIT 为 AI 红队攻击的实现框架（版本锁定 `pyrit==1.1.0`，见 ADR-0004）。下列术语为 PyRIT v1.1.0 原生对象在本文档中的规范称谓；来源统一为 PyRIT 官方文档 `microsoft.github.io/PyRIT/1.1.0/` 与 `docs/research/pyrit-canonical-references.md`。

**攻击策略 (attack strategy)**:
PyRIT v1.1.0 中封装单一攻击手法的可复用组件（位于 `pyrit.executor.attack` 的 `*Attack` 类，如 `PromptSendingAttack`、`RedTeamingAttack`），接收目标与评分配置后产出攻击结果。
_Avoid_: 攻击编排器（v1.1.0 前称 orchestrator，已弃用）

**XPIA 工作流 (XPIA workflow)**:
PyRIT v1.1.0 中承担间接提示注入（跨域提示注入）的工作流策略，位于 `pyrit.executor.workflow`（`XPIATestWorkflow` / `XPIAWorkflow`），由投放目标、摄取目标与评分器协同；**不是** `*Attack` 攻击策略。来源：`microsoft.github.io/PyRIT/1.1.0/api/pyrit-executor-workflow`。`XpiaAttack` 在 v1.1.0 不存在，属已排除名称。
_Avoid_: 跨域注入攻击策略、间接注入编排器

**执行器 (AttackExecutor)**:
PyRIT 中驱动并执行一个攻击策略的运行时组件（`AttackExecutor().execute_attack_async`），负责编排策略、目标、转换器与评分器的协同。
_Avoid_: 攻击执行器

**目标 (Target)**:
PyRIT 中接收提示并返回模型响应的 endpoint 抽象（如 `OpenAIChatTarget`、`HTTPTarget`），是攻击策略发力的对象。
_Avoid_: 靶机、靶标（指红队计分主机，非 PyRIT Target）

**转换器 (Converter)**:
PyRIT 中对提示做编码/混淆/格式变换的组件（经 `AttackConverterConfig` 配置链式组合），用于绕过护栏或构造载荷。
_Avoid_: 转译器、转换器链

**评分器 (Scorer)**:
PyRIT 中判定攻击是否生效的组件（如 `SelfAskTrueFalseScorer`、`SubStringScorer`），提供线索或决定性证据。
_Avoid_: 评判器、评测器

**记忆 (Memory)**:
PyRIT 中跨步骤或跨会话暂存对话与状态的存储后端（`pyrit.memory` 的 `SQLiteMemory` 文件型 / 内存型、`AzureSQLMemory`），经 `initialize_pyrit_async(memory_db_type=...)` 选择 `InMemory` / `SQLite` / `AzureSQL`；跨会话验证须用 `SQLite` 文件型后端。
_Avoid_: 记忆库、记忆体

**对象图 (object graph)**:
一次攻击在代码中的装配形态 = 攻击策略 + 目标 + 转换器 + 评分器 + 记忆 的组合实例，由单一公开入口在运行时构造。
_Avoid_: 装配图

**证据片段 (evidence fragment)**:
一次攻击步骤经 `collect_evidence.py` 落盘的原子证据单元（含三件套、AI 交互日志、flag 双通道记录），是评分与复核的基本单位。
_Avoid_: 证据切片

## 工程治理

**能力域 (capability domain)**:
大纲中的 11 个模块之一，是技能映射与优先级分层的对齐基准。

**技能 (skill)**:
符合《治理规范》第四章「技能工程规范」的自包含能力包（元信息 + 执行体 + 质量门 + 校验标准）。

**智能体 (agent)**:
运行时执行技能的载体，负责编排技能完成实战任务。

**质量基线 (quality baseline)**:
对证据、可复现性、AI 工具记录与报告提交设定的可度量下限。

**证据 (evidence)**:
一次攻击动作的完整记录 = 确切命令 + 关键输出 + 截图（+ AI 交互日志）。

**TTP**:
Tactics, Techniques, and Procedures（战术、技术与流程），描述攻击者的行为组合。

## CI/CD 治理

**流水线 (pipeline)**:
由若干阶段门禁串联的自动化质量与交付链路，强制实施《治理规范》第八章的校验。

**阶段门禁 (stage gate)**:
流水线中「进入下一阶段前必须通过」的判定点，未过即阻断，不得带病推进。

**合规校验器 (compliance validator)**:
对技能/文档执行 §4.2、§8.2 客观判据的自动化脚本（如 `validate_skill`、`check_glossary`）。

**纳管 (onboarding)**:
将新增 agent/skill 组件登记入流水线与《治理规范》§4.4 的流程，含 PR 门禁与验收。
