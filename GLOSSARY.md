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
由单一公网入口起始、贯穿 3 台主机的路径；共 2 条汇聚于域控。

**独立主机 (standalone host)**:
取得任一链内网立足点后方可达的 AI 向量主机，单计 15 分。

**域控 (Domain Controller, DC)**:
两条链汇聚的共享主机，持有 `proof.txt`；flag 仅可提交一次。

**AI 向量 (AI vector)**:
针对 AI 组件（agent/RAG/MCP/embedding 等）的攻击路径，每台 15 分。
_Avoid_: AI 攻击向量

**传统向量 (traditional vector)**:
经典网络渗透路径（服务利用/横向/提权等），每台 10 分。

**诱饵机 (decoy)**:
故意不设漏洞的主机（0 分），增加真实性；共 2 台。
_Avoid_: rabbit hole、蜜罐

**诱饵判定清单 (decoy judgment list)**:
`decoy-detect` 产出的结构化判定结果，每含主机标识/命中维度/具体依据/放弃理由/时间戳五字段，标「诱饵」或「不确定-已放弃」，供 `threat-model` 排除与 `report-exam` 引用。
_Avoid_: 诱饵清单

**三维度特征 (three-dimension decoy signal)**:
判定诱饵机的三类信号：行为特征（无 AI 基础设施面）、漏洞缺失（无高价值服务/无可达入口）、无价值特征（枚举干净/信息缺失/与资产清单不符）；任一类命中即疑似诱饵。
_Avoid_: 三维特征

**时间盒 (time-box)**:
单台疑似诱饵主机的判定硬性时长上限（`decoy-detect` 取 ≤30min）；超时记「不确定-已放弃」并主动放弃，不在 0 分主机空耗。
_Avoid_: 时间限制

**计分目标 (scored target)**:
8 个计分主机之一（6 链式+1 独立+1 域控）。

**flag**:
证明已攻陷的证据文件：`trad_vector.txt`/`ai_vector.txt`/`proof.txt`。

**及格线 (pass threshold)**:
75/100 分，达此方可获 OSAI 认证。

## 攻击面

**RAG (Retrieval-Augmented Generation)**:
检索增强生成流水线，可被知识库投毒与检索层操纵。

**知识库投毒 (knowledge-base poisoning)**:
向 RAG 语料注入恶意文档使目标 top-k 检索含攻击者可控内容；PoisonedRAG 双条件（检索+生成）是其理论内核（`attack-rag` 路径 A）。
_Avoid_: 知识投毒、投毒RAG

**检索层操纵 (retrieval manipulation)**:
以语料注入或 embedding 碰撞改变检索集合与排序（OWASP LLM08 向量/嵌入弱点），须投毒前后 top-k 对照取证（`attack-rag` 路径 B）。

**间接注入 (indirect injection)**:
经检索片段或外部数据源注入指令，使下游 agent 消费上下文时执行非预期动作（OWASP LLM01 / ASI06）；RAG 场景由 `XPIATestWorkflow` 承载，非 `*Attack`。

**下游决策影响 (downstream decision impact)**:
检索层操纵改变下游 agent 输出/动作的因果证明，须 baseline vs manipulated 双次捕获对照（`attack-rag` 路径 C）。

**MCP (Model Context Protocol)**:
模型上下文协议与工具集成面，可被滥用提权或执行非预期动作。

**工具面 (tool surface)**:
一次会话内 agent 可调用的全部 MCP 工具及元信息，每条含 server/工具名/描述/权限范围/信任级别；`attack-mcp-tool` 枚举单元，来源 MCP 规范 `tools/list`。
_Avoid_: 工具清单面

**工具投毒 (tool poisoning)**:
攻击者控制/篡改 MCP server 返回的工具描述/注解/输出，向模型注入误导上下文以改变调用决策（OWASP MCP Top 10 `MCP03:2025`）。
_Avoid_: 工具描述投毒

**调用劫持 (call hijacking)**:
以伪造调用块/返回值替代真实请求/响应，使 agent 基于篡改结果继续行动（OWASP MCP Top 10 `MCP06:2025`）。
_Avoid_: 工具劫持

**信任级别 (trust level)**:
目标侧对 MCP server 的可信度标注（`trusted`/`untrusted`/`shadow`），决定客户端是否采信其工具描述与返回；投毒效果定级输入。
_Avoid_: 信任等级

**工具遥测 (tool telemetry)**:
目标侧随工具调用结果下发的结构化判定数据（被调工具/所需权限/策略决定/影响半径/是否成功）；本仓库以其为确定性评分信号替代 LLM 判定。
_Avoid_: MCP 遥测、调用遥测

**校验预言机 (validation oracle)**:
以「标识 + 答案」为输入的判定接口；目标无 `ai_vector.txt` 时，以「提交成功 + 值原文同屏」构成等价 flag 双通道。
_Avoid_: 答案校验器

**A2A (Agent-to-Agent)**:
多智能体间通信协议与信任关系，可被消息操纵/冒充/破坏工作流。

**多智能体拓扑 (multi-agent topology)**:
目标内各智能体角色/连接/调用关系；a2a-01 发现产物，决定后续注入与冒充落点。

**消息操纵 (message manipulation)**:
在 A2A 总线注入/篡改智能体间消息，改变下游行为；a2a-02 攻击原语。

**智能体冒充 (agent impersonation)**:
伪造 AgentCard/身份使目标视为可信对端；a2a-03 攻击原语。

**共享记忆投毒 (shared memory poisoning)**:
改写多智能体共享记忆存储条目，使后续回合沿用污染内容；a2a-04 攻击原语。

**上下文投毒 (context poisoning)**:
污染智能体共享上下文与全局 prompt，影响同会话全部参与者决策；a2a-05 攻击原语。

**Embedding**:
嵌入向量，可经反演/信息提取泄露敏感数据。

**embedding 反演 (embedding inversion)**:
从 dense embedding 还原源文本的攻击（vec2text 多步纠错/填槽/beam search），属 OWASP LLM08 敏感信息泄露面；`attack-embeddings` emb-03 与 Ch6 增量反演原语。
_Avoid_: 向量逆推

**成员推断 (membership inference)**:
判定某样本是否属于训练/检索集的攻击；以 embedding 空间噪声邻居（Noisy Neighbors）困惑度差为判据；emb-04 攻击原语。
_Avoid_: 成员判定

**对抗样本 (adversarial example)**:
经细微扰动使 embedding/检索/分类结果偏离基线的输入（HotFlip/连续空间扰动）；emb-05 攻击原语。
_Avoid_: 对抗扰动样本

**向量库反查 (vector store lookup)**:
直接查询向量库、从嵌入空间反查知识库文档块（越权/数据外泄面，与 `attack-rag` 共享向量面）；emb-06 攻击原语。
_Avoid_: 向量检索提取

**AI 资产 (AI asset)**:

目标环境内承担推理/检索/编排/工具调用的可识别组件实例（LLM 引擎、模型服务、RAG、向量库、agent、MCP 工具面、护栏），`recon-ai` 输出单元。
_Avoid_: AI 靶标、AI 组件资产

**资产清单 (asset inventory)**:
`recon-ai` 产出的结构化资产集合，每条含资产ID、类别、产品/引擎、版本、暴露端点、凭证指纹、关联证据 step_id 七字段，可被下游按资产ID引用。
_Avoid_: 资产报表

**威胁模型 (threat model)**:
`threat-model` 技能产出，把资产清单转化为优先级攻击图的规划结果，驱动 §4.5 编排；不含实际攻击利用。
_Avoid_: 威胁建模文档

**信任边界 (trust boundary)**:
按可达性对资产归类（同内网/域、需先取得立足点、AI向量机/独立机直接可达），由分析师分类层标注，是绘制最短攻击路径的前提。
_Avoid_: 信任域划分

**最短攻击路径 (shortest attack path)**:
对 top-N 高价值资产计算的攻击路径（入口→横向→提权→AI利用→flag），标起止/阶段/耗时/依赖子技能；未就绪标「待补」。
_Avoid_: 最优攻击链

**优先级攻击图 (prioritized attack graph)**:
以最高杠杆资产为根、最短路径为边、诱饵机排除在外的有向图，输出 §4.5 编排顺序（先 AI向量机/独立机→再传统链→最后域控 `proof.txt` 单次提交）。
_Avoid_: 攻击优先级清单

**证据清单 (evidence manifest)**:
按步骤逐行登记证据片段的 JSONL，含 step_id/命令/产物哈希/时间戳/执行分级/留存入径/件套状态，供证据集独立复核。
_Avoid_: 证据目录、证据汇总表

**演练目标 (drill target)**:
经授权用于演练的目标主机或入口（如 AIVP 实例），非 OSAI 正式考试环境，结论不外推。
_Avoid_: 靶机、靶标

## 战利品管理

**战利品 (loot)**:
红队作战全程取得的凭据、会话、flag 与攻击路径的统称；每条以编号 `L-<n>` 登记于战利品登记簿，禁止散落于对话上下文（§5.2）。
来源：`skills/loot-manage/SKILL.md`。

**战利品登记簿 (loot registry)**:
`loot/registry.md` 的单一事实源 markdown 表，列结构固定 8 列（编号/类型/内容/来源主机/证据片段路径/时间戳/状态/双通道）；只存证据片段路径指针，不重复存储证据本体。
来源：`skills/loot-manage/SKILL.md`。

**攻击路径 (attack path)**:
单技能内「入口 → 主机 → 横向」的路径摘要，登记于战利品登记簿「攻击路径」小节，供报告 High-Level Attack Path 复用；与「攻击链」（跨 3 台主机的计分路径）不同，不可混用。
来源：`skills/loot-manage/SKILL.md`；`docs/research/loot-manage-canonical.md` §7。

## AI 供应链 (supply chain)

**AI 供应链 (AI supply chain)**:
由模型仓库、依赖源、数据管道与信任边界构成的 AI 产物供应链，可被投毒污染间接影响下游模型；对齐 OWASP Agentic ASI04 / LLM03 / LLM05。

**AI向量机 (AI vector machine)**:
计 15 分的 AI 向量主机（链内/独立机），flag 为 `ai_vector.txt`；`attack-supply-chain` 等 AI 技能目标计分单元；区别于「AI 向量（攻击路径）」：前者主机，后者路径。

**数据集投毒 (dataset poisoning)**:
污染训练/检索数据，使模型或 RAG 产物偏向攻击者（OWASP LLM03）。

**模型投毒 (model poisoning)**:
植入后门权重或恶意适配器，使模型在触发条件下输出攻击者期望结果。

**适配器投毒 (adapter poisoning)**:
以恶意 LoRA/适配器文件污染基座模型的推理行为（如恶意 safetensors 适配器）。

**数据管道投毒 (data pipeline poisoning)**:
在 ETL/预处理环节注入恶意变换，污染下游数据集。

**依赖投毒 (dependency poisoning)**:
在包索引/镜像/requirements 注入恶意依赖（typosquat 或替换），构建或安装时执行非预期代码（OWASP LLM05）。仅指依赖面，区别于数据集/模型投毒。

**构建触发 (build trigger)**:
使投毒在构建或推理时执行非预期代码的触发机制（setup 钩子 / 反序列化）。

## PyRIT 实现层

实现框架为 PyRIT，版本锁定 `pyrit==1.1.0`（ADR-0004）。下列为 v1.1.0 原生对象的规范称谓；来源见 `docs/research/pyrit-canonical-references.md`。

**攻击策略 (attack strategy)**:
PyRIT v1.1.0 封装单一攻击手法的可复用组件（`pyrit.executor.attack` 的 `*Attack`，如 `PromptSendingAttack`、`RedTeamingAttack`）。
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
对提示做编码/混淆/格式变换的组件（经 `AttackConverterConfig` 链式组合），绕过护栏或构造载荷。
_Avoid_: 转译器、转换器链

**评分器 (Scorer)**:
判定攻击是否生效的组件（如 `SelfAskTrueFalseScorer`、`SubStringScorer`），提供线索或决定性证据。
_Avoid_: 评判器、评测器

**记忆 (Memory)**:
跨步骤或跨会话暂存对话与状态的存储后端（`pyrit.memory` 的 `SQLiteMemory` / `AzureSQLMemory`），经 `initialize_pyrit_async(memory_db_type=...)` 选择；跨会话验证须用 `SQLite` 文件型后端。
_Avoid_: 记忆库、记忆体

**对象图 (object graph)**:
一次攻击的代码装配形态=攻击策略+目标+转换器+评分器+记忆的组合实例，由单一公开入口运行时构造。
_Avoid_: 装配图

**证据片段 (evidence fragment)**:
一次攻击步骤经 `collect_evidence.py` 落盘的原子证据单元（三件套/AI 交互日志/flag 双通道），评分与复核基本单位。
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
把 `collect_evidence.py` 片段与 `loot` 登记簿组装为对齐 S1 的考试报告 PDF/`.7z`（即 `report-exam`），复用既有证据管线不重新取证。
_Avoid_: 报告生成器（易与模板引擎混淆）

**双版 (dual-version)**:
同次考试产出 EN 官方版（提交候选）与 ZH 内部镜像；两版事实逐字一致，ZH 不上交。
_Avoid_: 双语（易被误解为单文档中英混排）

**证据归属 (evidence attribution)**:
报告每段标注来源片段路径（如 `（证据：evidence/.../aia-0X.md）`），使读者可回溯至 `collect_evidence` 原子单元。
_Avoid_: 证据溯源（与审计溯源混淆）

**五段式 (five-section host format)**:
report-exam 每台计分主机固定五段：枚举/漏洞描述与完整利用/提权（如适用）/flag 取证/证据归属，对齐 S1 §7.2。
_Avoid_: 五节格式

## 提交前校验（verify-evidence）

**访问证明 (access proof)**:
flag 取证截图同屏含 `whoami`/`id` 与 flag 值，排除他人截图与猜测（§6.2.2）。
_Avoid_: 权限截图

**判定分级 (verdict tier)**:
阻断项（违反「必须」禁提交）、缺失项（未取分预期缺失）、核实闸（不阻断但不可提交）三档互斥（§7.3）。

**机读校验结果 (machine-readable result)**:
`schema_version` 化的固定键 JSON（九项 checks + 分级列表 + 结论），供 CI 与组装侧消费。

## CI/CD 治理

**流水线 (pipeline)**:
由若干阶段门禁串联的自动化质量与交付链路，强制实施《治理规范》§8 校验。

**阶段门禁 (stage gate)**:
流水线中进入下一阶段前必须通过之判定点，未过即阻断，不得带病推进。

**合规校验器 (compliance validator)**:
对技能/文档执行 §4.2、§8.2 客观判据的自动化脚本（如 `validate_skill`/`check_glossary`）。

**纳管 (onboarding)**:
将新增 agent/skill 组件登记入流水线与 §4.4 流程，含 PR 门禁与验收。

## 侦察闭环（recon-ai）

术语（应用族/基路径/运行标识/未决面/缺口台账/自校验）见 `docs/operations/recon-ai-closed-loop-design.md`。
_Avoid_: 应用类型、子路径、证据时效、未知资产、自验证、覆盖表
## AI 基础设施 (AI infrastructure)

**模型服务器 (model server)**:
面向推理请求的服务进程（vLLM / Triton / Ollama 等）；是否存在以「状态码 + `Content-Type` + 响应结构」三元组判定，不以 HTTP 200 为据。
来源：`docs/research/attack-infra-canonical.md` §3（P-1、P-3）。

**推理网关 (inference gateway)**:
统一转发多家模型上游的代理层（如 LiteLLM），其配置常存放上游凭据；检索只记凭据指纹。
来源：同上 F-5。

**降级结论 (outcome verdict)**:
`attack-infra` 每步的互斥判定结论；五值语义与非 `EXPLOITED` 的依据要求见 `docs/operations/attack-infra-terms.md` §2。
来源：`docs/operations/attack-infra-terms.md` §2。

## 自动化编排（tooling-automate）

**任务清单 (task manifest)**:
任务级声明式清单（类别/目标/step/输入/输出/触发/分类七字段），驱动 `tooling-automate` 编排层批量执行；区别于「证据清单」（事后登记）。
_Avoid_: 任务表

**编排层 (orchestration layer)**:
`tooling-automate` 唯一编排件：S-1 统一编排入口（CLI 与库共用、命令执行器可注入）只串联既有共享工具（`collect_evidence` 与各校验脚本），不重写判据、不含攻击逻辑；每件输出附`复用声明`。

**推断探测 (inference probing)**:
向 RAG 接口发查询、把响应分段与各候选模型向量比对以识别 embedding 模型（top5 平均相似度判据）；Ch6 §6.2。
_Avoid_: 推理探针

**块分选 (chunk triage)**:
在全量 embedding 上用敏感度探针级联筛出高价值块、无需先反演；Ch6 §6.2。
_Avoid_: 块筛选
