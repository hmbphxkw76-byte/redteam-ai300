# PentAGI × OSAI AI-300 技能迁移清单

> **性质**：研究/评估清单（非规范正文），仅作迁移决策输入，不构成 GOVERNANCE 条款或验收条件。核验日期 2026-11-24（GMT+8）。
> **一手源**：本地只读 `D:\下载\pentagi-main`（`vxcontrol/pentagi` 快照，Go 1.26.5 / 761 Go 文件）；本仓库 `AGENTS.md`、`docs/research/osai-skill-framework-matrix.md`、`docs/research/osai-ai300-framework-decision.md`、`skills/*/SKILL.md`。
> **范围**：本仓库已落地技能 + PentAGI 一手源码可提取能力/方法论合并清单；术语以 `GLOSSARY.md` 为准。不修改技能实现，不建分支或 PR。

---

## 1. 判定标准

### 1.1 掌握程度（三档）

| 档位 | 定义 | 判据 |
|---|---|---|
| 已落地并验证 | 本仓库存在对应实现，且有门禁记录/测试/PR 合并证据 | 可指向 `skills/<name>/` 或 `tools/<name>/` + G0 记录 |
| 部分落地 | 有 partial 实现、PoC 或设计文档，未过全量门禁 | 可指向 `docs/operations/*design.md` 或未收口模块 |
| 仅设计或概念 | 一手源核实了上游设计，但本仓库无实现；或上游自身标注 Beta / 未来工作 | 仅有 PentAGI 路径锚点 |

### 1.2 迁移类别（A/B/C）

| 类别 | 定义 | 成本特征 |
|---|---|---|
| **A** 直接复用 | 无需额外学习，沿用既有 seam / 提示词约定，不引入新服务 | 零新依赖、零新栈 |
| **B** 少量调整复用 | 需映射到本仓库既有接口（11 阶段门禁、S-1 入口、评分器） | 仅改接线与判据 |
| **C** 重新学习适配 | 需引入新语言栈/外部服务/运维能力，与离线窗口有张力 | Go、Graph+DB、可观测栈、容器 |

---

## 2. 合并技能清单

### 2.1 A 类：无需额外学习即可直接复用

| 编号 | 能力/技能 | 类别 | 掌握程度 | 应用场景（OSAI） | 来源锚点 | 判定理由 |
|---|---|---|---|---|---|---|
| A-01 | 11 阶段主线流程与逐阶段 G0 门禁 | 流程方法论 | 已落地并验证 | 每个技能的落地与收口，防跳步 | `docs/operations/skill-mainline-workflow.md` | 本仓库唯一可信源，直接复用 |
| A-02 | to-spec 两遍（v1/v2）独立留痕 | 流程方法论 | 已落地并验证 | 新技能规格定稿 | 同上 §2 | 已是硬约束，无需学习 |
| A-03 | 证据三/五件套与 flag 双通道 | 证据契约 | 已落地并验证 | 报告关（文档缺失即零分风险） | `scripts/collect_evidence.py`、`skills/verify-evidence/` | `report-exam` 既有契约，直接复用 |
| A-04 | 五段式主机报告结构 | 报告方法论 | 已落地并验证 | 每台计分主机报告 | `skills/report-exam/`、`GLOSSARY.md` 五段式 | 已对齐 S1 §7.2 |
| A-05 | PyRIT 深度内核（多轮编排+证据） | 攻击框架 | 已落地并验证 | AI 向量主机主分面 | `tools/attack_ai_agent/`、`docs/research/pyrit-canonical-references.md` | 规范内核已建成，含版本适配框架 `tools/pyrit_compat/` |
| A-06 | 框架分层组合方法论（首扫→深度→固化→点解→落地） | 技术选型方法论 | 已落地并验证 | 开局到报告的全栈选型 | `docs/research/osai-ai300-framework-decision.md` §4 | 决策已固化，直接复用 |
| A-07 | 令牌预算纪律 C1–C8 | 工程方法论 | 已落地并验证 | 长流程编排压缩、CI 门禁 | `AGENTS.md` C1–C8、`scripts/check_token_budget.py` | 已是全项目强制条款 |
| A-08 | 三层隔离与 worktree 纪律 | 工程方法论 | 已落地并验证 | 并行技能落地不互相污染 | `docs/governance/adr/0006-*.md`、`scripts/checkout_lock.py` | 已验证的多会话隔离方案 |
| A-09 | 执行监控阈值判据（同工具 5 次 / 总 10 次触发教练介入） | 运行时监督 | 仅设计或概念 | 24 小时窗口内防死循环 | `backend/pkg/config/config.go:311-313`、`backend/pkg/providers/helpers.go:164-197` | 纯阈值判据，可用既有 S-1 入口实现，无需新依赖 |
| A-10 | 规划器 3–7 步清单 + 任务包装结构 | 提示词方法论 | 仅设计或概念 | 复杂链的多步任务分解 | `templates/prompts/question_task_planner.tmpl`、`task_assignment_wrapper.tmpl` | 提示词模板级，可直接落入既有 prompt 体系 |
| A-11 | 反思器三振纠错（连续 3 次未生成工具调用即介入） | 运行时监督 | 仅设计或概念 | 小模型/复杂场景卡死恢复 | `backend/pkg/providers/performer.go:162-189` | 判据与 G0 `BLOCKED` 重跑语义同构 |
| A-12 | 工具调用硬上限分级（通用 100 / 受限于 20） | 运行时护栏 | 仅设计或概念 | 防资源耗尽、防跑飞 | `backend/pkg/config/config.go:316-317`、`performer.go:124-136` | 计数与优雅终止为通用逻辑 |
| A-13 | 记忆写入匿名化规则（IP/域名/凭据/令牌换占位符） | 数据安全 | 仅设计或概念 | 跨会话经验沉淀不外泄目标标识 | `templates/prompts/pentester.tmpl:56-66`、`backend/pkg/tools/code.go:236-392` | 占位符规则集可直接复用，不涉及新栈 |
| A-14 | 双通道语言策略（交互日志本地语言 / 技术通道英文） | 提示词方法论 | 仅设计或概念 | 中文报告 + 英文命令/PoC 一致性 | `templates/prompts/pentester.tmpl:15-45` | 纯提示词约定，无需新工具 |
| A-15 | 报告独立复核判据（对照原始需求逐项判定达成度） | 复核方法论 | 部分落地 | 提交前终检，对齐 `verify-evidence` | `templates/prompts/reporter.tmpl`、`backend/pkg/providers/performers.go:22-94` | 与既有严格门互补，可并入终检清单 |
| A-16 | 摘要上下文标记协议（摘要只作历史、禁止模仿其格式） | 上下文方法论 | 部分落地 | 长会话压缩，对齐 C1/C2 | `templates/prompts/primary_agent.tmpl:161-193`、`full_execution_context.tmpl` | 约定级，直接纳入 C2 增量门禁 |
| A-17 | 终止/提问栅栏工具语义 | 护栏语义 | 已落地并验证 | 攻击链收口与人工确认点 | `backend/pkg/tools/registry.go:12-13`、`performer.go:247-253` | 与 flag 双通道/人工确认点同构 |

### 2.2 B 类：仅需少量调整即可复用

| 编号 | 能力/技能 | 类别 | 掌握程度 | 应用场景（OSAI） | 来源锚点 | 调整点与判定理由 |
|---|---|---|---|---|---|---|
| B-01 | 任务自动分解 + 增量精化（add/remove/modify/reorder） | 编排机制 | 仅设计或概念 | 链内主机任务动态重排 | `controller/task.go:102,341-378`、`backend/pkg/tools/args.go:70-95`、`performers.go:189` | 需把 delta 操作映射到 G0 门禁的"停留原阶段重跑"语义 |
| B-02 | 人在环控制工具（状态查询/停止/提交输入/改任务/等待） | 交互控制 | 仅设计或概念 | 考试中途人工纠偏、范围澄清 | `backend/pkg/tools/flow_manager.go:43,534,613,686,829` | 接 S-1 统一入口（`tooling-automate`），复用 CommandRunner 可注入 seam |
| B-03 | 类型化工具注册 + 按角色工具集 + 工具类型映射 | 工具治理 | 部分落地 | 限定每阶段可用工具面 | `backend/pkg/tools/registry.go:11,56-130`、`tools.go:874-1129` | 本仓库已有 S-1 单 seam，补类型标注即可；不改并发共用长行 |
| B-04 | 调用链 AST + 上下文压缩（摘要/窗口紧凑化） | 上下文管理 | 部分落地 | 长攻击链降 token，对齐 C1–C8 | `backend/pkg/cast/chain_ast.go:39-66,103-156`、`providers/window_compaction.go` | 与令牌预算检查器对接，须保证据三/五件套不丢 |
| B-05 | 跨模型工具调用 ID 归一化 + 参数自动修复 | 兼容性工程 | 部分落地 | 双模型凭据下工具调用稳定 | `backend/pkg/cast/chain_ast.go:909-1031`、`performer.go:355-395` | 与 `tools/pyrit_compat/` 适配器注册表规则同构，可并入 |
| B-06 | 确定性/瞬时错误分类与差异化重试 | 恢复机制 | 仅设计或概念 | 避免对确定性失败重复消耗 | `backend/pkg/providers/retry.go:20-93` | 映射为 C6 `--step` 单步复现的判定前置 |
| B-07 | 图谱本体分类法（主机/端口/服务/漏洞/凭据/证据等） | 知识建模 | 部分落地 | 资产-ID 身份链、威胁建模 | `templates/prompts/pentester.tmpl:76-110`、`backend/pkg/graphiti/` | 与 `threat-model` 资产-ID 身份链衔接；仅取分类法，不取图数据库 |
| B-08 | 多引擎检索 + exploit-mode 检索查询 | 情报能力 | 部分落地 | 开局组件识别、公开 PoC 定位 | `backend/pkg/tools/searchers/`、`web_search.go` | 考试内网窗口，须限本地/离线；禁用外发插件（对齐既有决策） |
| B-09 | 报告 web/Markdown/PDF 导出 | 报告工程 | 已落地并验证 | 24 小时后报告窗口 | `examples/reports/*.md,*.pdf`、`skills/report-exam/` | 本仓库 pandoc 3.14 须 `--pdf-engine=typst`，接既有管线即可 |
| B-10 | 提示词用户覆盖机制（模板 overlay） | 可配置性 | 仅设计或概念 | 按主机类型切换提示词 | `backend/pkg/controller/prompter.go`、`templates/templates.go:31-69` | 映射为 `skills/*/` 的模板变量，不改证据契约 |
| B-11 | 结果摘要白名单与记忆写入白名单 | 记忆治理 | 仅设计或概念 | 控制哪些工具结果可沉淀 | `backend/pkg/tools/registry.go` 中 `allowedSummarizingToolsResult` / `allowedStoringInMemoryTools` | 与 A-13 匿名化配套，复用既有脚本登记契约 |

### 2.3 C 类：需要重新学习适配

| 编号 | 能力/技能 | 类别 | 掌握程度 | 应用场景（OSAI） | 来源锚点 | 重新学习的必要性 |
|---|---|---|---|---|---|---|
| C-01 | Docker 沙箱隔离（能力裁剪、PID 上限、启动探针） | 基础设施 | 仅设计或概念 | 隔离执行高危命令 | `backend/pkg/docker/sandbox.go`、`client.go:375`、`worker_spec.go` | Go + moby 栈；考试用本地 Kali 接入，沙箱 daemon 非考试路径 |
| C-02 | Graphiti + Neo4j 时序知识图谱 | 知识设施 | 仅设计或概念 | 跨步骤关系追踪 | `backend/pkg/graphiti/`、`docker-compose-graphiti.yml` | 需新图数据库运维；与 24 小时离线窗口张力大 |
| C-03 | LLM 全链路可观测（Langfuse traces/spans/agents） | 可观测设施 | 仅设计或概念 | 调用审计与质量分析 | `backend/pkg/observability/langfuse/`、`docker-compose-langfuse.yml` | 需自托管服务 + ClickHouse/Redis/MinIO；非考试必需 |
| C-04 | 系统可观测（OTel/Grafana/Jaeger/Loki） | 可观测设施 | 仅设计或概念 | 平台运行监控 | `docker-compose-observability.yml`、`observability/` | 运维栈与考试目标无关 |
| C-05 | 多 provider 抽象（13 类云/本地模型） | 平台能力 | 仅设计或概念 | 模型可替换 | `backend/pkg/providers/{openai,anthropic,bedrock,ollama,...}/` | 本仓库双模型凭据已满足；扩展收益低、适配成本高 |
| C-06 | React 前端 + GraphQL/订阅 + REST 全套 API | 平台能力 | 仅设计或概念 | 平台化界面与自动化接口 | `frontend/src/`、`backend/pkg/graph/`、`backend/pkg/server/` | 与技能交付形态（CLI/脚本 + 报告）不匹配 |
| C-07 | 智能容器镜像选择 / 20+ 工具预置 | 平台能力 | 仅设计或概念 | 自动匹配工具镜像 | `README.md:63-95`、`backend/pkg/docker/` | 考试工具链固定为 Kali 本地工具，镜像自动选择不适用 |
| C-08 | 攻击剧本式 BAS / 对手模拟 | 概念（上游未实现） | 仅设计或概念 | 预定义攻击计划 | `README.md:95-97` 明确列为"非当前功能、未来工作" | 上游自己标注未实现，不可作为可借鉴能力；且 AI-300 不考预定义剧本 |

---

## 3. PentAGI 新增能力对照（本仓库无直接对应项）

| 能力 | PentAGI 锚点 | 本仓库最近似项 | 差距性质 | 是否建议引入 |
|---|---|---|---|---|
| 多智能体运行时监督（教练/规划/反思） | `providers/performer.go:99-514`、`performers.go:825-968` | `attack-multi-agent` 不含运行时监督 | 方法论缺口 | 引入 A-09～A-12 判据，不引入 Go 实现 |
| 任务增量精化 | `controller/task.go:341-378` | 11 阶段顺序固定、不跳不并 | 取向不同 | 仅阶段内受控重排 |
| 人在环 flow 控制 | `tools/flow_manager.go` | 人工确认点/flag 双通道 | 接口缺口 | 按 B-02 接入 S-1 |
| 时序知识图谱 | `backend/pkg/graphiti/`、`pentester.tmpl:76-110` | `threat-model` 资产-ID 身份链 | 设施缺口 | 只取本体分类法（B-07） |
| 全链路 LLM 可观测 | `backend/pkg/observability/langfuse/` | 证据片段 + 门禁记录 | 设施缺口 | 不引入（C-03） |
| 跨模型工具调用容错 | `cast/chain_ast.go:909-1031` | `tools/pyrit_compat/` 版本适配 | 可合并 | 按 B-05 并入注册表 |
| 多引擎外部检索 | `tools/searchers/`、`web_search.go` | `recon-ai` 首扫 + 本地工具 | 离线约束 | 受限引入（B-08，禁外发） |
| 会话级文件隔离 | `README.md` 登录后用法 §5 | worktree 隔离 | 粒度不同 | 不引入（C-06） |

反向差距（本仓库有、PentAGI 无）：证据契约与 flag 双通道、五段式报告、11 阶段门禁、令牌预算、AI 攻击技能族（agent/MCP/A2A/embedding/供应链/多模态）、框架矩阵。均为 AI-300 得分主面，迁移方向应为"本仓库 → 新项目"。

---

## 4. 对 OSAI AI-300 技能覆盖的增强分析

| 考试维度 | 现状 | PentAGI 可补强点 | 净效果 |
|---|---|---|---|
| AI 向量主机（主分面） | 已有 agent/RAG/MCP/A2A/embedding/供应链技能族 | 仅补运行时护栏，不补攻击深度 | 边际提升，非替代 |
| 传统向量 / 链入口 | `foothold-traditional` + Kali 已覆盖 | 多引擎检索加速组件识别（受离线约束） | 小幅提效 |
| 报告关（缺失即零分风险） | 证据片段 + 五段式 + 严格门已覆盖 | 独立复核（A-15）、双通道语言（A-14） | 提升稳定性 |
| 全局效率 / 24 小时窗口 | C1–C8 + S-1 入口 | 上下文压缩（B-04）、错误分类（B-06）、人在环（B-02） | 明确提升 |
| 域控 / 诱饵机 | 已有对应技能与判定清单 | 无实质补强 | 无变化 |

**结论**：价值集中在**编排与韧性**（运行时监督、上下文管理、人在环、复核判据），非 AI 攻击能力本身；上游边界（非 BAS、无预定义攻击计划、无 JSON 导出）进一步限制借鉴范围。不得削弱 AI 向量主分面投入。

---

## 5. 优先级建议

1. **P0**：A-09～A-17 判据级复用（监控阈值、规划、反思、硬上限、匿名化、双通道语言、复核、摘要标记、终止栅栏）；全为约定，无新服务。
2. **P1**：B-01、B-02、B-03、B-05、B-06、B-11（任务精化、人在环、工具类型化、调用容错、错误分类、沉淀白名单）；接既有 seam。
3. **P2**：B-04、B-07、B-08、B-09、B-10（上下文压缩、本体分类、受限检索、报告导出、模板覆盖）；须先过 C1–C8 与证据契约回归。
4. **不引入**：C-01～C-08（新栈/外部服务/上游未实现）；上游"预授权、绝不请求确认"原句与考试范围冲突，不得照搬。

---

## 6. 迁移风险与边界

- **令牌开销**：上游监督机制自述 2–3 倍时间与 token，与 C4/C6 冲突；只取判据，不启用全量调用，以 `--step` 复现。
- **证据契约**：B-04/A-16 改动须先过 `check_evidence_contract.py` 与 `report_exam.index.parse_fragment` 回归，flag 段保留原值块。
- **提示词隔离**：上游"全授权、永不请求确认"仅适用其自有框架；范围规则由 S1 快照定义，不得照搬，仅复用结构。
- **离线约束**：Langfuse、Graphiti、外部检索需网络；考试为 Tailscale VPN + 本地 Kali，B-08 须禁外发插件。
- **上游边界**：`README.md:95-97` 明确非 BAS、无 JSON 导出、攻击剧本属未来工作；"借鉴攻击剧本"不成立。
- **术语门禁**：已按 `GLOSSARY.md` 规避废弃术语；追加内容须复跑 `check_glossary.py` 与 markdownlint。
