# attack-embeddings 模块与接口设计（阶段 6）

> 输入：规格 v2（#158）、工单 #162–#171、`tools/` 既有约定（零外部依赖 + 延迟导入 + 假后端）。
> 原则：接口少、实现深；seam 置于最高层；依赖方向单向。

## 1. 模块布局（`tools/attack_embeddings/`）

| 模块 | 职责 | 公开接口 |
|---|---|---|
| `model.py` | 数据模型、判定级别 | `AttackRequest` `AttackReport` `StepVerdict` `LEVELS` `Finding` |
| `harness.py` | 本地夹具：确定性 embedder + 内存向量库 + 检索器 | `DeterministicEmbedder` `InMemoryVectorStore` `EmbeddingHarness` |
| `attacks.py` | 四类攻击原语 | `invert` `membership_inference` `adversarial_shift` `vector_lookup` `rag_impact` |
| `evidence.py` | 证据 seam（复用 recon_ai） | `EvidenceWriter` `RecordingWriter`（C1 复用） |
| `runner.py` | 对象图构造 + 编排 | `Runtime` `run_attack` `OBJECT_GRAPH` `STEP_IDS` |
| `cli.py` | 命令行入口 | `main` |
| `__init__.py` | 公开面聚合 | 仅导出上述公开符号 |

## 2. Seam 清单（与阶段 2 结论一致）

| Seam | 默认实现（零依赖） | 可注入 | 对应阶段 2 |
|---|---|---|---|
| EmbeddingModel | `DeterministicEmbedder`（哈希词袋，确定性） | 真实 embedder / `text-embedding-3-small` | S2 |
| VectorStore | `InMemoryVectorStore`（余弦 top-k） | FAISS / Chroma / pgvector | S2 |
| Inverter | `LexiconInverter`（vec2text 风格最近 token 还原） | `vec2text.analyze_utils` 预训练模型 | S1 |
| RagTarget（emb-07） | `FakeRagTarget`（确定性生成桩） | PyRIT `OpenAIChatTarget`（延迟导入） | S4 |
| Evidence | `recon_ai.evidence.EvidenceWriter` + `collect_evidence.py` | — | S3 |

seam 数量 = 4（+证据复用），与阶段 2 的 S1–S4 一一对应；新增 0。

## 3. 依赖方向（单向、无环）

`cli → runner → attacks → harness → model`；`runner → evidence → (recon_ai.evidence, collect_evidence)`。
PyRIT 仅在 `rag_impact` 内延迟导入；CI/测试不安装 pyrit 时走 `FakeRagTarget`。

## 4. 对象图构造

`run_attack(request)` 在入口按 `Runtime` 注入的 seam 构造对象图：embedder→store→inverter→target→evidence；单次构造、向下传递，不在子函数内重复 new（减少变更面）。

## 5. 权衡与被否决方案

- 否决「单文件 monolith」：不可单测、seam 不可注入。
- 否决「CI 下载真实 vec2text 模型」：违反零依赖策略（ADR-0003）；真实模型仅为可选核实闸 C-3。
- 否决「用 PyRIT 做反演/MIA」：v1.1.0 无 embedding 原语（调研 S-12），强行即违反 B9。

## 6. 公开接口契约（错误行为）

- `invert(vec)`：空向量→`ValueError`；未知维度→按最近词典回退并标注 `confidence`。
- `membership_inference(sample)`：空样本→`ValueError`；σ≤0→默认 0.01。
- `vector_lookup(concept, k)`：store 为空→返回 `[]`；k≤0→`ValueError`。
- `run_attack`：无 embedding 面→返回 `degraded` 报告（AC-11），不抛异常。
