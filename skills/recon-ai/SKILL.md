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

先以**被动信号**（响应头、部署配置、前端产物、SSE 元数据）定位 AI 入口；仅 `--profile active` 追加定向端口（≤8，禁全扫描），再逐类隐蔽枚举 7 类组件，每类独立 step_id 并经 `tools/collect_evidence.py` 产出「命令+输出+截图」三件套（含五件套表）落盘 `loot/`，供 `report-exam`/CI 复用（GOVERNANCE §6/§4.2）：

1. **LLM 引擎识别（recon-01）**：识别 LLM 推理引擎（vLLM、Ollama、TGI、llama.cpp、TensorRT-LLM 等）及其版本与暴露端口。
   - 证据：`python tools/collect_evidence.py --step recon-01 --out loot/recon-01-llm-engine.md --strict`
   - 命令：`curl -s <AI_ENDPOINT>/v1/models`
2. **模型服务枚举（recon-02）**：枚举模型服务端点、可用模型名与版本、计费/限流边界。
   - 证据：`python tools/collect_evidence.py --step recon-02 --out loot/recon-02-model-svc.md --strict`
   - 命令：`curl -s <AI_ENDPOINT>/v1/models | jq '.[].id'`
3. **RAG 库探测（recon-03）**：探测 RAG 框架/库（LangChain、LlamaIndex、Haystack 等）与检索链路痕迹（错误栈、特有路径、依赖特征）。
   - 证据：`python tools/collect_evidence.py --step recon-03 --out loot/recon-03-rag-lib.md --strict`
   - 命令：`curl -s <RAG_ENDPOINT>/<probe_path>`
4. **向量库发现（recon-04）**：发现向量数据库（Milvus :19530、Weaviate :8080、Qdrant :6333、Chroma、pgvector）及其健康检查/接口暴露。
   - 证据：`python tools/collect_evidence.py --step recon-04 --out loot/recon-04-vector-db.md --strict`
   - 命令：`curl -s <VECTOR_ENDPOINT>/healthz`（active 档对 6333/8080/19530/8000 各一次只读 GET；全关记 ABSENT）
5. **agent 系统识别（recon-05）**：识别 agent 框架（AutoGen、CrewAI、LangGraph 等）与编排/多智能体痕迹；A2A 命中时补录协议信息，不新增 step_id。
   - 证据：`python tools/collect_evidence.py --step recon-05 --out loot/recon-05-agent-sys.md --strict`
   - 命令：`curl -s <AGENT_ENDPOINT>/<agent_probe>`
   - A2A 补录（沿用 recon-05）：`curl -s <EP>/.well-known/agent.json | jq '{name,description,url,protocolVersion,capabilities,skills,securitySchemes}'`；`curl -s <EP>/openapi.json | jq '.paths|keys'` + `/a2a/workflow` schema `$ref`；`curl -s <EP>/agents` + `/agents/deregister`。记 skills/tags、注册/注销端点；基线见 `attack-multi-agent` a2a-01。null/404 记 `ABSENT`，超限按 `policy` 降级。
6. **MCP·工具面发现（recon-06）**：枚举 MCP 服务、工具定义（`/tools/list`）、function-calling 面与身份边界。
   - 证据：`python tools/collect_evidence.py --step recon-06 --out loot/recon-06-mcp.md --strict`
   - 命令：`curl -s -X POST <TARGET>/api/secrets/validate -H "Content-Type: application/json" -d '{"labId":"<LAB>","answer":"<单次错误答案>"}'`（被动枚举工具面与校验语义；字典扫描 `ffuf` 仅可在 `--profile active` 且已授权时使用，禁止爆破；多 MCP 端口逐端口汇总，资产按类别聚合 1 条）
7. **护栏与输入输出探测（recon-07）**：对发现的 AI 入口做最小侵入的输入/输出探测，记录护栏行为，并汇总以上结果至 `loot/ai-assets.md`；纯 WebSocket 会话（Streamlit）记协议缺口 `UNDETERMINED`。
   - 证据：`python tools/collect_evidence.py --step recon-07 --out loot/recon-07-guardrail.md --strict`
   - 命令：`curl -s <AI_ENDPOINT>/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"<MODEL>","messages":[{"role":"user","content":"<PROBE>"}]}'`
   - A2A 检测面基线（C5/§4.2）：授权可见 SIEM 时仅记规则名/触发（注册、DNS、hosts、`xp_cmdshell`、跳步、Unicode）；不改规则、不转抄正文，只写路径引用；不可访问记 `UNDETERMINED`。

证据通用参数：所有调用另加 `--cmd "<上方命令>" --shot-cmd "screenshot --region <REGION>" --target <TARGET>`；recon-07 另加 `--ai-log` 与 flag 双通道。

## 实现范围与能力边界

#### 实现范围（In scope，已实现且可执行）

- 7 步 AI 资产枚举（recon-01..recon-07），每步产出结构化证据片段 + 访问证明截图。
- 自适应发现：入口→应用族/基路径/版本（Streamlit/Gradio/Ollama/OpenAI/OpenAPI），请求≤12且只读；未知端点不猜路径，「未发现」不写「存在」。
- 家族感知：Streamlit 以 `/_stcore/health` + 聊天入口（按钮/iframe）取证；DVAA 以 `/health`、
  `/agents`、`/api/llm/status`、`/mcp/tools` 取证，回显选 `weak` api agent。
- 结构化清单（7 字段，markdown+JSON）：仅 PRESENT 建资产；UNDETERMINED 入缺口台账（类别/步骤/端点/依据/下一步），供下游按资产ID复用。
- 执行分级：`passive`（默认，只读 + 一次无害回显）／`active`（追加定向端口，≤8）。
- 运行隔离：`runs/<run_id>/` 独占（run.json/片段/MANIFEST/verification/报告），双跑不覆盖；MANIFEST 按窗口校验。
- 自校验门禁 C1–C9（PNG IEND）：覆盖、新鲜度/三件套、截图、清单一致、判定基底、七字段契约、报告结构、证据完整、结论一致；任一不过退出码 1，结论不由模板常量决定。
- 证据环节：三件套 + 脚本来源/修改说明 + 模型交互 + flag 双通道 + JSONL 清单。
- 诱饵判定与 30 分钟时间盒；失败隔离（单面失败不阻塞其余枚举，但对应门禁失败）。
- 入口：
  - `python tools/recon_ai/cli.py run --target <TARGET> [--profile passive|active]`
  - `python tools/recon_ai/cli.py verify --run <RUN_DIR>`
  - `python tools/recon_ai/cli.py inventory --path <AI_ASSETS_JSON>`

#### 功能边界（Boundary）

1. **不执行攻击**：不构造越狱/注入利用载荷、不投毒、不做模型抽取、不提权外联（属 `attack-*` 系列）。
2. **不做爆破**：无口令猜测、无 token 枚举、无大字典并发目录扫描。
3. **不做全端口扫描**：默认被动；主动档仅定向端口清单，且上限 8 个。
4. **只读**：不调用重置端点、不变更目标状态、不上传任何内容。
5. **不落盘明文凭据**：仅记 `Bearer-<前8位哈希>` 指纹。
6. **不生成提交物**：PDF/`.7z` 与提交属 `report-exam`/`verify-evidence`；本技能只产自身验证报告（覆盖矩阵/证据核对/缺口台账/门禁）。
7. **不深挖诱饵**：时间盒到期即降级并留痕。
8. **不推断未观测事实**：取不到版本记「不可判定」，不以产品文档替代运行时事实。
9. **不伪造截图**：无浏览器标「截图待补录」并使 C4 失败（退出码 1），不得占位图充数。
10. **garak 偏离**：未接入首扫（V4，见 `docs/operations/a2a-ch4-mainline-design.md`）。

**准入前提**：仅限已授权目标；未获授权时只允许被动分级。

## 模块职责划分

| 模块 | 单一职责 | 公开接口 |
|---|---|---|
| `model` | 领域类型与契约字段 | `Existence/Category/ProbeResult/Asset/AssetInventory/ASSET_FIELDS` |
| `transport` | 唯一网络出口（seam） | `Transport/UrllibTransport/FakeTransport` |
| `fingerprint` | 响应签名→产品/版本/类别 | `detect/primary/signature_summary` |
| `probes` | 7 步声明式探测 | `STEP_SPECS/JUDGES/find/parse_sse` |
| `shot` | 访问证明截图 | `ShotCapture/HeadlessShot/make_shot` |
| `evidence` | 证据落盘（UTF-8 固定） | `EvidenceWriter.emit/load_manifest` |
| `policy` | 分级/诱饵/时间盒/失败隔离 | `gate_requests/judge_decoy/FailureBudget` |
| `discovery` | 入口→应用族/基路径/版本 | `discover/DiscoveryPlan` |
| `inventory` | 判据→七字段清单+缺口台账 | `build` |
| `verifier` | 自校验 C1–C9（只读产物） | `verify_run/finalize/write_verification` |
| `runner` | 编排：发现→证据→清单→门禁→报告 | `run_recon` |
| `cli` | 命令行入口/门禁退出码 | `main` |

依赖单向：`cli→runner→{discovery,probes,inventory,evidence,policy,verifier,shot}→{transport,fingerprint,model}`，无环。设计见 `docs/operations/recon-ai-closed-loop-design.md`。

## 证据环节（对齐官方规范）

每步证据片段与官方文档要求逐条对应：

| 官方要求（S1/S3 §1、§2） | 片段落点 |
|---|---|
| 确切命令可复现 | 「确切命令」小节（bash 围栏，完整 `curl`/请求体） |
| 控制台输出 | 「关键输出」小节（原始响应，超长截断注明留存入径） |
| 脚本来源+修改说明 | 「脚本 / PoC」小节（sha256/来源 URL/修改说明；无脚本显式声明） |
| 每阶段截图 | 「截图（访问证明）」小节（`url` 直截或 `transcript` 渲染，标注类型） |
| 模型交互入正文（§6.3） | 「AI 交互日志」小节（通道/模型/提示/输出/采纳） |
| flag 双通道（§2） | 「flag 取证（双通道一致）」小节（分记两值并判一致） |
| 分析不与证据混淆 | 「分析注记」小节（判定+依据，独立于原始输出） |

**证据清单**（`MANIFEST.jsonl`）逐行记 `step_id`/`command`/`sha256`/`timestamp`/`profile`/`retention`/`pieces`，另附 `screenshot_sha256`/`flag_dual`，供报告与复核独立消费，不依赖会话上下文。

## OPSEC 隐蔽纪律

枚举全程遵守「被动优先、低频低噪、不写盘凭据」三原则，避免触发 IDS / 暴露红队存在：

- **被动优先**：响应头/TLS/自检端点先于端口扫描。
- **低频低噪**：贴近业务波动，禁全端口高速扫描与批量爆破。
- **不写盘凭据明文**：仅记 `Bearer-<前8位哈希>` 指纹。

## 质量门

每步**确切命令**、**关键输出**、**截图**与结构化资产清单必须齐全；统一经
`tools/collect_evidence.py` 产出（对齐 GOVERNANCE 质量门），缺失任一即未过门禁。

A2A 命中时 recon-05 须含 Card/OpenAPI/注册端点与 `ABSENT`，recon-07 须含检测基线或 `UNDETERMINED`；不新增 step_id、不改七字段契约。

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

- 若目标为疑似诱饵机（0 分、无 AI 组件），记录依据后降级轻量枚举，≤30 分钟结束。
- 若某 AI 组件无法指纹识别，记录「无法识别」及原因，不阻塞其余枚举。
- A2A Card 不可达或返回非协议 JSON 记 `ABSENT` 并留原始响应；SIEM 不可读记 `UNDETERMINED`，均不阻塞其余枚举。
- 探测暴露时立即中止该面、记录暴露点与时间窗，转被动观测，不重试同一动作。
