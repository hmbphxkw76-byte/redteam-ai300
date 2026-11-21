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

先以**被动信号**（响应头、部署配置、前端产物、SSE 元数据）定位 AI 入口；仅在 `--profile active` 追加定向端口枚举（≤8，禁全端口扫描），再逐类隐蔽枚举下列 7 类组件，每类独立 step_id 并**经 `tools/collect_evidence.py` 产出「确切命令 + 关键输出 + 截图」三件套（含五件套校验表）**落盘 `loot/`，供 `report-exam` 与 CI 复用（GOVERNANCE §6 / §4.2）：

1. **LLM 引擎识别（recon-01）**：识别推理引擎（vLLM、Ollama、TGI、llama.cpp、TensorRT-LLM 等）及版本与暴露端口。
   - 证据：`python tools/collect_evidence.py --step recon-01 --out loot/recon-01-llm-engine.md --strict`
   - 命令：`curl -s <AI_ENDPOINT>/v1/models`
2. **模型服务枚举（recon-02）**：枚举端点、模型名/版本、计费与限流边界。
   - 证据：`python tools/collect_evidence.py --step recon-02 --out loot/recon-02-model-svc.md --strict`
   - 命令：`curl -s <AI_ENDPOINT>/v1/models | jq '.[].id'`
3. **RAG 库探测（recon-03）**：探测 RAG 框架/库（LangChain、LlamaIndex、Haystack 等）与检索链路痕迹（错误栈、路径、依赖）。
   - 证据：`python tools/collect_evidence.py --step recon-03 --out loot/recon-03-rag-lib.md --strict`
   - 命令：`curl -s <RAG_ENDPOINT>/<probe_path>`
4. **向量库发现（recon-04）**：发现向量库（Milvus :19530、Weaviate :8080、Qdrant :6333、Chroma、pgvector）及健康检查/接口暴露。
   - 证据：`python tools/collect_evidence.py --step recon-04 --out loot/recon-04-vector-db.md --strict`
   - 命令：`curl -s <VECTOR_ENDPOINT>/healthz`（active 档对 6333/8080/19530/8000 各一次只读 GET；全关记 ABSENT）
5. **agent 系统识别（recon-05）**：识别 agent 框架（AutoGen、CrewAI、LangGraph 等）与编排痕迹。
   - 证据：`python tools/collect_evidence.py --step recon-05 --out loot/recon-05-agent-sys.md --strict`
   - 命令：`curl -s <AGENT_ENDPOINT>/<agent_probe>`
6. **MCP·工具面发现（recon-06）**：枚举 MCP 服务、工具定义（`/tools/list`）、function-calling 面。
   - 证据：`python tools/collect_evidence.py --step recon-06 --out loot/recon-06-mcp.md --strict`
   - 命令：`curl -s -X POST <TARGET>/api/secrets/validate -H "Content-Type: application/json" -d '{"labId":"<LAB>","answer":"<单次错误答案>"}'`（被动枚举工具面；`ffuf` 仅 active 且已授权时用，禁爆破；资产按类别聚合 1 条）
7. **护栏与输入输出探测（recon-07）**：最小侵入探测输入输出、记录护栏行为，汇总至 `loot/ai-assets.md`；纯 WebSocket（Streamlit）记协议缺口 `UNDETERMINED`。
   - 证据：`python tools/collect_evidence.py --step recon-07 --out loot/recon-07-guardrail.md --strict`
   - 命令：`curl -s <AI_ENDPOINT>/v1/chat/completions -H "Content-Type: application/json" -d '{"model":"<MODEL>","messages":[{"role":"user","content":"<PROBE>"}]}'`

证据通用参数：各步另加 `--cmd` / `--shot-cmd` / `--target`；recon-07 另加 `--ai-log` 与 flag 双通道。

## 实现范围与能力边界

#### 实现范围（In scope，已实现且可执行）

- 7 步 AI 资产枚举（recon-01..recon-07），每步产出结构化证据片段 + 访问证明截图。
- 自适应发现：入口 → 应用族/基路径/版本（Streamlit/Gradio/Ollama/OpenAI/OpenAPI），只读且 ≤12 请求；未知端点不猜路径，不把「未发现」写成「存在」。
- 家族感知：Streamlit 以 `/_stcore/health` + 聊天入口取证；DVAA 以 `/health`、`/agents`、`/api/llm/status`、`/mcp/tools` 取证，回显选 `weak` api agent。
- 结构化资产清单（7 字段契约，markdown + JSON 双态）：仅 PRESENT 建资产；UNDETERMINED 记入未决面与缺口台账（类别/步骤/已试端点/依据/下一步），可被下游按资产ID复用。
- 执行分级：`passive`（默认，只读 + 一次无害回显）／`active`（追加定向端口，≤8）。
- 运行隔离：每次运行独占 `runs/<run_id>/`（run.json、片段、MANIFEST、verification、报告），双跑不覆盖；`MANIFEST` 按运行窗口校验。
- 自校验门禁 C1–C9（PNG IEND 为准）：步骤覆盖、证据新鲜度/三件套、截图、清单一致性、判定基底、七字段契约、报告结构、证据完整性、结论一致性；任一不过即退出码 1。
- 证据环节：三件套 + 脚本来源/修改说明 + 模型交互 + flag 双通道 + JSONL 清单。
- 诱饵判定与 30 分钟时间盒；失败隔离（单面失败不阻塞其余枚举，但对应门禁失败）。
- 入口：
  - `python tools/recon_ai/cli.py run --target <TARGET> [--profile passive|active]`
  - `python tools/recon_ai/cli.py verify --run <RUN_DIR>`
  - `python tools/recon_ai/cli.py inventory --path <AI_ASSETS_JSON>`
  - `python tools/recon_ai/cli.py analyze --input <OBS_JSON> [--out <ANALYSIS_JSON>]`（Ch2 旁路分析，见下）

#### 功能边界（Boundary）

1. **不执行攻击**：不构造越狱/注入利用载荷、不投毒、不做模型抽取、不提权外联（属 `attack-*` 系列）。
2. **不做爆破**：无口令猜测、无 token 枚举、无大字典并发目录扫描。
3. **不做全端口扫描**：默认被动；主动档仅定向端口清单，且上限 8 个。
4. **只读**：不调用重置端点、不变更目标状态、不上传任何内容。
5. **不落盘明文凭据**：仅记 `Bearer-<前8位哈希>` 指纹。
6. **不生成考试提交物**：PDF / `.7z` 归档与提交属 `report-exam` / `verify-evidence`；本技能只产出自身验证报告（覆盖矩阵/证据核对/缺口台账/门禁）。
7. **不深挖诱饵**：时间盒到期即降级并留痕。
8. **不推断未观测事实**：取不到版本记「不可判定」，不以产品文档替代运行时事实。
9. **不伪造截图**：无浏览器时标注「截图待补录」并使 C4 门禁失败（退出码 1），不得以占位图充数。

**准入前提**：仅限已授权目标；未获授权时只允许被动分级。

## 模块职责划分

| 模块 | 单一职责 | 公开接口 |
|---|---|---|
| `model` | 领域类型与契约字段的唯一定义处 | `Existence`／`Category`／`ProbeResult`／`Asset`／`AssetInventory`／`ASSET_FIELDS` |
| `transport` | 唯一网络出口（传输 seam） | `Transport`／`UrllibTransport`／`FakeTransport` |
| `fingerprint` | 响应签名 → 产品/版本/类别 | `detect`／`primary`／`signature_summary` |
| `probes` | 7 步声明式探测（请求 + 解析 + 判据） | `STEP_SPECS`／`JUDGES`／`find`／`parse_sse` |
| `shot` | 访问证明截图（`url` 直截 / `transcript` 转录页） | `ShotCapture`／`HeadlessShot`／`make_shot` |
| `evidence` | 证据落盘，委托共享收集器（UTF-8 双向固定） | `EvidenceWriter.emit`／`load_manifest` |
| `policy` | 分级门控、诱饵判定、时间盒、失败隔离 | `gate_requests`／`judge_decoy`／`FailureBudget` |
| `discovery` | 入口 → 应用族/基路径/版本，追加类端点证据 | `discover`／`DiscoveryPlan` |
| `inventory` | 判据 → 七字段清单 + 未决面/缺口台账 | `build` |
| `verifier` | 运行自校验 C1–C9（只读实跑产物） | `verify_run`／`finalize`／`write_verification` |
| `runner` | 编排：发现 → 执行 → 证据 → 清单 → 门禁 → 报告 | `run_recon` |
| `cli` | 命令行入口、门禁退出码语义 | `main` |
| `ch2` | Ch2 旁路分析（离线，零网络） | `analyze`／`fingerprint_behavior`／`detect_canary`／`validate_analysis` |

依赖单向：`cli → runner → {discovery, probes, inventory, evidence, policy, verifier, shot} → {transport, fingerprint, model}`，无环；`ch2` 为离线旁路，不入依赖链。设计见 `docs/operations/recon-ai-closed-loop-design.md`。

## 证据环节（对齐官方规范）

每步证据片段与官方文档要求逐条对应：

| 官方要求（S1/S3 §1、§2） | 片段落点 |
|---|---|
| 确切命令，可 copy/paste 复现 | 「确切命令」（bash 围栏，完整 `curl` 与请求体） |
| 相关控制台输出 | 「关键输出」（原始响应，超长截断注明留存） |
| 脚本/exploit 来源或副本 + 修改说明 | 「脚本 / PoC」（副本 sha256 / 来源 URL / 修改说明） |
| 每阶段截图 | 「截图（访问证明）」（`url` 直截或 `transcript`，标注类型） |
| 模型交互入正文（§6.3） | 「AI 交互日志」（通道 / 模型 / 提示 / 输出 / 采纳） |
| flag 面板 + 截图双通道一致 | 「flag 取证（双通道一致）」（分记两值判定一致性） |
| 分析结论不与原始证据混淆 | 「分析注记」（判定 + 依据，独立于原始输出） |

**证据清单**（`MANIFEST.jsonl`）逐行登记 `step_id`／`command`／`sha256`／`timestamp`／`profile`／`retention`／`pieces`／`screenshot_sha256`／`flag_dual`，供报告与复核独立消费。

## OPSEC 隐蔽纪律

遵守「被动优先、低频低噪、不写盘凭据」，避免触发 IDS / 暴露红队：

- **被动优先**：响应头、TLS、自检端点等被动信号先于端口扫描。
- **低频低噪**：节奏贴近业务波动，禁全端口高速扫描与批量爆破。
- **不写盘凭据明文**：仅记 `Bearer-<前8位哈希>` 线索指纹。

## Ch2 对齐旁路分析（离线）

覆盖 Ch2 §2.1–2.4 中 7 步枚举未含的**行为级侦察**：`tools/recon_ai/ch2.py`，零网络、只读观测、不改 C1–C9。触发：判读响应头/健康端点/模型行为/RAG sources/端点状态/仓库工件/MCP·A2A schema/metadata/前端 JS/检索阈值序列/防御日志时。执行：`observations` JSON → `cli.py analyze --input <OBS_JSON> [--out <ANALYSIS_JSON>]`。输出与校验（拒绝无依据结论/明文凭据/无交叉家族/单样本阈值）见 `docs/operations/recon-ai-ch2-analysis.md`。

## 质量门

每步**确切命令**、**关键输出**、**截图**与结构化资产清单必须齐全；统一经 `tools/collect_evidence.py` 产出（GOVERNANCE 质量门），缺失任一即未过门禁。

## 校验标准

- 资产清单可被 `loot-manage` 与 `attack-ai-agent` / `attack-rag` / `attack-mcp-tool` 等**按资产ID复用**，无需二次枚举。
- 枚举过程可被 **copy/paste 复现**；术语符合 `GLOSSARY.md`，禁用 `_Avoid_` 废弃术语。
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
- 若探测行为被防护系统记录或触发告警（探测暴露），立即中止该面探测、记录暴露点与时间窗，转入被动观测，不反复重试同一动作。
