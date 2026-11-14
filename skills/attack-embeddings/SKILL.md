---
name: attack-embeddings
priority: P1
domain: D6
scoring_unit: AI向量机
trigger: recon-ai 已确认目标暴露 embedding 模型/接口，且已取得可达 AI 向量机的内网立足点（foothold-traditional 之后）
input: recon-ai 资产清单（embedding 端点、模型名、向量库来源与信任边界）、已取得上下文与身份
output: 每攻击步骤「命令 + 输出 + 截图」证据、反演/提取前后对照、下游 RAG/检索被操纵取证、ai_vector.txt flag 取证（AI向量机）
---

# attack-embeddings — Embedding 反演与信息提取

攻击 embedding 模型与接口，覆盖四大攻击面：**embedding 面定位与反演/重建**、**成员推断与对抗样本**、**知识库内容提取（向量库反查）**、**下游 RAG/检索影响取证**。embedding 反演/提取属模型反演与训练数据提取类风险（业界归类于 sensitive information disclosure / model extraction），是 exam 环境 AI 向量机（每台 15 分）的高杠杆计分面。取得内网立足点后亦向独立机延伸 embedding 工具滥用，形成第二个 15 分目标；两者 flag 文件均为 `ai_vector.txt`。

## 执行体

按「定位 embedding 面 → 探测端点 → 反演/重建 → 成员推断 → 对抗样本 → 知识库提取 → 下游影响取证 → flag 取证」顺序推进，每步经 `tools/collect_evidence.py` 落盘证据，未过质量门不得进入下一步。

### 前置：定位 embedding 工具面

1. 复用 `recon-ai` 资产清单，确认 embedding 端点、模型名（如 `text-embedding-3-small`）、向量库（如 FAISS / Chroma / pgvector）与信任边界。
2. 记录正常检索/相似度基线，作为后续反演/操纵效果的对照。

### 攻击路径 A — embedding 定位与反演/重建

1. **emb-01 定位 embedding 模型/接口**：枚举 embedding 端点与模型清单，确认可查询面。
   - 命令：`curl -s <EMBED_API>/v1/models`
   - 证据：`python tools/collect_evidence.py --step emb-01 --cmd "curl -s <EMBED_API>/v1/models" --out loot/emb-01-surface.md --shot-cmd "screenshot --region embed_models" --target <EMBED_API> --strict`
2. **emb-02 探测 embedding 端点（可查询性/维度/模型）**：确认端点可提交文本、返回维度与所用模型。
   - 命令：`curl -s <EMBED_API>/embed -H "Content-Type: application/json" -d '{"input":"probe"}'`
   - 证据：`python tools/collect_evidence.py --step emb-02 --cmd "curl -s <EMBED_API>/embed -d '<probe payload>'" --out loot/emb-02-probe.md --shot-cmd "screenshot --region embed_probe" --target <EMBED_API> --strict`
3. **emb-03 embedding 反演/重建（近似还原语料）**：用向量反查/优化方法从 embedding 近似还原训练或检索语料（示意脚本，须记录来源）。
   - 命令：`python tools/embed_invert.py --endpoint <EMBED_API> --vec out.vec --topk 50`
   - 证据：`python tools/collect_evidence.py --step emb-03 --cmd "python tools/embed_invert.py --endpoint <EMBED_API>" --out loot/emb-03-invert.md --shot-cmd "screenshot --region inversion" --target <EMBED_API> --strict`
4. **emb-04 成员推断（样本是否在训练/检索集）**：通过向量距离/置信度差异判断某样本是否属于训练或检索集（示意脚本，须记录来源）。
   - 命令：`python tools/membership_inference.py --endpoint <EMBED_API> --sample suspect.txt`
   - 证据：`python tools/collect_evidence.py --step emb-04 --cmd "python tools/membership_inference.py --endpoint <EMBED_API>" --out loot/emb-04-membership.md --shot-cmd "screenshot --region membership" --target <EMBED_API> --strict`

### 攻击路径 B — 成员推断/对抗样本/知识库提取

5. **emb-05 对抗样本（扰动改变 embedding/检索）**：在输入上加细微扰动，使 embedding 或检索/分类结果偏离基线（示意脚本，须记录来源）。
   - 命令：`python tools/adv_embed.py --endpoint <EMBED_API> --text "benign" --eps 0.01`
   - 证据：`python tools/collect_evidence.py --step emb-05 --cmd "python tools/adv_embed.py --endpoint <EMBED_API>" --out loot/emb-05-adv.md --shot-cmd "screenshot --region adv" --target <EMBED_API> --strict`
6. **emb-06 知识库内容提取（向量库反查文档块）**：直接查询向量库，从嵌入空间反查知识库文档块，与 `attack-rag` 共享向量库/embedding 面（示意脚本，须记录来源）。
   - 命令：`python tools/vector_lookup.py --store <VECTOR_DB> --query "<target concept>" --topk 50`
   - 证据：`python tools/collect_evidence.py --step emb-06 --cmd "python tools/vector_lookup.py --store <VECTOR_DB>" --out loot/emb-06-kb-extract.md --shot-cmd "screenshot --region kb_extract" --target <VECTOR_DB> --strict`
7. **emb-07 下游 RAG/检索影响取证**：对比操纵前后检索结果，证明 RAG 检索/生成被影响，含 AI 交互日志（§6.3）。
   - 命令：`curl -s <RAG_API>/query -H "Content-Type: application/json" -d '{"q":"<poisoned concept>"}'`
   - 证据：`python tools/collect_evidence.py --step emb-07 --cmd "curl -s <RAG_API>/query -d '<poisoned query>'" --out loot/emb-07-rag-impact.md --shot-cmd "screenshot --region rag_impact" --ai-log "见 loot/emb-07-rag-impact.md" --target <RAG_API> --strict`

### 收尾：flag 取证

1. **emb-08 flag 取证（AI向量机）**：取得 embedding 面代码执行/数据访问后定位并读取 `ai_vector.txt`；向独立机延伸 embedding 工具滥用重复上述流程。
   - 命令：`whoami; id; find / -name ai_vector.txt 2>/dev/null -exec cat {} \;`
   - 证据：`python tools/collect_evidence.py --step emb-08 --cmd "whoami; id; find / -name ai_vector.txt 2>/dev/null -exec cat {} \;" --out loot/emb-08-flag.md --shot-cmd "screenshot --region flag_proof" --ai-log "见 loot/emb-08-flag.md" --flag "<ai_vector.txt 值>" --target <AI_VECTOR_HOST> --strict`
2. 取证须含访问证明：`whoami`/`id` + flag 内容同屏截图（对齐 §6.2 双通道一致）。

## 质量门

以下证据**必须**全部产出，缺失任一即判定未过门禁，不得进入下一技能：

- 每个攻击步骤的**确切命令**（可直接 copy/paste）。
- 每步骤的**关键输出**（含反演命中、成员推断判定、对抗扰动效果、向量库反查命中的响应原文）。
- 每步骤的**截图**（访问证明，含目标标识与时间戳）。
- **反演/提取前后对照**证据（向量/文档块 before/after 或命中列表）。
- **下游 RAG/检索被操纵取证**（检索结果差异，含 AI 交互日志 §6.3）。
- `ai_vector.txt` flag 的「面板提交 + 截图」双通道一致。
- 上述每步证据统一通过共享工具 `tools/collect_evidence.py` 产出（对齐 §质量门），保证三件套/五件套结构稳定、与 `report-exam` 的 Attack Walkthrough 兼容、并可由 CI 校验。

## 校验标准

- 攻击过程可被技术读者 **copy/paste 逐步复现**（§6.1）。
- 证据结构与 `report-exam` 的 Attack Walkthrough 小节直接兼容，可**无损复用**，无需二次整理。
- 每步骤满足「命令 + 输出 + 截图」三件套；术语符合 `GLOSSARY.md`（用「AI向量机」「向量库」「embedding」等规范词，禁用 `_Avoid_` 废弃术语）。

## 失败与豁免

- 若目标无 embedding 接口或不可查询，记录判定依据后改走 `attack-rag`（检索层）或 `attack-ai-agent`，不阻塞其余路径。
- 若反演仅部分生效（还原出片段但非完整语料），如实记录命中率与置信度，不得夸大。
- 若对抗样本被护栏拦截，记录拦截行为与原因，评估改走其它扰动策略；不反复重试同一被拦截动作。
- 若目标为疑似诱饵机（0 分、无 AI 向量面），记录判定依据后 ≤30 分钟内结束，不在 0 分主机空耗。
