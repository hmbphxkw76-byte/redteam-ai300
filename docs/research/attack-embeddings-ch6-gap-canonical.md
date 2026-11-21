# OffSec AI-300 Ch6「Attacking Embeddings」差距调研（一手源锁定）

> **版本** v1.0 · **状态** 生效 · **调研日期** 2026-11-21（GMT+8）
> **目标技能** `skills/attack-embeddings/SKILL.md`（P1 · D6 · AI向量机）
> **课程事实源** `D:\视频\OffSec   AI-300 Advanced AI Red Teaming\Ch6-Attacking-Embeddings.html`（115MB / 47 正文块；§6.1–§6.5 + Listing/Table/Figure 编号可定位）
> **性质** 主线阶段 1 交付物：把《文档 vs 项目对照分析》的差距映射到一手源，消除规格阶段的猜测
> **框架组合**（矩阵 ⑨，强制）：vec2text（embedding inversion）+ PyRIT(v1.1.0)（编排/证据）+ 自定义脚本（探测/越权/triage/填槽）
> **冲突优先级**：官方考试事实 > GOVERNANCE「必须」> CI-CD > 主线规范 > 历史映射 > 技能局部约定 > 课程教材

## 1. 结论摘要

1. 课程 Ch6 的核心是**向量数据库反演**：把 embedding 当作非单向函数，通过语义保持特性还原明文口令/密钥。项目现有实现（emb-01..08）只覆盖「定位/探测/近似反演/成员推断/对抗/反查/下游影响/flag」，**未覆盖** Ch6 的侦察三件套（导出、模型识别、块分选）、填槽式反演、beam search、ALGEN/canary、Vec2Text、决策矩阵与限制前置判定。
2. 三篇核心论文一手源全部核实：Vec2Text（EMNLP'23，92%/32-token exact-match）、ALGEN（ACL 2025 long，1k 样本最优、单样本部分成功、防御均无效）、Zero2Text（arXiv:2602.01757v2，training-free，recursive online alignment + ridge regression）。
3. **教材与论文的差异须显式记录**（避免把课程适配当成论文事实）：ALGEN 的「canary 注入 + token 32→64 + RAG probing 集成」是课程适配，论文原始只用 cross-model alignment + 生成；Vec2Text 的「企业域语料 + recon-guided + 单 T4」是课程适配，原论文用百万指令 + 多 GPU。
4. AIVP 无独立 embedding 反演 lab（`attack-embeddings-canonical.md` §1.6/§4，已核实），项目以本地合成夹具为主验证面属**既有设计决策**，不判为缺陷；ALGEN/Vec2Text 等需要真实目标/大 GPU 的能力标为「环境相关，待 C-1 取证」，不阻塞 P0 实现。

## 2. 一手源事实（逐条 URL / 版本）

| # | 事实 | 来源（一手） | 关键原文 / 取值 | 核实状态 |
|---|---|---|---|---|
| S-1 | Vec2Text =《Text Embeddings Reveal (Almost) As Much As Text》，EMNLP 2023；多步迭代纠错重嵌入可精确还原 92% 的 32-token 输入；可恢复临床笔记全名 | arXiv:2310.06816 · <https://arxiv.org/abs/2310.06816> · GitHub `jxmorris12/vec2text` | "recover 92% of 32-token text inputs exactly"；"Accepted at EMNLP 2023" | ✅ 2026-11-21 实读 abstract |
| S-2 | ALGEN =《ALGEN: Few-shot Inversion Attacks on Textual Embeddings via Cross-Model Alignment and Generation》，Chen/Xu/Bjerva，ACL 2025 Long（Vienna），pages 24330–24348 | ACL Anthology 2025.acl-long.1185 · <https://aclanthology.org/2025.acl-long.1185/> · DOI 10.18653/v1/2025.acl-long.1185 | "single data point is sufficient for a partially successful inversion"；"as little as 1k data samples, performance reaches an optimum"；"none [defenses] are effective" | ✅ 2026-11-21 实读 abstract+PDF 首页 |
| S-3 | Zero2Text =《Zero2Text: Zero-Training Cross-Domain Inversion Attacks on Textual Embeddings》，Kim et al.，2026-02-02 submitted / 02-03 v2 | arXiv:2602.01757v2 · <https://arxiv.org/abs/2602.01757> | "training-free framework based on recursive online alignment"；"LLM priors with a dynamic ridge regression mechanism"；"differential privacy fail to effectively mitigate" | ✅ 2026-11-21 实读 abstract |
| S-4 | 课程 §6.2 侦察三件套：导出向量（Weaviate GraphQL cursor 分页 → .npy/.csv/.parquet）、维度指纹（384/768/1536/3072）、inference probing（top5_avg≥0.85 判命中，0.5–0.6 为错模型） | 课程 Ch6 Listing 1–8 | "GraphQL cursor-based pagination"；"correct model ... typically 0.85 or higher" | ✅ 课程 HTML 提取文本 |
| S-5 | chunk triage 三级：Density→Contrastive Pairwise→Reconstruction，加权 RRF（density 1.0/PW 1.5/recon 2.0），sensitivity probes 覆盖 credentials/API keys/SSH keys/PII/financial | 课程 Ch6 Listing 9 / Figure 5 | "chains three complementary triage stages into a cascading pipeline"；"default weights (density: 1.0, PW: 1.5, reconstruction: 2.0)" | ✅ 课程 HTML 提取文本 |
| S-6 | 填槽式零样本反演：模板检测域（20 企业域）+ 四扩展策略 + wordlist 成员推断填高熵槽 + margin-aware + consensus voting；attractor candidates 用 500–5,000 定向词表缓解 | 课程 Ch6 Listing 11–14 | "separate the problem into two stages"；"scoring hundreds of thousands of templates ... voting panel" | ✅ 课程 HTML 提取文本 |
| S-7 | 五大限制：token length（工具 32–64 vs 真实块 256–512）、high-entropy、model identification、dimensionality reduction/quantization（PQ/SQ）、domain mismatch | 课程 Ch6 §6.1 BLOCK 9 / Figure 3 | " Vec2Text's primary results ... 32-token inputs"；"ZSInvert was tested up to 64 tokens" | ✅ 课程 HTML 提取文本 |
| S-8 | 决策矩阵：Table 1（四方法需求）+ Table 2（prep/attack time、GPU、invasiveness、best when） | 课程 Ch6 Table 1 / Table 2 / BLOCK 44 | "typical decision path in a time-constrained engagement" | ✅ 课程 HTML 提取文本 |
| S-9 | PyRIT v1.1.0 无 embedding 反演/成员推断/向量库原语；emb-07 编排用 OpenAIChatTarget + SQLiteMemory | `docs/research/attack-embeddings-canonical.md` §2 S-12/S-13、`pyrit-canonical-references.md` §3 | "无 `*Attack` 覆盖 embedding" | ✅ 项目既有调研 |
| S-10 | AIVP 无独立 embedding 反演 lab → 本地合成夹具为主验证面；ALGEN/Vec2Text 环境相关 | `docs/research/attack-embeddings-canonical.md` §1.6/§4/§5 C-1 | "AIVP 无独立 embedding 反演专用 lab" | ✅ 项目既有调研 |

## 3. 差距 → 一手源映射（P0/P1/P2）

| 差距（Ch6 对照） | 一手源 | 实现约束 | 优先级 |
|---|---|---|---|
| embedding 批量导出 .npy/.csv/.parquet | S-4 Listing 3 | GraphQL cursor 分页；float32 保留精度；落盘三格式 | P0 |
| inference probing（3 策略 + deep mode + 多粒度 + top5_avg + 分离度 + pairs 落盘） | S-4 Listing 8 | 维度过滤候选；单句/句对/全文；cos≥0.85 判命中；供 ALGEN 对齐 | P0 |
| chunk triage 三级 + 加权 RRF + sensitivity probes | S-5 Listing 9 | 级联缩池；RRF 按 rank 融合；可追溯 chunk 索引 | P0 |
| 模板填槽式反演（域检测 + 扩展 + 成员推断 + margin-aware + consensus） | S-6 Listing 11–13 | 两阶段（结构+填槽）；margin-aware 避语义重叠误报 | P0 |
| 维度指纹对照表（多模型共享维度输出候选） | S-4 Listing 5–7 | 384/768 不唯一；输出候选列表 + 需 probing 确认 | P1 |
| beam search 反演（GPT-2/Zero2Text + 高熵检测 + dual-embedder ridge） | S-3 + S-6 Listing 15 | 论文 training-free ridge；课程用 GPT-2 beam；记录差异 | P1 |
| 决策矩阵 Table 1/2 → runner 择路 | S-8 | 布尔判据驱动；时间紧默认 emb_fin→zero2text→ALGEN→Vec2Text | P1 |
| 限制前置判定（token/quantization/domain/high-entropy/model-id） | S-7 | 作为可行性门禁；不满足时如实标注或改路 | P1 |
| 规格真实性（spec-v2 AC-3 Vec2Text 措辞） | S-1 + S-10 C-3 | 夹具替身 ≠ 真实 Vec2Text 92%；修正措辞 | P1 |
| ALGEN + canary + rag_probe + 多候选推断 | S-2 + S-10 C-1 | 环境相关；待 C-1 取证或标注不适用 | P1（条件） |
| Vec2Text inverter+corrector + recon-guided | S-1 + S-10 C-1 | 环境相关；60h GPU 不可行时标不适用 | P1（条件） |
| attribute-inference 概念与脚本 | S-4 §6.1 BLOCK 3 | 课程列为三类攻击之一；用于 triage 前置筛选 | P2 |
| canary 清理/stealth、付费 API 预算、随机串不可恢复判据 | S-6/S-7/S-4 BLOCK 38 | 风险注意事项；写进 SKILL.md 失败与豁免 | P2 |

## 4. 已排除（勿再当事实）

| 名称/假设 | 排除依据 |
|---|---|
| ALGEN 论文有 canary 注入 / token 64 / RAG probing | S-2 原文只讲 cross-model alignment + generation；课程适配非论文事实 |
| Zero2Text 需要训练 / 用 1k 泄漏对 | S-3 原文明确 training-free、zero leaked pairs |
| Vec2Text 论文用 200 模板企业语料 / 单 T4 | S-1 原文用 million instructions + 多 GPU；课程适配非论文事实 |
| AIVP 有独立 embedding 反演 lab | S-10 canonical §4 已排除；课程 lab 是 OffSec 演练环境非 AIVP |
| 项目已实现 Ch6 的导出/probing/triage/填槽 | 全仓 grep 无 `inference_probing`/`chunk_triage`/`generate_templates`/`algen`/`canary`/`beam_search` 实现 |

## 5. 待核实（带取证方式，不阻塞）

| # | 待核实项 | 取证方式 | 状态 |
|---|---|---|---|
| C-1 | AIVP 是否存在可查询 embedding 端点/向量库 | 轻探针 `curl <API>/v1/models`、`/embed`；若仅 SPA 回退记 ABSENT | 待现场 |
| C-5 | Zero2Text 课程脚本（GPT-2 beam + ridge dual-embedder）与论文 recursive alignment 的等价度 | 论文 HTML §Method vs 课程 Listing 15；记录为「课程近似实现」 | 部分（abstract 已核） |
| C-6 | ALGEN 课程适配（canary 50k→3k、FlanT5-small、max_length 64）还原率 | 需真实 GPU + 目标 lab；AIVP 无 lab 时标「环境不适用」 | 待现场 |

## 6. G0 门禁记录（阶段 1）

| 编号 | 检查项 | 依据 | 实测结果（命令 + 输出摘要） | 判定 | 不符合项描述 | 修正要求 | 复验结果 | 结论 |
|---|---|---|---|---|---|---|---|---|
| B7 | PyRIT 版本与对象图 | S-9 | `pyrit==1.1.0`，无 embedding 原语；组合 vec2text+PyRIT+自定义（矩阵⑨） | 符合 | 无 | — | 矩阵 §2⑨ 对齐 | PASS |
| B8 | 可追溯性 | S-1..S-10 | 10/10 附 URL 或项目路径锚点；13 差距逐条映射 | 符合 | 无 | — | 抽查 S-2/S-3 重读 | PASS |
| B9 | 框架选型合规 | §1.4 两份资料 | 组合取自矩阵⑨，偏离 0 | 符合 | 无 | — | `grep` 矩阵 attack-embeddings 条目 | PASS |
| 验收① | 结论可定位一手源 | §2 | 三篇论文 URL + abstract 原文实读；课程 Listing 编号 | 符合 | — | — | — | PASS |
| 验收② | 版本号明确 | S-1/S-2/S-3 | EMNLP'23 / ACL 2025 / arXiv:2602.01757v2 | 符合 | — | — | — | PASS |
| 验收③ | 每条差距有源映射 | §3 | 13 条差距全映射 | 符合 | — | — | — | PASS |
| 验收④ | 待核实项命名+取证 | §5 | C-1/C-5/C-6 各含取证方式 | 符合 | — | — | — | PASS |

**结论：PASS**。不符合项 0。上游无（阶段 1 为首阶段，本次为增量差距调研，与原 canonical 并存不覆盖）。

## 7. 关联文档

- 行为唯一来源：`skills/attack-embeddings/SKILL.md`
- 原调研（并存）：`docs/research/attack-embeddings-canonical.md`
- 规格 v1/v2（issue #158）：本次阶段 2/3 将追加增量章节
- 术语基准：`GLOSSARY.md`
- 主线规范：`docs/operations/skill-mainline-workflow.md` v1.2
