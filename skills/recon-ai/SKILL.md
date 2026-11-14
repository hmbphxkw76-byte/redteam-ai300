---
name: recon-ai
priority: P0
domain: D2
scoring_unit: 通用
trigger: 对目标环境发起红队前，需定位 AI 资产与攻击面
input: 目标网段/入口、已知主机与凭据（可选）
output: 结构化 AI 资产清单（组件、暴露面、依赖、证据）
---

# recon-ai — AI 资产侦察与枚举

## 执行体

先以**被动信号**（响应头、部署配置、前端产物、SSE 元数据）定位暴露的 AI 入口；仅在 `--profile active` 下追加定向端口枚举（`nmap -sV -p <定向端口清单> <TARGET>`，端口数 ≤8，禁止全端口扫描），再**逐类隐蔽枚举下列 7 类 AI 组件**，每类分配独立 step_id 并**经 `tools/collect_evidence.py` 产出「确切命令 + 关键输出 + 截图」三件套证据（含五件套校验表）**，落盘至 `loot/`，供 `report-exam` 与 CI 复用（对齐 GOVERNANCE §6 / §4.2 质量门）：

1. **LLM 引擎识别（recon-01）**：识别 LLM 推理引擎（vLLM、Ollama、TGI、llama.cpp、TensorRT-LLM 等）及其版本与暴露端口。
   - 命令：`curl -s <AI_ENDPOINT>/v1/models`
   - 证据：`python tools/collect_evidence.py --step recon-01 --cmd "curl -s <AI_ENDPOINT>/v1/models" --out loot/recon-01-llm-engine.md --shot-cmd "screenshot --region model_list" --target <AI_ENDPOINT> --strict`
2. **模型服务枚举（recon-02）**：枚举模型服务端点、可用模型名与版本、计费/限流边界。
   - 命令：`curl -s <AI_ENDPOINT>/v1/models | jq '.[].id'`
   - 证据：`python tools/collect_evidence.py --step recon-02 --cmd "curl -s <AI_ENDPOINT>/v1/models | jq '.[].id'" --out loot/recon-02-model-svc.md --shot-cmd "screenshot --region model_ids" --target <AI_ENDPOINT> --strict`
3. **RAG 库探测（recon-03）**：探测 RAG 框架/库（LangChain、LlamaIndex、Haystack 等）与检索链路痕迹（错误栈、特有路径、依赖特征）。
   - 命令：`curl -s <RAG_ENDPOINT>/<probe_path>`
   - 证据：`python tools/collect_evidence.py --step recon-03 --cmd "curl -s <RAG_ENDPOINT>/<probe_path>" --out loot/recon-03-rag-lib.md --shot-cmd "screenshot --region rag_probe" --target <RAG_ENDPOINT> --strict`
4. **向量库发现（recon-04）**：发现向量数据库（Milvus :19530、Weaviate :8080、Qdrant :6333、Chroma、pgvector）及其健康检查/接口暴露。
   - 命令：`curl -s <VECTOR_ENDPOINT>/healthz`
   - 证据：`python tools/collect_evidence.py --step recon-04 --cmd "curl -s <VECTOR_ENDPOINT>/healthz" --out loot/recon-04-vector-db.md --shot-cmd "screenshot --region vector_health" --target <VECTOR_ENDPOINT> --strict`
5. **agent 系统识别（recon-05）**：识别 agent 框架（AutoGen、CrewAI、LangGraph 等）与编排/多智能体痕迹。
   - 命令：`curl -s <AGENT_ENDPOINT>/<agent_probe>`
   - 证据：`python tools/collect_evidence.py --step recon-05 --cmd "curl -s <AGENT_ENDPOINT>/<agent_probe>" --out loot/recon-05-agent-sys.md --shot-cmd "screenshot --region agent_probe" --target <AGENT_ENDPOINT> --strict`
6. **MCP·工具面发现（recon-06）**：枚举 MCP 服务、工具定义（`/tools/list`）、function-calling 面与身份边界。
   - 命令：`curl -s -X POST <TARGET>/api/secrets/validate -H "Content-Type: application/json" -d '{"labId":"<LAB>","answer":"<单次错误答案>"}'`（被动枚举工具面与校验语义；字典扫描 `ffuf` 仅可在 `--profile active` 且已授权时使用，禁止爆破）
   - 证据：`python tools/collect_evidence.py --step recon-06 --cmd "curl -s <TARGET>/api/secrets/validate -d '<PROBE>'" --out loot/recon-06-mcp.md --shot-cmd "screenshot --region mcp_probe" --target <TARGET> --strict`
7. **护栏与输入输出探测（recon-07）**：对发现的 AI 入口做最小侵入的输入/输出探测，记录护栏行为，并汇总以上结果至 `loot/ai-assets.md`。
   - 命令：`curl -s <AI_ENDPOINT>/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"<MODEL>","messages":[{"role":"user","content":"<PROBE>"}]}'`
   - 证据：`python tools/collect_evidence.py --step recon-07 --cmd "curl -s <AI_ENDPOINT>/v1/chat/completions -d '<PROBE>'" --out loot/recon-07-guardrail.md --shot-cmd "screenshot --region chat_response" --ai-log "见 loot/recon-07-guardrail.md" --flag "AI-ASSETS-<ENGAGEMENT>-<DATE>" --target <AI_ENDPOINT> --strict`

## 实现范围与能力边界

#### 实现范围（In scope，已实现且可执行）

- 7 步 AI 资产枚举（recon-01..recon-07），每步产出结构化证据片段 + 访问证明截图。
- 结构化资产清单（7 字段契约，markdown + JSON 双态），可被下游技能按资产ID直接复用。
- 执行分级：`passive`（默认，无状态变更的读 + 一次无害回显）／`active`（追加定向端口探测，上限 8 个）。
- 证据环节：三件套 + 脚本来源与修改说明 + 模型交互留痕 + flag 双通道 + JSONL 证据清单。
- 诱饵判定与 30 分钟时间盒；失败隔离（单面失败不阻塞其余枚举）。
- 入口：`python tools/recon_ai/cli.py run --target <TARGET> [--profile passive|active]`。

#### 功能边界（Boundary）

1. **不执行攻击**：不构造越狱/注入利用载荷、不投毒、不做模型抽取、不提权外联（属 `attack-*` 系列）。
2. **不做爆破**：无口令猜测、无 token 枚举、无大字典并发目录扫描。
3. **不做全端口扫描**：默认被动；主动档仅定向端口清单，且上限 8 个。
4. **只读**：不调用重置端点、不变更目标状态、不上传任何内容。
5. **不落盘明文凭据**：仅记 `Bearer-<前8位哈希>` 指纹。
6. **不生成报告与提交物**：PDF / `.7z` 命名归档属 `report-exam` 与 `verify-evidence`。
7. **不深挖诱饵**：时间盒到期即降级为轻量枚举并记录判定依据。
8. **不推断未观测事实**：取不到版本记「不可判定」，不以产品文档替代运行时事实。

**准入前提**：仅限已授权目标；未获授权时只允许被动分级。

## 模块职责划分

| 模块 | 单一职责 | 公开接口 |
|---|---|---|
| `model` | 领域类型与契约字段的唯一定义处 | `Existence`／`Category`／`ProbeResult`／`Asset`／`AssetInventory`／`ASSET_FIELDS` |
| `transport` | 唯一网络出口（传输 seam） | `Transport`／`UrllibTransport`／`FakeTransport` |
| `fingerprint` | 响应签名 → 产品/版本/类别 | `detect`／`primary`／`signature_summary` |
| `probes` | 7 步声明式探测（请求 + 解析 + 判据） | `STEP_SPECS`／`JUDGES`／`find`／`parse_sse` |
| `shot` | 访问证明截图（`url` 直截 / `transcript` 转录页） | `ShotCapture`／`HeadlessShot`／`make_shot` |
| `evidence` | 证据落盘，委托共享收集器 | `EvidenceWriter.emit`／`load_manifest` |
| `policy` | 分级门控、诱饵判定、时间盒、失败隔离 | `gate_requests`／`judge_decoy`／`FailureBudget` |
| `inventory` | 判据 → 七字段清单 + 契约校验 | `build` |
| `runner` | 编排：执行 → 证据 → 清单 → 验证报告 | `run_recon` |
| `cli` | 命令行入口与退出码语义 | `main` |

依赖方向单向：`cli → runner → {probes, inventory, evidence, policy, shot} → {transport, fingerprint, model}`，无环。设计记录见 `docs/operations/recon-ai-design.md`。

## 证据环节（对齐官方规范）

每步证据片段与官方文档要求逐条对应：

| 官方要求（S1/S3 §1、§2） | 片段落点 |
|---|---|
| 每一步的确切命令，且可 copy/paste 复现 | 「确切命令」小节（bash 围栏，含完整 `curl` 与请求体） |
| 相关控制台输出 | 「关键输出」小节（原始响应，超长截断并注明留存入径） |
| 所用脚本/exploit 的来源链接或代码副本 + 修改说明 | 「脚本 / PoC」小节（副本 sha256 / 来源 URL / 修改说明；无脚本时显式声明） |
| 每阶段的截图 | 「截图（访问证明）」小节（`url` 直截或 `transcript` 转录页渲染，标注类型） |
| 模型交互须入正文（§6.3） | 「AI 交互日志」小节（通道 / 模型 / 提示 / 输出 / 采纳） |
| flag 面板 + 截图双通道一致（§2 失分条款） | 「flag 取证（双通道一致）」小节（分记两值并判定一致性） |
| 分析结论不与原始证据混淆 | 「分析注记」小节（判定 + 依据，独立于原始输出） |

**证据清单**（`MANIFEST.jsonl`）逐行登记：`step_id`、`command`、`sha256`、`timestamp`、`profile`、`retention`、`pieces`（各项状态），另附 `screenshot_sha256` 与 `flag_dual`，供报告组装与人工复核独立消费，不依赖会话上下文。

## OPSEC 隐蔽纪律

枚举全程遵守「被动优先、低频低噪、不写盘凭据」三原则，避免触发 IDS / 暴露红队存在：

- **被动优先**：先以 HTTP 响应头、TLS 证书、API 自检端点等被动/低侵入信号识别组件，确有必要再做端口扫描。
- **低频低噪**：探测节奏控制在目标正常业务波动内；避免全端口高速扫描、批量爆破式请求。
- **不写盘凭据明文**：口令、token 等凭证线索仅以「线索指纹」形式记入资产清单（如 `凭证线索: Bearer-<前8位哈希>`），绝不将明文凭据落盘。

## 质量门

以下证据**必须**全部产出，缺失任一即判定未过门禁，不得进入后续技能：

- 每个枚举步骤的**确切命令**。
- 每个步骤的**关键输出**（含版本/端点/组件指纹）。
- 每个步骤的**截图**（访问证明）。
- 结构化资产清单（含每项的证据引用）。
- 上述每步证据统一通过共享工具 `tools/collect_evidence.py` 产出（对齐 GOVERNANCE §质量门），保证三件套结构稳定、与 `report-exam` 兼容、并可由 CI 校验。

## 校验标准

- 资产清单可被 `loot-manage` 与后续攻击技能（`attack-ai-agent` / `attack-rag` / `attack-mcp-tool` 等）**按资产ID直接复用**，无需二次枚举。
- 枚举过程可被技术读者 **copy/paste 复现**。
- 术语符合 `GLOSSARY.md`（使用「诱饵机」「AI 向量」「检索操纵」等规范词，禁用 `_Avoid_` 废弃术语）。
- **资产清单契约**（决策级 schema，每条资产含以下字段，供后续技能程序化引用）：

  | 字段 | 含义 |
  |---|---|
  | 资产ID | 稳定唯一标识，如 `ai-llm-<host>-01` |
  | 组件类别 | LLM引擎 / 模型服务 / RAG库 / 向量库 / agent系统 / MCP工具面 / 护栏 |
  | 产品/引擎 | 具体产品与引擎（vLLM、Milvus、LangChain…） |
  | 版本 | 识别到的版本或版本区间 |
  | 暴露端点/端口 | 可访问的 URL / host:port |
  | 凭证线索 | 仅记线索指纹（如 `Bearer-<前8位哈希>`），**不落盘明文** |
  | 关联证据片段 step_id | 对应 recon-0x 的证据文件（如 `loot/recon-03-rag-lib.md`） |

## 失败与豁免

- 若目标为疑似诱饵机（0 分、无 AI 组件），记录判定依据后降级为轻量枚举，≤30 分钟内结束，不在 0 分主机空耗。
- 若某 AI 组件无法指纹识别，记录「无法识别」及原因，不阻塞其余枚举。
- 若探测行为被防护系统记录或触发告警（探测暴露），立即中止该面探测、记录暴露点与时间窗，转入被动观测，不反复重试同一动作。
