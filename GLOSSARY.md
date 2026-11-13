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
