# recon-ai 实现事实索引

> **版本** v1.0 · **状态** 已核实 · **性质** recon-ai 单一可信源
> **取证日期** 2026-11-14（GMT+8）· **取证方式** 官方项目页 + 演练目标一手探针（命令与输出逐条留痕）
> **上游** [`skills/recon-ai/SKILL.md`](../../skills/recon-ai/SKILL.md) · **治理** `GOVERNANCE.md` §4.2 / §6 · **流程** `docs/operations/skill-mainline-workflow.md` §3.1
> **职责边界** 本文件只记录「实现所依赖的事实」，不定义流程、不复制宪法条款。

---

## 0. 结论摘要

1. 演练目标 `http://192.168.40.189` 是 **OWASP AIVP（AI Vulnerabilities Playground，Incubator 项目）** 的部署实例：前端 React/Vite SPA + `nginx/1.27.5` 反代 + FastAPI（SSE 流式）+ 可替换模型后端。
2. 该部署**不存在** OpenAI 兼容 `/v1/models`。任何未匹配路径均由 SPA 回退返回 `200 text/html`，因此**「HTTP 200」不能作为资产存在判据**——这是 recon-ai 必须内建的判据前提（§2 F-3）。
3. 真实 AI 资产面 = **4 个 phase / 55 个 lab** 的 HTTP 面 + 3 个仅见于前端 bundle 的 API（`/api/config`、`/api/me/runs`、`/api/secrets/validate`）。
4. 该部署的默认模型为 `LongCat-2.5`，与 AIVP 上游文档的 `llama3.1` 基线不同 → **产品基线 ≠ 部署事实**，指纹必须来自运行时响应而非产品文档。
5. 全部安全响应头缺失（CSP / X-Frame-Options / X-Content-Type-Options / HSTS / Referrer-Policy）→ 护栏面（recon-07）有可判定依据。
6. recon 阶段**不需要** PyRIT 攻击对象：唯一需要的评分能力是确定性 `SubStringScorer`；若 recon-07 需对抗性探针则用 `PromptSendingAttack`（B7 合规映射见 §4）。

---

## 1. 已核实清单（一手源逐条）

| # | 事实 | 来源（URL / 命令） | 输出摘要 |
|---|---|---|---|
| F-1 | AIVP 是 OWASP Incubator 项目，4 phase、50+ lab，覆盖提示注入 / agentic / 工具滥用 / MCP 信任边界 | <https://owasp.org/projects/ai-vulnerabilities-playground> | 项目页明示 Incubator、4 phase、场景 1–12 与 MCP 风险 |
| F-2 | 技术栈：Ollama + LLM、FastAPI（SSE `POST /api/labs/{lab}/chat`）、React/Vite；Docker 模式为 nginx + API + Redis | 同上项目页 Requirements 段；`RUN_STEPS` 结构 | `Python 3.10+ / Node 18+ / Ollama`；`FastAPI (SSE streaming)` |
| F-3 | 演练目标存在 SPA 回退：未知路径返回 `200` + `index.html`（1702 字节），`/v1/models`、`/healthz`、`/mcp`、`/tools/list`、`/robots.txt` 均命中回退 | `curl -s -o /dev/null -w "%{http_code} %{size_download}" http://192.168.40.189/v1/models` | `200 1702`，`Content-Type: text/html` |
| F-4 | API 段返回 FastAPI 风格 JSON 404（22 字节 `{"detail":"Not Found"}`）；缺字段返 422 带 `loc`/`msg` → 后端为 FastAPI + Pydantic | `curl -s http://192.168.40.189/api/labs`；`curl -s -X POST -d '{"token":"probe"}' /api/secrets/validate` | `{"detail":"Not Found"}`；`422` + `missing/labId`、`missing/answer` |
| F-5 | `/api/config` 泄露部署配置：默认模型、训练 lab 白名单、artifact 回放白名单 | `curl -s http://192.168.40.189/api/config` | `{"training_labs_enabled":false,"training_lab_ids":["MM_05","MM_04","MM_07"],"artifact_replay_labs":[...],"llm_model_default":"LongCat-2.5"}` |
| F-6 | 会话面存在且可匿名建立：SSE 响应下发 `aivp_sid`（HttpOnly / 30 天 / SameSite=lax） | `curl -D - -X POST /api/labs/MM_04/chat -d '{"prompt":"..."}'` | `set-cookie: aivp_sid=<uuid>; HttpOnly; Max-Age=2592000; Path=/; SameSite=lax` |
| F-7 | `/api/me/runs` 为运行遥测面，匿名可读，当前空 | `curl -s "http://192.168.40.189/api/me/runs?limit=1"` | `{"runs":[]}` |
| F-8 | `/api/secrets/validate` 为「labId + answer」校验预言机（MCP/secret 类 lab 的验证入口） | 同 F-4 的 422 载荷 | `loc:["body","labId"]`、`loc:["body","answer"]` |
| F-9 | `/api/labs/{id}/summary` 需 `request_id`（缺参 422）；`/api/labs/{id}/compare` 仅 POST（GET 405）；`OPTIONS /api/config` 405 | `curl -o /dev/null -w "%{http_code}"` 三次 | `422` / `405` / `405` |
| F-10 | SSE 事件结构：`event: meta`（`request_id`、`lab_id`、`phase`、`control_mode`、`artifact_replay`）+ 默认事件 `data:{"content":...}` 分片 + `mcp_result` | `curl -s -N -X POST /api/labs/MM_04/chat` | `event: meta` → `{"request_id":"…","lab_id":"MM_04","phase":3,"control_mode":"off","artifact_replay":true}`；随后 `data:{"content":"RE"}`… |
| F-11 | 前端 bundle 静态目录：PI 10 + DE 15 + MM 15 + MCP 15 = **55 个 lab**，phase 与前缀一一对应 | `curl -s /assets/index-BtcwQhVS.js` → 正则 `\{id:"[A-Z]{2}_\d{2}"` | `PI_01..PI_10`、`DE_01..DE_15`、`MM_01..MM_15`、`MCP_01..MCP_15` |
| F-12 | API base 为 `/api`（bundle 内 `kn="/api"`），对外暴露 6 条路径（§3 表） | 同 F-11 提取 `${kn}/…` | `config`、`labs/{id}/chat`、`labs/{id}/compare`、`labs/{id}/summary`、`me/runs`、`secrets/validate` |
| F-13 | 安全响应头全缺：无 CSP / X-Frame-Options / X-Content-Type-Options / HSTS / Referrer-Policy | `curl -s -D - -o /dev/null /explore \| grep -iE "content-security\|x-frame\|…"` | 仅 `Server: nginx/1.27.5` 命中 |
| F-14 | PyRIT 版本与对象图：`pyrit==1.1.0`；攻击策略为 `pyrit.executor.attack` 下 `*Attack`；`SubStringScorer` 在 `pyrit.score` | `docs/research/pyrit-canonical-references.md` §1/§3（一手源已核） | 版本锁定 1.1.0；`pyrit.orchestrator` 已删除 |
| F-15 | 官方文档要求：每步「命令 + 输出 + 代码/脚本或其来源与修改说明 + 截图」，须可 copy/paste 复现；flag 须「控制面板 + 截图」双通道 | S3 快照 §1 / §2 / §4；`GOVERNANCE.md` §6.1 / §6.2 | 见 `docs/governance/references/OSAI-Exam-Guide-snapshot.md` §1、§4 |

---

## 2. 对实现构成硬约束的判定

| 编号 | 判定 | 依据 | 对规格的传导 |
|---|---|---|---|
| D-1 | 资产存在性判据 = 「状态码 + Content-Type + 响应体指纹」三元组，缺一不成立 | F-3 | probe 结果必须携带 `exists` 三值（存在 / 不存在 / 不可判定），禁止用 200 直接判定 |
| D-2 | 指纹来源必须是运行时响应，不得引用产品文档作为版本/模型依据 | F-5 vs F-1（LongCat-2.5 ≠ llama3.1） | 指纹规则表以「响应签名」为中心，规则命中需保留命中片段 |
| D-3 | 被动优先：先取 `/api/config`、响应头、bundle、SSE meta；端口扫描仅在被动信号不足且授权窗口内执行 | SKILL.md OPSEC + F-5/F-13 | 执行体默认 `--profile passive`；`active` 需显式开关 |
| D-4 | `recon-07` 只做最小侵入探针（无害回显 + 拒答观察），不得发起越狱/载荷 | SKILL.md 质量门与失败豁免 | 探针载荷固定为回显串，评分用确定性 `SubStringScorer` |
| D-5 | 证据片段须承载「脚本/工具来源 + 修改说明」，现有三件套不覆盖该官方要求 | F-15 | 证据环节必须扩展，否则 recon-01..07 的产物不足以支撑报告 |

---

## 3. 攻击路径 → 探测面 → 对象映射（SKILL.md 七步全覆盖）

| step | 攻击路径（SKILL.md） | 本部署对应探测面（一手源） | 判据 | PyRIT 对象映射 |
|---|---|---|---|---|
| recon-01 | LLM 引擎识别 | `/api/config`（`llm_model_default`）+ SSE `meta` + `Server` 头 | 模型名与引擎族可命名 | 无攻击对象；证据为 HTTP 响应 |
| recon-02 | 模型服务枚举 | `/api/labs/{id}/chat`（SSE 分片、`request_id`）+ `training_lab_ids` | 服务端点数、模型名、会话面 | `HTTPTarget`（chat，SSE 回调） |
| recon-03 | RAG 库探测 | `DE_10 RAG Exploitation` lab + bundle 字符串 `retrieved/documents/knowledge/retrieval` | 检索链路痕迹可举证 | `HTTPTarget`（lab 面） |
| recon-04 | 向量库发现 | 无独立向量端口暴露（被动面）；lab 级向量面见 `DE_10`/`MM_05` | 存在 / 不存在 / 不可判定 三值 | 无（负结果亦须留证） |
| recon-05 | agent 系统识别 | `DE_01..DE_15` agentic phase + `/api/me/runs` 遥测 + `mcpTelemetry` | 编排/多智能体痕迹 | `HTTPTarget`（lab 面） |
| recon-06 | MCP·工具面 | `MCP_01..MCP_15` + `/api/secrets/validate` + bundle `tools` 定义 | 工具面无鉴权即可枚举 | `HTTPTarget`（`/api/secrets/validate`） |
| recon-07 | 护栏与 I/O 探测 | 无害回显探针（F-10）+ 缺失安全响应头（F-13）+ `control_mode` | 护栏行为可描述、可复现 | `PromptSendingAttack` + `SubStringScorer`（仅对抗性探针时） |

**B7 合规**：全部对象取自 `pyrit.executor.attack` / `pyrit.prompt_target` / `pyrit.score`；不使用 `pyrit.orchestrator`、`*Orchestrator`、`AzureOpenAIChatTarget`、`XpiaAttack`。

---

## 4. 待核实（核实闸，逐条带取证方式）

| 闸 | 待核实项 | 取证方式 | 阻塞面 |
|---|---|---|---|
| R-1 | 55 个 lab 是否为运行时全量（bundle 为静态目录，`/api/config` 白名单仅 3 个） | 对 `MCP_01` 发一次 meta 探针，比对 `lab_id/phase` | recon-06 |
| R-2 | 模型后端是否 Ollama（本部署 `LongCat-2.5`，上游为 `llama3.1`） | 被动：`/api/config` + meta；主动：定向探 `11434`（需 `--profile active`） | recon-01 定级 |
| R-3 | 向量库实现与端口（本部署被动面无端口证据） | 定向探 `6333`/`8080`/`19530`/`8000`，单次、低频 | recon-04 定级 |
| R-4 | `/api/secrets/validate` 的失败语义（4xx 还是 200+body） | 用一次已知错误 `answer` 取状态码，不爆破 | recon-06 判据 |
| R-5 | `control_mode: off` 的业务含义 | 对比 `MM_05`（白名单内）与 `MM_04` 的 meta | recon-07 护栏结论 |

---

## 5. 已排除（不作为实现依据）

- **`/v1/models` 端点**：SKILL.md 模板假设存在；本部署实测为 SPA 回退，排除为「默认探针」，改为「可选探针 + 负结果留证」。
- **`nmap -sC -sV -p- <CIDR>` 作为默认动作**：违反 OPSEC「低频低噪」，排除；降为 `--profile active` 的显式选项。
- **`pyrit.orchestrator` / `*Orchestrator` / `AzureOpenAIChatTarget` / `XpiaAttack`**：v1.1.0 已删除或不存在（F-14），排除。
- **以产品文档推断部署版本/模型**：与 F-5 冲突，排除（D-2）。
- **明文凭据落盘**：SKILL.md 明确禁止，排除；仅记线索指纹。
- **`/mcp`、`/tools/list`、`/healthz` 作为通用 AI 面探针**：本部署全部命中 SPA 回退，排除为判据（F-3）。

---

## 6. 门禁记录（阶段 1）

| 编号 | 检查项 | 依据 | 实测（命令 + 摘要） | 判定 | 结论 |
|---|---|---|---|---|---|
| B7 | PyRIT 版本与对象图 | §2.1 | `grep -n "pyrit==1.1.0" docs/research/pyrit-canonical-references.md` → §1 命中；本文 §3 映射仅用 `executor.attack`/`prompt_target`/`score` | 符合 | PASS |
| B8 | 可追溯性 | §2.1 | F-1..F-15 每条带 URL 或可复跑 curl；§4 五闸均带取证方式 | 符合 | PASS |
| AC-1 | 每条结论可定位一手源 | §3.1 验收① | F-1..F-15 均有来源列，无空来源 | 符合 | PASS |
| AC-2 | 版本号明确 | 验收② | `pyrit==1.1.0`；`nginx/1.27.5`；`LongCat-2.5` | 符合 | PASS |
| AC-3 | 七条攻击路径均有对象映射 | 验收③ | §3 表 recon-01..07 全覆盖 | 符合 | PASS |
| AC-4 | 待核实项逐条命名 + 取证方式 | 验收④ | R-1..R-5 | 符合 | PASS |
| AC-5 | 落盘 `docs/research/` | 验收⑤ | 本文件 | 符合 | PASS |

**阶段结论**：`PASS`（不符合项 0）。复验命令：`python scripts/check_glossary.py && python scripts/validate_skill.py`。
