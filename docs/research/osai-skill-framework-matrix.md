# OSAI (AI-300) 技能 × 最佳攻击框架组合对照清单

> **性质**：研究/决策文档（非规范正文）。基于 `docs/research/osai-ai300-framework-decision.md` 的分层 best-of-breed 结论，逐技能拆解推荐框架组合。
> **核验日期**：2026-11-15（GMT+8）。框架版本与考试事实同上游决策文档；技能优先级（P0/P1/P2）取自各 `skills/*/SKILL.md` 元数据。
> **总原则**：**没有任何单一框架覆盖全部 10 考纲场景**。每个 skill 按"主攻框架 + 辅助固化 + 适配器（自定义/专项点解/Kali）"三层组合；PyRIT(v1.1.0) 是 AI 向量深度利用 + 证据留痕的**规范内核**，但仅在它真正占优的场景做主角。

---

## 0. 框架角色图例（来自决策文档）

| 角色 | 框架 | 一句话定位 |
|---|---|---|
| 首扫层 | **garak** (v0.17.1) | LLM/模型层快速漏洞扫描，**离线、无需 judge** |
| 深度层（内核） | **PyRIT** (v1.1.0) | AI 向量多轮编排（Crescendo/PAIR/TAP）+ SQLiteMemory 证据留痕 |
| 固化层 | **promptfoo** (0.125.1) | agent/MCP 声明式用例（**须自托管 provider、禁用联网插件**） |
| 适配层 | **专项点解** | A2ASecBench / mcp-scan / agentic-radar / AgentPoison / vec2text / ModelScan / IBM ART |
| 落地层 | **Kali 工具链** | nmap/burp/impacket/云 CLI — 传统向量/横向/DC/云 |
| 协作层 | **许可 AI 助手** | payload 编写/排障/判读 co-pilot（OSAI 明确允许） |

---

## 1. 优先级总排序（按考试杠杆：AI 主分面 + 报告关 + 链入口）

> 考试计分：AI 向量占 75/100，传统向量 20，DC 5；报告缺失=零分风险。下表为框架组合的**掌握与落地优先顺序**。

| 序 | Skill | 优先级 | 主攻框架组合 | 考试杠杆 |
|---:|---|:--:|---|---|
| 1 | attack-ai-agent | P0 | PyRIT（内核）+ promptfoo agent 插件 + 自定义 | AI 主分最深、仓库已建成 canonical |
| 2 | attack-mcp-tool | P0 | promptfoo(MCP) + mcp-scan/agentic-radar + PyRIT HTTPTarget | 15 分场景类且 PyRIT 无原生策略 |
| 3 | attack-rag | P0 | PyRIT + PoisonedRAG + 自定义 | AI 主分面 |
| 4 | report-exam | P0 | PyRIT 证据导出 + promptfoo 报告 + 五段式模板 + 截图 | 报告关=生死 |
| 5 | verify-evidence | P0 | PyRIT 证据五件套/三件套 + 双通道核验 | 防"面板+截图缺失"零分 |
| 6 | recon-ai | P0 | garak 首扫 + Kali 侦察 + 许可 AI | 开局映射 AI 组件 |
| 7 | foothold-traditional | P0 | 纯 Kali OSCP 工具链 + 自定义 | 链入口 + 传统 10 分/台 |
| 8 | loot-manage | P0 | 结构化凭据库（脚本/笔记）+ 许可 AI | 全程凭据与证据归集 |
| 9 | attack-embeddings | P1 | vec2text + PyRIT + 自定义 | AI 场景（LLM08 实证） |
| 10 | attack-multi-agent | P1 | A2ASecBench + a2a-scanner + PyRIT HTTPTarget | AI 场景（A2A） |
| 11 | attack-supply-chain | P1 | ModelScan + IBM ART + PyRIT | AI 场景（供应链） |
| 12 | attack-infra | P1 | Kali + 云 CLI + MS AIRT Labs + 自定义 | AI 基础设施/云（框架普遍缺席） |
| 13 | threat-model | P1 | MITRE ATLAS/OWASP + 文档 + 许可 AI | 规划层，框架是被建模对象 |
| 14 | decoy-detect | P1 | 纯 Kali/网络侦察 + 人工 + 许可 AI | 识别 2 台诱饵机省时 |
| 15 | capstone-rehearse | P2 | 全栈串联（garak→PyRIT+promptfoo+专项+Kali+AI） | 综合演练 |
| 16 | tooling-automate | P2 | 自定义脚本编排各 CLI + CI + 许可 AI | 效率杠杆，建于各框架之上 |
| 17 | attack-jailbreak | P1 | PyRIT（内核多轮策略）+ 转换器 + 分级评分 + 自定义 | AI 主分面（护栏绕过），PyRIT 占优场景 |
| 18 | attack-multimodal | P1 | PyRIT（多模态 target）+ 转换器 + 自定义 + 复用 attack-rag 原语 | AI 主分面（跨模态注入） |

> 序号 17/18 为 P3 缺口补齐新增（jailbreak/multimodal），经一手源核实 PyRIT 1.1.0 在两场景占优，按 GOVERNANCE §8.3 显式声明纳入矩阵。详见 `docs/research/attack-jailbreak-multimodal-canonical.md` §4。

> **2026-11-28 补遗（R06/R12）**：技能注册以 GOVERNANCE §4.4 的 **20 技能**为准——本表 18 项之外另有 `foothold-ad`（P0 域控收敛，Kali/impacket 离线工件解析，无 AI 框架参与）与 `osai-orchestrator`（P2 纯逻辑编排，无攻击框架）。当前 PyRIT 锁定目标为 **1.2.1**（`requirements.txt` 与 CI `--target 1.2.1`）；本表 v1.1.0 API 事实为历史基线，1.2.x 适配以 `docs/research/pyrit-version-tracking-1.2.x.md` 与 `docs/operations/pyrit-compat-alignment-matrix.md` 为准（1.2.0 适配集覆盖 1.2.1）；框架归属追踪 issue #252。

---

## 2. 逐技能明细

### ① attack-ai-agent（D3 / P0）
- **推荐组合**：**PyRIT(v1.1.0) 内核** + promptfoo agent 插件（excessive-agency / tool-discovery / memory-poisoning 固化） + 自定义脚本（业务逻辑手动利用）。
- **组合方式**：复用既有 `tools/attack_ai_agent/` 的 `RealPyRITBackend` 单 seam 承载多轮攻击（Crescendo/PAIR），`SQLiteMemory` 留证；promptfoo 声明式固化已知 agent 漏洞类；手搓脚本补目标特有业务逻辑。
- **选择理由**：本仓库已建成经一手源核实的 PyRIT 1.1.0 实现（双模型命名空间 `OPENAI_CHAT_*`/`OPENAI_SCORER_*`），深度多轮编排无可替代；promptfoo 补 agent 攻击广度。
- **适用场景**：agentic 主机（FinBot 类多 agent 平台、订单/退款/邮件 agent）。

### ② attack-mcp-tool（D7 / P0）
- **推荐组合**：**promptfoo(MCP 插件)** + mcp-scan/agentic-radar（静态+运行时扫描） + **PyRIT HTTPTarget 回调**（深度多轮，复用 `attack-mcp-tool` 双形态 seam） + MCP Inspector/Python SDK（协议级 recon）。
- **组合方式**：mcp-scan 扫 rug-pull / cross-server shadowing；agentic-radar 可视化工作流并映射 OWASP；promptfoo 固化 MCP 攻击用例；PyRIT 通过 `HTTPTarget`+回调打深度多轮。
- **选择理由**：**PyRIT v1.1.0 无原生 MCP 攻击策略**（决策文档已核实），MCP 是 15 分场景类，必须靠 promptfoo + 专项点解主导，PyRIT 仅做深度补位。
- **适用场景**：暴露 MCP server 的主机（Appsecco vulnerable-mcp-servers-lab 类）。

### ③ attack-rag（D5 / P0）
- **推荐组合**：**PyRIT（RAG 多轮 + 证据）** + PoisonedRAG（USENIX Sec'25 官方，知识库投毒） + 自定义脚本（向量库越权/间接注入）。
- **组合方式**：PoisonedRAG 跑黑盒/白盒投毒；PyRIT 编排间接提示注入并利用 `SQLiteMemory` 留证；手搓脚本测向量库访问控制绕过。
- **选择理由**：RAG 是 AI 主分面；PoisonedRAG 是该场景权威实现（97% 劫持率实证），PyRIT 补编排与证据。
- **适用场景**：RAG 知识库/文档助手主机。

### ④ report-exam（D11 / P0）
- **推荐组合**：**PyRIT SQLiteMemory 证据导出** + promptfoo 结构化报告 + 手动截图 + 本仓库五段式模板（`report-exam`）。
- **组合方式**：PyRIT memory → 结构化证据；promptfoo/模板 → 报告骨架；截图补齐每一步。统一收口到 `.7z`/PDF。
- **选择理由**：报告门槛是首要失分风险（文档缺失=零分）；PyRIT 证据库 + 五段式是过报告关最稳组合。
- **适用场景**：24h 后 24h 报告窗口。

### ⑤ verify-evidence（D11 / P0）
- **推荐组合**：**PyRIT 证据五件套/三件套**（`collect_evidence.py` 严格门） + 手动双通道核验（控制面板 + 截图） + 报告模板一致性检查。
- **组合方式**：`--strict` 质量门校验证据完整性；对照考试 Point Disqualification（面板+截图双通道）逐项核验。
- **选择理由**：直接对应"面板+截图双通道缺失"即零分条款；PyRIT 证据工具链已建，复用即可。
- **适用场景**：提交前证据终检。

### ⑥ recon-ai（D2 / P0）
- **推荐组合**：**garak 首扫**（模型层探针） + Kali 侦察（nmap/burp/dirb） + 许可 AI 助手（目标画像/攻击面梳理）。
- **组合方式**：garak 先扫暴露的 LLM 端点定位薄弱点；Kali 做网络/服务 recon；AI 助手辅助解读与优先级排序。
- **选择理由**：garak 离线、内置检测器无需 judge，最适合"先扫一遍 AI 组件"；recon 阶段不需要深度利用框架。
- **适用场景**：考试开局 recon 环境、映射 AI 组件。

### ⑦ foothold-traditional（D1 / P0）
- **推荐组合**：**纯 Kali OSCP 工具链**（nmap/enum4linux/impacket/burp/SQLi 等） + 自定义 Py/Bash；**AI 框架零参与**。
- **组合方式**：标准渗透获取初始立足点、进入内网，作为两条攻击链入口。
- **选择理由**：传统向量 10 分/台且是链入口；AI 红队框架对 OSCP 级漏洞无覆盖，Kali 工具是正确答案。
- **适用场景**：链入口主机初始访问。

### ⑧ loot-manage（D1,D10 / P0）
- **推荐组合**：**结构化凭据库（脚本/笔记系统）** + 许可 AI 助手（去重/关联）；无攻击框架。
- **组合方式**：统一归集 hash/密钥/flag/AI 凭证，支撑横向移动与报告证据链。
- **选择理由**：运维型技能，框架无关；价值在"不漏证、不乱证"。
- **适用场景**：全程凭据与证据归集。

### ⑨ attack-embeddings（D6 / P1）
- **推荐组合**：**vec2text**（embedding inversion，LLM08 敏感泄露实证） + PyRIT（编排/证据） + 自定义脚本（相似度探测/越权）。
- **组合方式**：vec2text 从向量反演原文；PyRIT 留证。
- **选择理由**：Emb 是 AI 场景；vec2text 是该面权威工具，PyRIT 补编排与证据。
- **适用场景**：向量库/embedding store 主机。

### ⑩ attack-multi-agent（D4 / P1）
- **推荐组合**：**A2ASecBench**（协议感知基准，ICLR'26） + Cisco a2a-scanner（Agent Card 分析） + PyRIT HTTPTarget（打 A2A 端点多轮） + A2A Python SDK/samples（演练目标基座与 recon）。
- **组合方式**：a2a-scanner 扫恶意 Agent Card；A2ASecBench 六类攻击可插拔 SUT；PyRIT 打端点。
- **选择理由**：MA 是 AI 场景；PyRIT 无原生 MA 策略，靠 A2ASecBench + 专项；A2A SDK 做协议 recon。
- **适用场景**：multi-agent 平台（A2A 协议）主机。

### ⑪ attack-supply-chain（D8 / P1）
- **推荐组合**：**ModelScan**（模型/pickle 恶意代码检测） + **IBM ART**（投毒/提取/规避全谱） + PyRIT（编排/证据） + 自定义脚本（依赖/命名空间抢注）。
- **组合方式**：ModelScan 扫模型文件；ART 做投毒/提取攻击；PyRIT 留证。
- **选择理由**：SC 是 AI 场景；ModelScan/ART 是该面权威，PyRIT 补证据。
- **适用场景**：模型仓库/依赖供应链主机。

### ⑫ attack-infra（D9 / P1）
- **推荐组合**：**Kali + 云 CLI**（aws/az/gcloud） + MS AIRT Playground Labs（12 级渐进挑战，补 Infra/Cloud 手法） + 自定义脚本；AI 红队框架基本缺席。
- **组合方式**：标准云/IaC/容器/K8s 攻击；MS AIRT 练手；PyRIT 仅打可达 AI 端点。
- **选择理由**：Infra/Cloud 框架普遍无覆盖，靠 OSCP 级云安全 + 微软靶场；这是考试"企业落地"半壁江山。
- **适用场景**：AI 编排框架/云侧主机。

### ⑬ threat-model（D10 / P1）
- **推荐组合**：**方法论**（MITRE ATLAS / OWASP LLM Top10 / OWASP Agentic Top10） + 文档/图表 + 许可 AI 助手（结构化梳理）；无专用框架，框架是被建模对象。
- **组合方式**：对目标建威胁模型，指引用哪层框架、先打哪类。
- **选择理由**：威胁建模是分析活动，框架是输入而非工具。
- **适用场景**：每目标利用前的规划阶段。

### ⑭ decoy-detect（D2 / P1）
- **推荐组合**：**纯 Kali/网络侦察 + 人工判定 + 许可 AI 助手**（行为分析）；无 AI 攻击框架。
- **组合方式**：快速识别 2 台"故意不脆弱"主机，避免浪费时间在零分机上。
- **选择理由**：纯识别任务，靠侦察与经验；AI 框架无用。
- **适用场景**：环境开局快速区分计分机与诱饵机。

### ⑮ capstone-rehearse（D11 / P2）
- **推荐组合**：**全栈串联**：garak(首扫) → PyRIT(深) + promptfoo(固) + 专项点解 + Kali(落地) + 许可 AI 助手；即决策文档分层栈整体演练。
- **组合方式**：综合演练把各 skill 串成端到端攻击链，验证框架协同。
- **选择理由**：capstone 是综合，需要全部框架协同。
- **适用场景**：考前综合演练。

### ⑯ tooling-automate（D11 / P2）
- **推荐组合**：**自定义脚本**统一编排上述各框架 CLI + CI 集成（promptfoo CI / PyRIT 批处理） + 许可 AI 助手（脚本生成）。
- **组合方式**：把 garak/promptfoo/PyRIT/Kali 串成可复跑流水线，批量收集证据。
- **选择理由**：自动化是效率杠杆，但建立在各框架之上。
- **适用场景**：复跑攻击、批量证据收集。

### ⑰ attack-jailbreak（P3 新增 / P1）
- **推荐组合**：**PyRIT(v1.1.0) 多轮策略内核**（RedTeamingAttack / CrescendoAttack / PAIRAttack / TreeOfAttacksWithPruningAttack）+ 转换器 + 分级评分（SubStringScorer 优先）+ 自定义。
- **组合方式**：单一真实 seam 承载 PyRIT 调用，测试替身保持零依赖；证据复用 `collect_evidence.py`。
- **选择理由**：越狱是 AI 主分面护栏绕过核心手段，PyRIT 多轮编排无可替代；一手源核实见 `attack-jailbreak-multimodal-canonical.md` M7。
- **适用场景**：仅启用护栏加固、需系统性越狱的 AI 向量机。

### ⑱ attack-multimodal（P3 新增 / P1）
- **推荐组合**：**PyRIT(v1.1.0) 多模态 target**（OpenAIChatTarget 图像输入 / PlaywrightTarget image_path / HTTPXAPITarget 文件上传）+ 转换器 + 复用 attack-rag 的 multimodal_camouflage 原语。
- **组合方式**：与 jailbreak 同构 seam；target 层用 1.1.0 已核实多模态类（M2/M5/M6）。
- **选择理由**：跨模态注入是 AI 主分面；1.1.0 一手源已核实多模态 target（M1–M6），无需 1.2.x。
- **适用场景**：图像上传/OCR/PDF 文件输入的跨模态注入场景。

---

## 3. 跨技能共性结论

1. **PyRIT 是内核但非万能**：仅在 LLM/Agt/RAG/Emb/SC/Rep（①②③⑨⑪④⑤）做主角；在 MCP(②)、MA(⑩)、Infra(⑫) 仅做深度补位或完全缺席。
2. **MCP 与 MA 必须外挂**：promptfoo(MCP) + mcp-scan/agentic-radar、A2ASecBench + a2a-scanner 是这两类的正确主控，PyRIT 经 `HTTPTarget` 回调接入。
3. **传统/云/DC 与 AI 框架无关**：⑦⑫⑭ 及链内横向完全靠 Kali 工具链 + 自定义脚本；这是考试"企业落地"半壁江山，AI 工具零贡献。
4. **报告与证据是独立的一层**：④⑤ 用 PyRIT 证据库 + 五段式模板统一收口，是降低"零分风险"的关键，优先级与攻击 skill 同等（P0）。
5. **promptfoo 须自托管**：其联网生成/评分插件现属 OpenAI，考试内网存在数据外发与可用性风险，落地前须实测自托管 provider 并禁用联网插件，否则内网改用 garak+PyRIT+自定义。

---

## 4. 参考源

- 框架决策：`docs/research/osai-ai300-framework-decision.md`
- 考试事实：S3 快照 `docs/governance/references/OSAI-Exam-Guide-snapshot.md`
- PyRIT 规范：`docs/research/pyrit-canonical-references.md`、`pyrit-v110-api-verification.md`
- 工具精选源文档：`D:\下载\osai-ai300-skill-coverage-decision.md`（仓库外外部依赖，未入库；异机复核须先取得该源）
- 技能元数据：`skills/*/SKILL.md`（priority / domain 字段）
