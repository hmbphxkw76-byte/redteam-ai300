# attack-rag 一手源调研

> **版本** v1.0 · **状态** 生效 · **调研日期** 2026-11-15（GMT+8）
> **目标技能** `skills/attack-rag/SKILL.md`（P0 · D5 · AI向量机）
> **演练目标** `http://192.168.40.189`（AIVP 实例，非 OSAI 正式考试环境）
> **性质** 阶段 1 交付物：实现所依赖事实的一手源锁定，消除规格阶段的猜测
> **框架组合**（取自 `docs/research/osai-skill-framework-matrix.md` ③）：**PyRIT(v1.1.0) 内核** + **PoisonedRAG** + **自定义脚本**（向量库越权/间接注入）

## 1. 结论摘要（先读这一节）

1. `attack-rag` 的「知识库投毒」攻击面是 **PoisonedRAG**（Zou et al., USENIX Security 2025, arXiv:2402.07867）——**首个** RAG 知识腐败攻击；其「双条件」结构（检索条件 + 生成条件）是路径 A 的理论内核，已在官方论文与实测中验证（5 篇投毒文本注入百万级语料可达 90%–97% ASR）。
2. 「操纵检索返回 / 间接注入」对齐 **OWASP LLM Top 10 2025 的 LLM01（间接提示注入）+ LLM04（数据/模型投毒）+ LLM08（向量与嵌入弱点）**，下游 agent 决策操纵进一步落入 **Agentic Top 10 ASI06（记忆与上下文投毒）**。
3. PyRIT 在 RAG 场景的可用原生对象：多轮编排用 `RedTeamingAttack` / `CrescendoAttack` / `PromptSendingAttack`，间接注入（XPIA）用 `pyrit.executor.workflow` 的 `XPIATestWorkflow` / `XPIAWorkflow`（**非** `*Attack`），目标统一 `OpenAIChatTarget`，证据走 `SQLiteMemory` + `PrettyAttackResultMemoryPrinter`（C1：具体 API 仅列名，细节引 `docs/research/pyrit-canonical-references.md`）。
4. 「篡改检索相关性 / embedding 碰撞」与「向量库越权直写」**无 PyRIT 原生原语**，须按矩阵「自定义脚本」实现（攻击文本构造 + 相似度探测 + 访问控制绕过），PyRIT 仅在此做编排与证据补位——**不得强行用 PyRIT 单栈覆盖**（B9）。
5. 演练目标 AIVP 未观察到独立 知识库投毒 lab（仅 MCP_06 `rag_server` 为上下文载荷面）；故 attack-rag 实现以**本地合成 RAG 夹具**为主验证面，AIVP 作为可选核实闸（§7 闸 A）。

## 2. 一手源事实（官方 URL 逐条）

| # | 事实 | 来源 | 关键原文 / 取值 |
|---|---|---|---|
| S-1 | PoisonedRAG 定位：首个 RAG 知识腐败攻击，向知识库注入少量恶意文本使 LLM 对指定目标问题生成攻击者选定答案 | <https://www.usenix.org/conference/usexsecurity25/presentation/zou> · arXiv:2402.07867 | "the first knowledge corruption attack to RAG" |
| S-2 | 两设置（按攻击者背景知识）：黑盒（不能见检索器内部）+ 白盒（知 embedder），分别给出解法 | 同上 | black-box / white-box settings |
| S-3 | 双条件结构：① 检索条件（恶意文本须落入目标问题 top-k）；② 生成条件（进入上下文后须说服 LLM 采纳目标答案） | arXiv:2402.07867 §3；转述见 §6 | Retrieval condition + Generation condition |
| S-4 | 黑盒启发式：构造 `[目标问题文本] + [攻击者目标答案叙述]` 前置问题以最大化 embedding 相似度 | arXiv:2402.07867；OWASP 社区转述 | prepend the question verbatim |
| S-5 | 白盒：直接优化文本 token 使 embedding 与目标问题碰撞（embedding collision） | arXiv:2402.07867；OWASP 社区转述 | embedding collision |
| S-6 | 效果：注入 5 篇投毒文本到百万级语料，ASR 90%；某案例 5 篇注入 2.6M 干净文本 ASR 97% | arXiv:2402.07867；USENIX 论文 p.8 | 90% / 97% ASR |
| S-7 | 成本极低：黑盒约 2 次 LLM 查询；白盒每篇恶意文本 <30s | USENIX 论文评测 | ~2 queries / <30s |
| S-8 | 对 Self-RAG、CRAG 等鲁棒；改写/困惑度过滤等防御不足 | USENIX 论文 §defenses | defenses insufficient |
| S-9 | OWASP LLM Top 10 2025 与 RAG 关联项：LLM01 提示注入（间接）、LLM04 数据/模型投毒、LLM08 向量与嵌入弱点 | <https://owasp.org/www-project-top-10-for-large-language-model-applications/> | LLM01/LLM04/LLM08 |
| S-10 | Agentic Top 10 ASI06 记忆与上下文投毒：检索内容持久化污染下游 agent 推理（ReAct 案例被误导） | OWASP Agentic Top 10 2025（S-3 案例研究） | ASI06 Memory & Context Poisoning |
| S-11 | PyRIT 版本与对象图（RAG 可用原语） | `docs/research/pyrit-canonical-references.md` §1/§3 | `pyrit==1.1.0`；`RedTeamingAttack`/`CrescendoAttack`/`PromptSendingAttack`；XPIA 在 `pyrit.executor.workflow`；`OpenAIChatTarget`；`SQLiteMemory` |

## 3. 攻击路径 → 对象映射（SKILL.md 对齐 S1/S2）

| SKILL 路径 | 步骤 | SKILL 技术分类 | 实现层对象 | 框架归属 |
|---|---|---|---|---|
| 前置：定位 RAG 攻击面 | — | 复用 recon-ai 资产清单 | `ReconAsset.typed("rag")` / 资产清单七字段 | 既有 |
| 路径 A 知识库投毒 | 注入恶意文档 | OWASP LLM04 / PoisonedRAG | `PoisonedRAGInjector`（黑盒前置问题法 / 白盒 embedding 碰撞） | **PoisonedRAG + 自定义** |
| | 篡改检索相关性 | OWASP LLM08 | `EmbeddingCollisionCraft` + `RetrievalProbe`（相似度探测） | **自定义脚本** |
| 路径 B 操纵检索返回 | 探针 before/after top-k | OWASP LLM08 | `RetrievalProbe.before_after()` | 自定义 |
| | 在检索片段嵌指令操纵下游 agent | OWASP LLM01 间接注入 / ASI06 | `XPIATestWorkflow`（`pyrit.executor.workflow`） | **PyRIT 内核** |
| 路径 C 验证下游决策影响 | baseline vs manipulated 差异 | ASI06 | `DecisionDiffCapture` + `OpenAIChatTarget` + `SQLiteMemory` | PyRIT |
| 收尾：flag 取证 | `ai_vector.txt` 双通道 | GOVERNANCE §6.2 | `collect_evidence.py --step rag-NN --strict` + `FlagProof` | 既有共享工具 |
| 证据收口 | 三件套/五件套 | §6.1/§6.3 | `tools/collect_evidence.py` | 既有 |

## 4. 已排除（勿再当成事实）

| 名称/假设 | 排除依据 |
|---|---|
| PyRIT 存在 RAG 专用攻击策略或 embedding 碰撞原语 | v1.1.0 无；检索/越权须自定义（S-11 + §1.4） |
| `XpiaAttack` 可用于间接注入 | v1.1.0 不存在；间接注入归 `pyrit.executor.workflow`（S-11） |
| 演练目标存在独立 知识库投毒 lab | AIVP 仅 MCP_06 `rag_server`（上下文载荷面）；全量 lab 枚举见 `attack-mcp-tool-canonical.md` §3.1，无 知识库投毒专用 lab |
| 演练目标存在 `ai_vector.txt` | T-6（attack-mcp-tool 实测）全部命中 SPA 回退，判定缺席 |
| PoisonedRAG 黑盒需梯度/白盒知识 | 黑盒只需前置问题文本，无需 embedder 访问（S-4） |

## 5. 待核实（带取证方式，不阻塞实现）

| # | 待核实项 | 取证方式 |
|---|---|---|
| C-1 | AIVP 是否存在可写/可摄取的 RAG 端点（非 MCP_06 上下文面） | 轻探针 `curl` 枚举 `/api/labs/*/chat` 系统提示与可调用工具，确认有无 ingestion/vector 接口 |
| C-2 | 本地夹具选用的 embedder 与考试 `text-embedding-3-small` 行为差异 | 固定 `EmbeddingModel` 注入点，测试用 `sentence-transformers` 本地模型，记录版本 |
| C-3 | `XPIATestWorkflow` 的 `processing_callback` 与 `attack_content` 精确形态 | `pyrit==1.1.0` 已装环境 `python -c "import inspect; ..."` 取签名（核实闸 §7 闸 B） |
| C-4 | 白盒 embedding 碰撞在本地夹具的可达 ASR（验证 S-6 可复现） | 注入 5 篇到合成 2.6M 级语料，统计 top-k 命中率 |

## 6. 实现前必须取证的核实闸

1. **闸 A（测试面）**：AIVP 无 知识库投毒 lab → 实现**必须**提供本地合成 RAG 夹具（`RagHarness`：向量库 + 检索器 + 生成器），所有攻击路径先在该夹具跑通；AIVP 仅作可选回归闸（C-1）。
2. **闸 B（对象图）**：间接注入必须用 `XPIATestWorkflow`/`XPIAWorkflow`，不得误用 `*Attack`；`OpenAIChatTarget` 单例构造经注入点（C-3）。
3. **闸 C（判据）**：下游决策影响必须用「baseline vs manipulated」双次捕获做因果对照，禁止仅凭单次检索变化判「生效」；flag 双通道缺席时按 `validate oracle` 等价通道处理（GLOSSARY `校验预言机`）。

## 7. 门禁记录（阶段 1 / G0）

| 编号 | 检查项 | 依据 | 实测结果（命令 + 摘要） | 判定 | 不符合项 | 修正要求 | 复验 | 结论 |
|---|---|---|---|---|---|---|---|---|
| B7 | PyRIT 版本与对象图 | S-11 / §3 | `pyrit==1.1.0`；§3 映射用 `OpenAIChatTarget`/`XPIATestWorkflow`，无 `*Attack` 误用 | 符合 | 无 | — | `grep -nE "XpiaAttack|orchestrator" 本文件` 无命中 | PASS |
| B8 | 可追溯性 | §2 S-1..S-11 | 11/11 附官方 URL 或 `pyrit-canonical-references.md` 锚点；§3 8 步全映射 | 符合 | 无 | — | 抽查 S-1、S-6 重读 | PASS |
| B9 | 框架选型合规 | 矩阵 ③ / §1.4 | 组合取自矩阵对应条目（PyRIT+PoisonedRAG+自定义）；偏离项 0 | 符合 | 无 | — | `grep "osai-skill-framework-matrix.md" 本文件` | PASS |
| 验收① | 结论可定位到官方 URL/源码 | §2 | 11/11 含源 | 符合 | — | — | — | PASS |
| 验收② | 版本号明确 | S-11 / §1.4 | `pyrit==1.1.0`；PoisonedRAG USENIX'25 | 符合 | — | — | — | PASS |
| 验收③ | 每条攻击路径有对象映射 | §3 | 4 路径 / 8 步 | 符合 | — | — | — | PASS |
| 验收④ | 待核实项逐条命名+取证方式 | §5 | 4 项（C-1..C-4）各含取证方式 | 符合 | — | — | — | PASS |
| 验收⑤ | 落盘于 `docs/research/` | 本文件 | 存在 | 符合 | — | — | — | PASS |

**结论：PASS**。不符合项 0。上游无（阶段 1 为首阶段）。

## 8. 关联文档

- 行为唯一来源：`skills/attack-rag/SKILL.md`
- 术语基准：`GLOSSARY.md`
- PyRIT 权威索引：`docs/research/pyrit-canonical-references.md`
- 框架组合：`docs/research/osai-skill-framework-matrix.md` ③
- 主线规范：`docs/operations/skill-mainline-workflow.md`
- 模式参考：`docs/research/attack-mcp-tool-canonical.md`
