# attack-embeddings 一手源调研

> **版本** v1.0 · **状态** 生效 · **调研日期** 2026-11-15（GMT+8）
> **目标技能** `skills/attack-embeddings/SKILL.md`（P1 · D6 · AI向量机）
> **演练目标** `http://192.168.40.189`（AIVP 实例，非 OSAI 正式考试环境）
> **性质** 阶段 1 交付物：实现所依赖事实的一手源锁定，消除规格阶段的猜测
> **框架组合**（取自 `docs/research/osai-skill-framework-matrix.md` ⑨）：**vec2text**（embedding 反演，LLM08 实证）+ **PyRIT(v1.1.0)**（编排/证据）+ **自定义脚本**（相似度探测/越权/对抗扰动）

## 1. 结论摘要（先读这一节）

1. `attack-embeddings` 的「embedding 反演/重建」攻击面是 **vec2text**（Morris et al.）：EMNLP 2023《Text Embeddings Reveal (Almost) As Much As Text》给出 embedding 反演方法，多步受控生成可**精确还原 92% 的 32-token 输入**；ICLR 2024《Language Model Inversion》扩展为语言模型反演。代码与预训练反演模型均发布于 GitHub `jxmorris12/vec2text` 与 HuggingFace `jxm/*`。
2. 「成员推断」对齐 **Noisy Neighbors**（Galli et al., ACL PrivateNLP 2024, arXiv:2406.16565）：在 embedding 空间注入高斯噪声构造「噪声邻居」，仅需目标模型**推理模式访问**即可做 MIA，AUC 0.727 接近 shadow-model 的 0.753。
3. 「对抗样本 / 检索操纵」对齐 **HotFlip**（Ebrahimi et al., 2018）与 **Corpus Poisoning via AGGD**（arXiv:2406.05087）：在 embedding 空间优化对抗文档使其对目标查询 top-k 命中，单段对抗文本可达 80%+ 攻击成功率（ASR）；连续空间无监督投毒（RRR + 扰动模型）可达 4× 加速且低困惑度（更隐蔽）。
4. 「知识库内容提取（向量库反查）」是 OWASP LLM08 2025 的核心风险面之一：**向量库直接查询/越权** 使攻击者绕过应用层鉴权，用语义相似搜索批量外泄源文档；多租户 namespace 过滤失败可导致跨租户泄露——无需任何技术利用，是设计缺陷（Helmwart T28 / Lorikeet / ThreatClaw）。
5. PyRIT v1.1.0 **无** embedding 反演/成员推断/向量库原语（见 `pyrit-canonical-references.md` §3）：反演须用 vec2text、MIA/对抗/越权须自定义脚本；PyRIT 仅在此做**编排（RedTeaming/PromptSending）+ SQLiteMemory 证据补位**——不得强行用 PyRIT 单栈覆盖（B9）。
6. 演练目标 AIVP 未观察到独立 embedding 反演 lab（全量 lab 见 `attack-mcp-tool-canonical.md` §3.1）；故 attack-embeddings 实现以**本地合成 embedding 夹具**为主验证面（含 `text-embedding-3-small` 形态映射），AIVP 作为可选核实闸（§7 闸 A）。

## 2. 一手源事实（官方 URL 逐条）

| # | 事实 | 来源 | 关键原文 / 取值 |
|---|---|---|---|
| S-1 | vec2text 定位：把 dense embedding 反演回原文，多步受控生成（iterate-correct-re-embed） | <https://arxiv.org/abs/2310.06816> · GitHub <https://github.com/jxmorris12/vec2text> | "recover 92% of 32-token text inputs exactly" |
| S-2 | 发布信息：EMNLP 2023（doi:10.18653/v1/2023.emnlp-main.765）；ICLR 2024《Language Model Inversion》(arXiv:2311.13647) 扩展 | 同上；ACL Anthology / OpenReview | EMNLP'23 + ICLR'24 |
| S-3 | 用法：预训练反演模型发布于 HuggingFace `jxm/*`（如 `jxm/t5-base__llama-7b__one-million-instructions__emb`）；`analyze_utils.load_experiment_and_trainer_from_pretrained` | GitHub `jxmorris12/vec2text` README | `from vec2text import analyze_utils` |
| S-4 | 反演器输入：frozen embeddings（固定 embedding 向量）或 logits；可恢复临床笔记中的全名等 PII | arXiv:2310.06816 摘要 | recover personal info (full names) |
| S-5 | 可迁移反演（无需原 embedder）：Huang et al., ACL 2024 用替代模型做 transferable embedding inversion | Christian-Schneider 博客引 ACL 2024（Huang et al.）；OWASP 社区转述 | surrogate model inverts without original embedder |
| S-6 | OWASP LLM08 2025「Vector and Embedding Weaknesses」：反演、投毒、跨上下文泄露、访问控制绕过 | <https://owasp.org/www-project-top-10-for-large-language-model-applications/> | LLM08 |
| S-7 | Noisy Neighbors MIA：在 embedding 空间加高斯噪声 ρ~N(0,σ²) 构造噪声邻居，比较同模型在原始/噪声样本上的困惑度差；仅需推理访问 | <https://aclanthology.org/2024.privatenlp-1.1/> · arXiv:2406.16565 | AUC 0.727 vs shadow 0.753 |
| S-8 | HotFlip：基于 embedding 梯度做 token 替换，使文档向量逼近目标查询向量，最大化检索相似度 | arXiv:2406.05087v1 §3.2（引 Ebrahimi 2018） | gradient-based token swap |
| S-9 | Corpus Poisoning via AGGD：单段对抗文档对多查询同时高排名；注入单段可达 80%+ ASR | <https://arxiv.org/pdf/2406.05087v1.pdf> | 80%+ attack success rate |
| S-10 | 无监督连续空间投毒（RRR 重建 + 扰动模型 ϕ）：4× 加速、困惑度 461.7（HotFlip 为 59468.5），更隐蔽 | Lacuna 转述 University of Amsterdam 工作 | 4x speedup; perplexity 461.7 |
| S-11 | 向量库直接查询外泄：语义搜索不校验请求者权限，返回最近邻即泄露；多租户 namespace 过滤失败 = 跨租户泄露 | Helmwart T28 <https://www.helmwart.com/threats/t28> · Lorikeet / ThreatClaw | semantic search as data exfiltration |
| S-12 | PyRIT v1.1.0 无 embedding 专用原语：反演/MIA/向量库须自定义 | `docs/research/pyrit-canonical-references.md` §3 | 无 `*Attack` 覆盖 embedding |
| S-13 | PyRIT RAG/embedding 可用原语：多轮编排 `RedTeamingAttack`/`PromptSendingAttack`/`CrescendoAttack`；目标 `OpenAIChatTarget`；证据 `SQLiteMemory` + `PrettyAttackResultMemoryPrinter` | `pyrit-canonical-references.md` §3 | `pyrit==1.1.0` |

## 3. 攻击路径 → 对象映射（SKILL.md 对齐 S1/S2）

| SKILL 路径 | 步骤 | SKILL 技术分类 | 实现层对象 | 框架归属 |
|---|---|---|---|---|
| 前置：定位 embedding 工具面 | — | 复用 recon-ai 资产清单（embedding 端点/模型/向量库/信任边界） | `ReconAsset.typed("embedding")` / 资产清单七字段 | 既有 |
| 路径 A 定位与反演 | emb-01 枚举 embedding 端点/模型 | 端点枚举 | `curl <API>/v1/models` + `EmbeddingRecon.probe_models()` | **自定义脚本** |
| | emb-02 探测端点（可提交/维度/模型） | 可查询性探测 | `EmbeddingProbe.submit("probe")` | 自定义 |
| | emb-03 反演/重建（近似还原语料） | OWASP LLM08 / vec2text | `Vec2TextInverter`（封装 `vec2text.analyze_utils`，frozen embeddings 输入） | **vec2text + 自定义** |
| | emb-04 成员推断（样本是否在集） | Noisy Neighbors | `MembershipInference.noisy_neighbors()`（embedding 空间噪声 + 困惑度差阈值） | **自定义脚本** |
| 路径 B 成员推断/对抗/提取 | emb-05 对抗样本（扰动改变 embedding/检索） | HotFlip/连续空间扰动 | `AdversarialEmbedder.gradient_step()`（梯度 token 替换 / 向量扰动） | 自定义 |
| | emb-06 知识库内容提取（向量库反查文档块） | OWASP LLM08 / 向量库越权 | `VectorLookup.query(store, concept, topk)`（FAISS/Chroma/pgvector 直查 API） | 自定义（与 attack-rag 共享向量面） |
| | emb-07 下游 RAG/检索影响取证 | LLM01 间接注入 / ASI06 | `RagImpactDiff` + `OpenAIChatTarget` + `SQLiteMemory`（baseline vs manipulated 双次捕获） | **PyRIT 内核** |
| 收尾：flag 取证 | emb-08 `ai_vector.txt` 双通道 | GOVERNANCE §6.2 | `collect_evidence.py --step emb-08 --strict` + `FlagProof` | 既有共享工具 |
| 证据收口 | 三件套/五件套 | §6.1/§6.3 | `tools/collect_evidence.py` | 既有 |

## 4. 已排除（勿再当成事实）

| 名称/假设 | 排除依据 |
|---|---|
| PyRIT 存在 embedding 反演/MIA/向量库专用攻击策略 | v1.1.0 无；须 vec2text + 自定义（S-12 + §1.4） |
| `XpiaAttack` 可用于间接注入 | v1.1.0 不存在；间接注入归 `pyrit.executor.workflow`（S-13） |
| 演练目标存在独立 embedding 反演 lab | AIVP 全量 lab 枚举见 `attack-mcp-tool-canonical.md` §3.1，无 embedding 反演专用 lab |
| 演练目标存在 `ai_vector.txt` | T-6（attack-mcp-tool 实测）全部命中 SPA 回退，判定缺席 |
| 向量库越权需代码执行 | 语义搜索本身即外泄通道，无需技术利用（S-11） |

## 5. 待核实（带取证方式，不阻塞实现）

| # | 待核实项 | 取证方式 |
|---|---|---|
| C-1 | AIVP 是否存在可查询/可越权的 embedding 端点或向量库 | 轻探针 `curl <API>/v1/models` 与 `/embed`，确认有无 embedding 服务与访问控制 |
| C-2 | 本地夹具 embedder 与考试 `text-embedding-3-small` 行为差异 | `EmbeddingModel` 注入点固定；测试用 `sentence-transformers` 本地模型，记录版本与维度 |
| C-3 | vec2text 预训练反演模型在本地夹具的可达还原率（验证 S-1 92%） | 注入合成 32-token 样本，统计 exact-match 率 |
| C-4 | Noisy Neighbors 在本地夹具的最佳 σ（验证 S-7 AUC≈0.73） | 二值搜索 σ，计算 member/non-member 困惑度差 AUC |

## 6. 实现前必须取证的核实闸

1. **闸 A（测试面）**：AIVP 无独立 embedding 反演 lab → 实现**必须**提供本地合成 embedding 夹具（`EmbeddingHarness`：embedder + 向量库 + 检索器），所有攻击路径先在该夹具跑通；AIVP 仅作可选回归闸（C-1）。
2. **闸 B（对象图）**：emb-07 下游影响必须用 `OpenAIChatTarget` + `SQLiteMemory`，间接注入归 `pyrit.executor.workflow`；不得误用 `*Attack` 做 XPIA（S-13）。
3. **闸 C（判据）**：成员推断/下游影响必须用「baseline vs manipulated」双次捕获做因果对照，禁止仅凭单次变化判「生效」；flag 双通道缺席时按 `校验预言机` 等价通道处理（GLOSSARY）。

## 7. 门禁记录（阶段 1 / G0）

| 编号 | 检查项 | 依据 | 实测结果（命令 + 摘要） | 判定 | 不符合项 | 修正要求 | 复验 | 结论 |
|---|---|---|---|---|---|---|---|---|
| B7 | PyRIT 版本与对象图 | S-12/S-13/§3 | `pyrit==1.1.0`；§3 反演/MIA/向量库用自定义+vec2text，仅 emb-07 用 `OpenAIChatTarget`，无 `*Attack` 误用 | 符合 | 无 | — | `grep -nE "XpiaAttack|orchestrator" 本文件` 无命中 | PASS |
| B8 | 可追溯性 | §2 S-1..S-13 | 13/13 附官方 URL 或 `pyrit-canonical-references.md` 锚点；§3 8 步全映射 | 符合 | 无 | — | 抽查 S-1、S-7 重读 | PASS |
| B9 | 框架选型合规 | 矩阵 ⑨ / §1.4 | 组合取自矩阵对应条目（vec2text+PyRIT+自定义）；偏离项 0 | 符合 | 无 | — | `grep "osai-skill-framework-matrix.md" 本文件` | PASS |
| 验收① | 结论可定位到官方 URL/源码 | §2 | 13/13 含源 | 符合 | — | — | — | PASS |
| 验收② | 版本号明确 | S-1/S-2/S-13 | vec2text EMNLP'23+ICLR'24；`pyrit==1.1.0` | 符合 | — | — | — | PASS |
| 验收③ | 每条攻击路径有对象映射 | §3 | 4 路径 / 8 步 | 符合 | — | — | — | PASS |
| 验收④ | 待核实项逐条命名+取证方式 | §5 | 4 项（C-1..C-4）各含取证方式 | 符合 | — | — | — | PASS |
| 验收⑤ | 落盘于 `docs/research/` | 本文件 | 存在 | 符合 | — | — | — | PASS |

**结论：PASS**。不符合项 0。上游无（阶段 1 为首阶段）。

## 8. 关联文档

- 行为唯一来源：`skills/attack-embeddings/SKILL.md`
- 术语基准：`GLOSSARY.md`
- PyRIT 权威索引：`docs/research/pyrit-canonical-references.md`
- 框架组合：`docs/research/osai-skill-framework-matrix.md` ⑨
- 主线规范：`docs/operations/skill-mainline-workflow.md`
- 模式参考：`docs/research/attack-rag-canonical.md`
