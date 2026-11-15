# attack-embeddings 行为规格 v1（What）

> 行为唯一来源：`skills/attack-embeddings/SKILL.md`（P1 · D6 · AI向量机）
> 框架组合（取自矩阵 ⑨）：vec2text + PyRIT(v1.1.0) + 自定义脚本
> 调研依据：`docs/research/attack-embeddings-canonical.md`（阶段 1，G0 PASS）
> 本版本仅回答「做什么」；实现细节（文件路径/代码）不在本层。

## 1. Problem Statement

考试 AI 向量主分面（75/100）中，embedding 模型与向量库构成独立的高杠杆计分面（每台 AI向量机 15 分）。取得内网立足点并复用 `recon-ai` 资产清单后，目标暴露四类风险：embedding 端点可查询、向量可反演还原语料、成员可被推断、向量库可被越权反查并操纵下游 RAG/检索。当前仓库缺一个可逐步复现、证据结构化、对齐 `report-exam` 的 attack-embeddings 落地能力。本规格把 `SKILL.md` 声明的攻击逻辑翻译为用户视角的行为描述，作为可评审的输入。

## 2. Solution

按「定位 embedding 面 → 探测端点 → 反演/重建 → 成员推断 → 对抗样本 → 知识库提取 → 下游决策影响取证 → flag 取证」顺序推进，每一步经 `tools/collect_evidence.py` 落盘三件套/五件套证据，未过质量门不得进入下一步。反演用 vec2text，成员推断用 Noisy Neighbors 方法，对抗样本用 HotFlip/连续空间扰动，向量库提取用向量库直查 API，下游影响用 PyRIT 编排并由 `SQLiteMemory` 留证。所有路径先在本地合成 embedding 夹具跑通，AIVP 仅作可选回归闸。

## 3. User Stories

- US-1 作为红队工程师，我能枚举目标的 embedding 端点与模型清单（`/v1/models`），确认可查询面，以便确定反演/探测入口。
- US-2 作为红队工程师，我能向 embedding 端点提交探测文本，确认其返回维度与所用模型，以便建立正常检索/相似度基线。
- US-3 作为红队工程师，我能用 vec2text 从 embedding 向量近似还原训练/检索语料，记录还原命中率与置信度，以便证明 sensitive information disclosure。
- US-4 作为红队工程师，我能通过向量距离/困惑度差异判断某样本是否属于训练/检索集（成员推断），以便证明模型记忆了私有数据。
- US-5 作为红队工程师，我能在输入上加细微扰动使 embedding 或检索/分类结果偏离基线（对抗样本），以便证明检索可被操纵。
- US-6 作为红队工程师，我能直接查询向量库从嵌入空间反查知识库文档块（与 attack-rag 共享向量面），以便证明向量库越权/数据外泄。
- US-7 作为红队工程师，我能对比操纵前后检索结果，证明 RAG 检索/生成被影响，并含 AI 交互日志，以便证明下游影响。
- US-8 作为红队工程师，我能在取得 embedding 面代码执行/数据访问后定位并读取 `ai_vector.txt`，向独立机延伸 embedding 工具滥用，以便完成 AI向量机 flag 取证。
- US-9 作为技术读者，我能在不知道任何内部上下文的情况下，按证据逐步 copy/paste 复现每一步命令与输出，以便满足 §6.1 报告门槛。
- US-10 作为审计者，我能核验每步证据三件套（命令+输出+截图）与反演前后对照、下游 RAG 被操纵取证、flag 双通道一致，以便满足 §6.2/§6.3 质量门。
- US-11 作为考试参与者，当目标无 embedding 接口或不可查询、反演仅部分生效、对抗被护栏拦截、或判为诱饵机时，我能按 SKILL.md 失败与豁免条款降级处理并在 ≤30 分钟内结束零分主机，以便不空耗。

## 4. Implementation Decisions

- 框架组合取自矩阵 ⑨：vec2text（反演）+ PyRIT（emb-07 编排/证据）+ 自定义脚本（探测/MIA/对抗/向量库）。PyRIT 仅在其占优场景做主角，不强行单栈覆盖 embedding 面。
- 反演/MIA/对抗/向量库的实现封装在统一的工具命名空间下，对外暴露高层函数（反演、成员推断、对抗扰动、向量反查），内部可替换 embedder 与向量库后端。
- 下游影响（emb-07）使用 PyRIT 的 `OpenAIChatTarget` 与 `SQLiteMemory` 做 baseline vs manipulated 双次捕获；间接注入归 `pyrit.executor.workflow`，不误用 `*Attack`。
- 本地合成 embedding 夹具（embedder + 向量库 + 检索器）作为主验证面；embedder 经注入点可替换，以映射考试 `text-embedding-3-small` 形态。
- 每步证据统一经 `tools/collect_evidence.py --strict` 落盘，结构对齐 `report-exam` 的 Attack Walkthrough，无需二次整理。

## 5. Testing Decisions

- 仅测外部行为：反演还原率、成员推断 AUC、对抗扰动后相似度偏移、向量库反查命中、flag 双通道一致性。
- 既有参考测试：复用 `tests/` 中 `collect_evidence` 的 evidence_contract 夹具模式；参考 `attack-rag` 夹具设计。
- 本地夹具驱动的端到端链路作为主测试面；AIVP 相关用例为可选回归。
- 不断言实现细节（如具体 token 替换算法），只断言可观测的检索/还原/推断结果。

## 6. Out of Scope

- 目标无 embedding 接口或不可查询时，改走 attack-rag（检索层）或 attack-ai-agent（按 SKILL.md 失败与豁免）。
- 真实考试环境的端到端取证（属演练/AIVP 回归，非本规格必交付）。
- 向量库自身加固/防御实现（本规格只做红队面，不作蓝队修复）。
- PyRIT 原生 embedding 原语开发（v1.1.0 无，已排除）。

## 7. Further Notes

- 术语以 `GLOSSARY.md` 为准：用「AI向量机」「向量库」「embedding」「成员推断」「对抗样本」「反演」等规范词。
- 与 attack-rag 共享向量库/embedding 面，须避免重复实现向量查询原语。
- 待核实项（C-1..C-4）见调研文档 §5，不阻塞规格，实现前取证。

## 8. Seam 提案（需与用户核对）

- **S1 反演 seam**：`Vec2TextInverter` 封装 vec2text，输入 frozen embeddings，输出还原文本；后端可替换为本地自训反演模型。
- **S2 检索 seam**：`EmbeddingHarness` 统一 embedder + 向量库 + 检索器，作为所有路径的本地验证面与可注入依赖。
- **S3 证据 seam**：复用既有 `tools/collect_evidence.py`，不新增证据机制。
- **S4 编排 seam**：emb-07 经 PyRIT `OpenAIChatTarget`+`SQLiteMemory` 单入口构造对象图。
- 结论：seam 数量压到最少（4 个），均置于最高层，与阶段 2 结论一致；待用户在评审中确认或调整。
