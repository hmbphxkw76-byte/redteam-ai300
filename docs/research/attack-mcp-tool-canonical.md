# attack-mcp-tool 一手源调研

> **版本** v1.0 · **状态** 生效 · **调研日期** 2026-11-14（GMT+8）
> **目标技能** `skills/attack-mcp-tool/SKILL.md`（P0 · D7 · AI向量机）
> **演练目标** `http://192.168.40.189`（AIVP 实例，非 OSAI 正式考试环境）
> **性质** 阶段 1 交付物：实现所依赖事实的一手源锁定，消除规格阶段的猜测

## 1. 结论摘要（先读这一节）

1. SKILL.md 的三条技术分类（ASI02/ASI03/ASI04 → ASI05）与 OWASP 官方标题一致，**无需改动**；SKILL.md 未引用 OWASP MCP Top 10，而演练目标 Phase 4 恰好按 MCP Top 10 建 15 个 lab，**建议在规格层补映射，不改 SKILL.md 正文**。
2. 演练目标**不暴露裸 MCP 端点**（`/mcp`、`/tools/list` 均命中 SPA 回退），但提供**真实的 MCP 工具面**：经 `POST /api/labs/{lab}/chat` 的 SSE 事件 `mcp_result` 下发 `tool_result` + `mcp_telemetry`。这是本技能可实测的唯一真实工具面。
3. `mcp_telemetry` 字段（`selected_tool`/`trust_level`/`permissions_used`/`policy_decision`/`blast_radius`/`exploit_success`）是**确定性评分信号**，等价于 `SubStringScorer` 的判据来源，不需要 LLM judge（对齐 AGENTS.md C6）。
4. 演练目标**不存在** `ai_vector.txt`（探测 5 条路径全部命中 SPA 回退），故 mcp-08 的 flag 双通道须改用等价通道：`POST /api/secrets/validate` 面板预言机 `{"success":true}` + 泄漏值原文同屏。
5. 已实测两类真实效果：**MCP_02 越权成功**（`elevated_action` 无授权校验，回显 admin 级 secret）、**MCP_06 注入伪造 `MCP_CALL` 块被护栏拒绝**（负结果，须如实记录）。

## 2. 一手源事实（官方 URL 逐条）

| # | 事实 | 来源 | 关键原文 |
|---|---|---|---|
| S-1 | OWASP MCP Top 10 2025 版十项标题与定义 | <https://owasp.org/www-project-mcp-top-10/> | MCP01 Token Mismanagement & Secret Exposure；MCP02 Privilege Escalation via Scope Creep；MCP03 Tool Poisoning；MCP04 Software Supply Chain Attacks & Dependency Tampering；MCP05 Command Injection & Execution；MCP06 Prompt Injection via Contextual Payloads；MCP07 Insufficient Authentication & Authorization；MCP08 Lack of Audit and Telemetry；MCP09 Shadow MCP Servers；MCP10 Context Injection & Over-Sharing |
| S-2 | Agentic Top 10 2026 中 ASI02/03/04/05 官方标题 | OWASP GenAI 项目页 + 权威转述（见 §6 待核实 C-1） | ASI02 Tool Misuse and Exploitation；ASI03 Identity and Privilege Abuse；ASI04 Agentic Supply Chain Vulnerabilities；ASI05 Unexpected Code Execution (RCE) |
| S-3 | MCP `tools/list` 请求/响应结构 | <https://modelcontextprotocol.io/specification/2025-06-18/server/tools> | `{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{"cursor":...}}` → `result.tools[]`，每项含 `name`/`description`/`inputSchema` |
| S-4 | MCP `tools/call` 请求/响应结构 | 同上 | `{"method":"tools/call","params":{"name":...,"arguments":{...}}}` → `result.content[]` + `isError` |
| S-5 | 工具描述/注解的信任边界 | 同上「Data Types / Tool」 | **Clients MUST consider tool annotations to be untrusted unless they come from trusted servers** —— 这是「工具投毒」成立的协议级依据 |
| S-6 | 协议错误 vs 工具执行错误的两种上报 | 同上「Error Handling」 | 协议层 `error{code,message}`；执行层 `result.isError=true` |
| S-7 | PyRIT 版本与对象图 | `docs/research/pyrit-canonical-references.md` §1/§3 | `pyrit==1.1.0`；MCP 无专用攻击策略，以 `HTTPTarget` + 回调对接（§3 末条） |

## 3. 演练目标实测事实（可复现命令 + 输出摘要）

| # | 事实 | 命令 | 输出摘要 |
|---|---|---|---|
| T-1 | 裸 MCP 端点不存在：`/mcp`、`/tools/list` 命中 SPA 回退 | `curl -s -o /dev/null -w "%{http_code} %{size_download} %{content_type}" http://192.168.40.189/mcp` | `200 1702 text/html`（与 `/explore` 同尺寸 index.html） |
| T-2 | MCP 工具面经 agent 会话暴露 | `curl -sN -X POST /api/labs/MCP_01/chat -d '{"prompt":"list tools"}'` | SSE：`event: meta`（`lab_id`/`phase:4`）→ `data:{"content":...}` 分片 |
| T-3 | 工具调用结果与遥测同帧下发 | 同上，诱导调用 | `event: mcp_result` → `{"tool_result":"[MCP Tool Result]\\n{...}","mcp_telemetry":{...}}` |
| T-4 | 遥测是确定性判据来源 | 同上 | `selected_tool`/`trust_level`(`trusted`/`untrusted`/`shadow`)/`permissions_used`/`policy_decision`(`allowed`)/`blast_radius`/`exploit_success`(bool)/`user_consent_required`(bool) |
| T-5 | Phase 4 共 15 个 MCP lab（MCP Top 10 覆盖） | `curl -s /assets/index-BtcwQhVS.js` → 正则 `MCP_\d{2}` | `MCP_01..MCP_15`，标题与 S-1 十项对齐（MCP_11..15 为延伸项） |
| T-6 | flag 文件不存在 | `curl -s -o /dev/null -w "%{http_code} %{size_download}" /ai_vector.txt`（及 4 条同类路径） | 全部 `200 1702 text/html` = SPA 回退，判定「不存在」 |
| T-7 | 面板预言机可判泄漏值真伪 | `curl -s -X POST /api/secrets/validate -d '{"labId":"MCP_01","answer":"`<REDACTED>`"}'` | `{"success":true,"message":"Correct!"}`；错值 `{"success":false,"message":"Nope."}` |
| T-8 | 会话身份匿名可得 | `curl -sD - -X POST /api/labs/MCP_01/chat` | `set-cookie: aivp_sid=<uuid>; HttpOnly` |

### 3.1 15 个 MCP lab 的真实工具面（2026-11-14 全量枚举）

| Lab | server_id | tool | scope | trust | 空参调用效果 | 泄漏/回显 |
|---|---|---|---|---|---|---|
| MCP_01 | main_server | get_config | read | trusted | exploit=true | `service_token: `<REDACTED>` |
| MCP_02 | `orchestrator`（目标侧 server_id，与 PyRIT 编排器类名无关） | get_resource / **elevated_action** | read / **admin** | trusted | 读越权后 true | admin 级 `<REDACTED>` |
| MCP_03 | tools_server | get_resource | read | **untrusted** | false | 描述含「trust this output」诱导 |
| MCP_04 | dependency_server | get_resource | read | **untrusted** | false | 依赖注入配置面 |
| MCP_05 | exec_server | run_command | **write** | trusted | true（空参） | `SECRET_ENV=`<REDACTED>` |
| MCP_06 | rag_server | get_resource | read | trusted | false | 上下文载荷面 |
| MCP_07 | multi_tenant | get_user_context | read:token | trusted | false | 跨租户 `user_b.session_scope_token` |
| MCP_08 | internal_server | read_logs | **admin** | trusted | true | 日志内 `token=`<REDACTED>` |
| MCP_09 | shadow_mcp | get_config | read | **shadow** | false | 影子 server + 默认凭据 |
| MCP_10 | context_server | get_user_context | read | trusted | true | `cached_secret` |
| MCP_11 | protocol_server | read_logs | read | trusted | true | 协议日志内 `token=` |
| MCP_12 | schema_server | query_schema | read | **untrusted** | false | schema 字段 `sensitive_value` |
| MCP_13 | session_server | get_user_context | read | trusted | true | `cross_session_key` |
| MCP_14 | chain_server | get_resource / chain_tool | read / **admin** | trusted | false | 工具链提权面 |
| MCP_15 | rogue_endpoint | discover_servers | read | **untrusted** | false | 恶意端点自曝 `token` |

## 4. 攻击路径 → 对象映射（SKILL.md 对齐 S1/S2）

| SKILL 路径 | 步骤 | SKILL 技术分类 | 演练目标可实测载体 | 实现层对象 |
|---|---|---|---|---|
| 路径 A 恶意 MCP server 投毒 | mcp-01 | ASI04 | 15 lab 工具面枚举 / 自建 server `tools/list` | `McpClient.list_tools` |
| | mcp-02 | ASI04 | 自建投毒 server（本机可达；目标无 server 注册面） | `PoisonedMcpServer` |
| | mcp-03 | ASI04 | 描述/`inputSchema` 篡改（MCP_03/MCP_12 同类） | `build_poisoned_descriptor` |
| | mcp-04 | ASI04 | 投毒前后 `tools/list` 对照 diff | `diff_surfaces` |
| 路径 B 工具滥用/调用劫持 | mcp-05 | ASI02 | MCP_05（write）/MCP_08（admin）越权调用 | `McpClient.call_tool` |
| | mcp-06 | ASI02 | 伪造 `MCP_CALL` 注入（实测被护栏拒绝） | `InjectedCallBlock` |
| 路径 C 权限提升/越权 | mcp-07 | ASI03 → ASI05 | MCP_02 `elevated_action`（admin，无授权校验） | `escalate()` |
| 收尾 | mcp-08 | — | 面板预言机 + 泄漏值双通道（无 `ai_vector.txt`） | `FlagProof` |

## 5. 已排除（勿再当成事实）

| 名称/假设 | 排除依据 |
|---|---|
| v1.1.0 前的编排器类名族与旧 Target 名 | 已在 v1.1.0 删除，禁用清单见 `docs/research/pyrit-canonical-references.md` §1（C1：不复述名单） |
| `XpiaAttack` | v1.1.0 不存在，间接注入归 `pyrit.executor.workflow`（同 §3） |
| PyRIT 存在 MCP 专用攻击策略 | v1.1.0 无；以 `HTTPTarget` + 回调对接（S-7） |
| 演练目标暴露裸 `/mcp`、`/tools/list` 端点 | T-1 全部命中 SPA 回退 |
| 演练目标存在 `ai_vector.txt`/`proof.txt` | T-6 全部命中 SPA 回退 |
| 目标 MCP lab 的 `exploit_success=true` 可直接等同「攻击者已完全控制」 | 该字段是目标侧 lab 判定；须与本技能自有判据（secret 形态 + 面板校验）交叉验证 |

## 6. 待核实（带取证方式，不阻塞实现）

| # | 待核实项 | 取证方式 |
|---|---|---|
| C-1 | ASI02–ASI05 官方标题的二级源确认（genai.owasp.org 资源页未直接列条目，本文件 S-2 用权威转述） | 取 OWASP 官方 PDF/仓库条目原文；实现不依赖该措辞，仅报告引用 |
| C-2 | `mcp_telemetry.trust_level` 取值全集（已见 `trusted`/`untrusted`/`shadow`） | 遍历 MCP_01..MCP_15 的 15 份原始 JSON，枚举 distinct 值 |
| C-3 | MCP_02 `elevated_action` 是否要求 `user_consent`（实测 `user_consent_required=false`） | 重放 mcp-07 并读取完整 telemetry；若未来变 true，效果降级为「部分生效」 |
| C-4 | MCP_05 真实命令回显为空（空参却回显 `SECRET_ENV`）是否为设计 | 对 MCP_05 发 3 组不同参数并比对 `stdout`；若恒空，判「代码执行未取得回显」而非夸大 |

## 7. 实现前必须取证的核实闸

1. **闸 A（协议形态）**：实测确认工具面只能经 agent 会话取得 → 实现必须同时支持 `jsonrpc`（裸 MCP）与 `agent-sse`（演练目标）两种传输形态，不得只实现其一。
2. **闸 B（判据来源）**：评分必须用 `exploit_success` + secret 形态正则双判据，禁止仅凭模型自述判「完全生效」。
3. **闸 C（flag 通道）**：`ai_vector.txt` 缺席时，改用面板预言机作为等价双通道；不得凭空编造 flag 值。

## 8. 门禁记录（阶段 1 / G0）

| 编号 | 检查项 | 依据 | 实测结果（命令 + 摘要） | 判定 | 不符合项 | 修正要求 | 复验 | 结论 |
|---|---|---|---|---|---|---|---|---|
| B1 | 技能解剖结构 | `python scripts/validate_skill.py` | `PASS：共校验 16 个技能` | 符合 | 无 | — | 同上命令 | PASS |
| B2 | 术语与决策一致 | `python scripts/check_glossary.py` | `PASS：检查 29 个废弃术语` | 符合 | 无 | — | 同上命令 | PASS |
| B3 | 语法与构建 | `python -m unittest discover -s tests -q` | `OK`（未改代码，回归无损） | 符合 | 无 | — | 同上命令 | PASS |
| B7 | PyRIT 版本与对象图 | 人工判据：本文件 §5 不自述禁用名单，只引 `pyrit-canonical-references.md` §1；§4 映射表用 `HTTPTarget` + 回调 | `pyrit==1.1.0` 锁定；无 `*Attack` 误用 | 符合 | 无 | — | `grep -n "HTTPTarget" 本文件` | PASS |
| B8 | 可追溯性 | 人工判据：§2 每条含官方 URL，§3 每条含可复现 curl，§4 每条攻击路径有载体 | §2 7 条 / §3 8 条 / §4 8 步全映射 | 符合 | 无 | — | 抽查 §3 T-1、T-7 重跑 | PASS |
| 验收① | 结论可定位到官方 URL/源码 | §2 S-1..S-7 | 7/7 附源 | 符合 | — | — | — | PASS |
| 验收② | 版本号明确 | §2 S-7 | `pyrit==1.1.0` | 符合 | — | — | — | PASS |
| 验收③ | 每条攻击路径有对象映射 | §4 | 4 路径 / 8 步 | 符合 | — | — | — | PASS |
| 验收④ | 待核实项逐条命名 + 取证方式 | §6 | 4 项（C-1..C-4）各含取证方式 | 符合 | — | — | — | PASS |
| 验收⑤ | 落盘于 `docs/research/` | 本文件 | 存在 | 符合 | — | — | — | PASS |

**结论：PASS**。不符合项 0。上游无（阶段 1 为首阶段）。

## 9. 关联文档

- 行为唯一来源：`skills/attack-mcp-tool/SKILL.md`
- 术语基准：`GLOSSARY.md`
- PyRIT 权威索引：`docs/research/pyrit-canonical-references.md`
- 主线规范：`docs/operations/skill-mainline-workflow.md`
