---
name: attack-supply-chain
priority: P1
domain: D8
scoring_unit: AI向量机
trigger: recon-ai 已确认目标暴露 AI 供应链面（模型仓库/依赖源/数据管道），且已取得可达 AI 向量机的内网立足点（foothold-traditional 之后）
input: recon-ai 资产清单（模型仓库、依赖源、数据管道端点）、已取得上下文与身份
output: 每攻击步骤「命令 + 输出 + 截图」证据、投毒前后对照、下游模型行为影响取证、ai_vector.txt flag 取证（AI向量机）
---

# attack-supply-chain — AI 供应链投毒

攻击 AI 供应链，覆盖三大攻击面：**数据集/模型/适配器投毒**、**依赖/包投毒**、**下游模型行为影响取证**。技术分类对齐 OWASP Agentic ASI04（Agentic Supply Chain Vulnerabilities）与 OWASP LLM03（训练数据投毒）/ LLM05（供应链）。它污染训练或推理产物，间接影响 AI 向量机（每台 15 分）。取得内网立足点后亦向独立机延伸，形成第二个 15 分目标；两者 flag 文件均为 `ai_vector.txt`。

## 执行体

按「发现供应链面 → 数据集投毒 → 模型/适配器投毒 → 数据管道投毒 → 依赖/包投毒 → 构建/运行时触发 → 下游取证 → flag 取证」顺序推进，每步经 `tools/collect_evidence.py` 落盘证据，未过质量门不得进入下一步。

### 前置：发现 AI 供应链面

1. 复用 `recon-ai` 资产清单，确认模型仓库（如 Hugging Face / 内部 registry）、依赖源（PyPI / npm / 内部索引）、数据管道（ETL / 预处理）与信任边界。
2. 记录正常产物哈希/来源，作为后续投毒效果的对照。

### 攻击路径 A — 数据集/模型/适配器投毒

1. **sc-01 发现供应链面**：枚举模型仓库、依赖源、数据管道端点与信任边界。
   - 命令：`curl -s <REGISTRY>/api/models` 或 `pip index versions <pkg>`
   - 证据：`python tools/collect_evidence.py --step sc-01 --cmd "curl -s <REGISTRY>/api/models" --out loot/sc-01-supply-surface.md --shot-cmd "screenshot --region supply_surface" --target <REGISTRY> --strict`
2. **sc-02 数据集投毒**：污染训练/检索数据，使模型或 RAG 产物偏向攻击者（示意脚本，须记录来源）。
   - 命令：`python tools/dataset_poison.py --data <CORPUS> --inject "<trigger>:<target>" --frac 0.01`
   - 证据：`python tools/collect_evidence.py --step sc-02 --cmd "python tools/dataset_poison.py --data <CORPUS>" --out loot/sc-02-data-poison.md --shot-cmd "screenshot --region data_poison" --target <CORPUS> --strict`
3. **sc-03 模型/适配器投毒**：植入后门权重或恶意 LoRA 适配器（示意脚本，须记录来源）。
   - 命令：`python tools/model_poison.py --base <MODEL> --adapter-out loRA-bad.safetensors --trigger "<trigger>"`
   - 证据：`python tools/collect_evidence.py --step sc-03 --cmd "python tools/model_poison.py --base <MODEL>" --out loot/sc-03-model-poison.md --shot-cmd "screenshot --region model_poison" --target <MODEL> --strict`
4. **sc-04 数据管道投毒**：在 ETL / 预处理环节注入恶意变换（示意脚本，须记录来源）。
   - 命令：`python tools/pipeline_poison.py --pipeline <ETL> --stage preprocess --inject "<transform>"`
   - 证据：`python tools/collect_evidence.py --step sc-04 --cmd "python tools/pipeline_poison.py --pipeline <ETL>" --out loot/sc-04-pipeline-poison.md --shot-cmd "screenshot --region pipeline_poison" --target <ETL> --strict`

### 攻击路径 B — 依赖/包投毒

5. **sc-05 依赖/包投毒**：在镜像/包索引/requirements 中注入恶意依赖（typosquat 或替换，示意脚本，须记录来源）。
   - 命令：`python tools/dep_poison.py --index <PYPI> --pkg legit --malicious legit-evil`
   - 证据：`python tools/collect_evidence.py --step sc-05 --cmd "python tools/dep_poison.py --index <PYPI>" --out loot/sc-05-dep-poison.md --shot-cmd "screenshot --region dep_poison" --target <PYPI> --strict`
6. **sc-06 构建/运行时触发**：使投毒在构建或推理时执行非预期代码（示意脚本，须记录来源）。
   - 命令：`python tools/trigger_poison.py --build <CI> --payload "import os; os.system('<cmd>')"`
   - 证据：`python tools/collect_evidence.py --step sc-06 --cmd "python tools/trigger_poison.py --build <CI>" --out loot/sc-06-trigger.md --shot-cmd "screenshot --region trigger" --target <CI> --strict`

### 攻击路径 C — 下游取证与 flag

7. **sc-07 下游模型行为影响取证**：对比投毒前后模型输出/检索结果，证明行为被影响，含 AI 交互日志（§6.3）。
   - 命令：`curl -s <MODEL_API>/generate -H "Content-Type: application/json" -d '{"prompt":"<trigger>"}'`
   - 证据：`python tools/collect_evidence.py --step sc-07 --cmd "curl -s <MODEL_API>/generate -d '<trigger prompt>'" --out loot/sc-07-impact.md --shot-cmd "screenshot --region impact" --ai-log "见 loot/sc-07-impact.md" --target <MODEL_API> --strict`
8. **sc-08 flag 取证（AI向量机）**：取得供应链代码执行/数据访问后定位并读取 `ai_vector.txt`；向独立机延伸供应链投毒重复上述流程。
   - 命令：`whoami; id; find / -name ai_vector.txt 2>/dev/null -exec cat {} \;`
   - 证据：`python tools/collect_evidence.py --step sc-08 --cmd "whoami; id; find / -name ai_vector.txt 2>/dev/null -exec cat {} \;" --out loot/sc-08-flag.md --shot-cmd "screenshot --region flag_proof" --ai-log "见 loot/sc-08-flag.md" --flag "<ai_vector.txt 值>" --target <AI_VECTOR_HOST> --strict`
9. 取证须含访问证明：`whoami`/`id` + flag 内容同屏截图（对齐 §6.2 双通道一致）。

## 质量门

以下证据**必须**全部产出，缺失任一即判定未过门禁，不得进入下一技能：

- 每个攻击步骤的**确切命令**（可直接 copy/paste）。
- 每步骤的**关键输出**（含投毒生效、下游行为偏移、触发执行的响应原文）。
- 每步骤的**截图**（访问证明，含目标标识与时间戳）。
- **投毒前后对照**证据（产物/输出 before/after）。
- **下游模型行为影响取证**（输出/检索差异，含 AI 交互日志 §6.3）。
- `ai_vector.txt` flag 的「面板提交 + 截图」双通道一致。
- 上述每步证据统一通过共享工具 `tools/collect_evidence.py` 产出（对齐 §质量门），保证三件套/五件套结构稳定、与 `report-exam` 的 Attack Walkthrough 兼容、并可由 CI 校验。

## 校验标准

- 攻击过程可被技术读者 **copy/paste 逐步复现**（§6.1）。
- 证据结构与 `report-exam` 的 Attack Walkthrough 小节直接兼容，可**无损复用**，无需二次整理。
- 每步骤满足「命令 + 输出 + 截图」三件套；术语符合 `GLOSSARY.md`（用「AI向量机」「供应链」「投毒」等规范词，禁用 `_Avoid_` 废弃术语）。

## 失败与豁免

- 若目标无可用供应链面，记录判定依据后改走 `attack-rag` / `attack-embeddings`，不阻塞其余路径。
- 若投毒仅部分生效（触发率低），如实记录命中率，不得夸大。
- 若恶意依赖被签名校验/护栏拦截，记录拦截行为与原因，评估改走其它路径；不反复重试同一被拦截动作。
- 若目标为疑似诱饵机（0 分、无 AI 供应链面），记录判定依据后 ≤30 分钟内结束，不在 0 分主机空耗。
