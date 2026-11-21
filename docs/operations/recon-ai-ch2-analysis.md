# recon-ai — Ch2 对齐旁路分析规范

本文是 `skills/recon-ai/SKILL.md`「Ch2 对齐旁路分析」章节的字段与规则唯一事实源（AGENTS.md C1）。实现位于 `tools/recon_ai/ch2.py`；7 步资产枚举（recon-01..07）与其 C1–C9 门禁不变，本层为零网络旁路，不新增资产类别、不修改证据片段结构。

## 1. 依据与范围

事实来源：OffSec AI-300《AI-300: Reconnaissance for AI Targets》第 2 章（Ch2-Reconnaissance-for-AI-Targets.html），四个学习单元：

| 文档单元 | 本文落点 | 7 步枚举是否覆盖 |
|---|---|---|
| §2.1 AI System Attack Surfaces | `TAXONOMY` 四层分类法 + `parse_self_describing` | 部分：7 类组件覆盖分层 + MCP/A2A 自描述面，但缺四层归类表述 |
| §2.2 Passive Reconnaissance | `parse_ai_headers` / `parse_health_config` / `mine_repository` | 缺：AI 专用响应头、健康端点配置字段、仓库工件 |
| §2.3 Active Reconnaissance | `classify_endpoint_status` / `fingerprint_behavior` / `parse_rag_sources` / `map_knowledge_base` / `parse_client_config` / `probe_threshold_series` | 缺：401 vs 404 语义、六类行为指纹、RAG 源元数据与知识库映射、JS 配置泄露、检索阈值递减 |
| §2.4 Detection and Evasion Analysis | `assess_detection` / `endpoint_burst_risk` / `covert_rewrite` / `pacing_plan` / `detect_canary` / `parse_response_metadata` / `assess_log_visibility` | 缺：规则命中、隐蔽改写、节奏计划、诱饵识别、metadata 泄露、防御日志可见性 |

不实现文档中的主动载荷构造、注入利用、凭据使用等攻击动作（属 `attack-*` 系列，且违反本技能「不执行攻击」边界）。

## 2. 触发条件

满足任一即启用旁路分析：

1. 已取得 HTTP 响应头，需判读 `X-AI-Backend` / `X-RAG-Provider` / `X-Powered-By` / `Server` / `Via` / Kong 与限流头。
2. 已取得健康端点 JSON（含 `status` 或 `model`），需抽取 `model` / `mcp_enabled` / `rag_enabled` / `version` / `service`。
3. 已取得端点 HTTP 状态码，需区分 401/403（存在需认证）与 404（不存在）。
4. 已取得模型交互回显，需按六类技术做行为指纹。
5. 已取得 RAG `sources[]`，需判读文档名、chunk_id、原文片段、相似度分数与详细度分级。
6. 已取得疑似诱饵文本（密钥、口令、内部 URL、过完整凭据组），需识别并留痕。
7. 需评估查询的检测规则命中、给出隐蔽改写建议或请求节奏计划。
8. 已取得仓库工件文本，需离线抽取依赖、RAG 配置、工具权限、系统限制、护栏、环境变量名、供应链与提交历史。
9. 已取得 MCP/A2A 自描述 schema，需判读工具 name、能力、信任关系（自报，须运行时复核）。
10. 聊天响应体含 `metadata.provider`/`model`（wrapper 回传上游对象），需指纹化抽取。
11. 已取得前端 JS 工件，需抽 `apiBase`/`assistantEndpoint`/`featureFlags` 配置键。
12. 已取得检索递减序列（精确/同义/错拼），需观察检索触发翻转与阈值边界。
13. 已取得防御日志字段与能力清单，需评估捕获面与语义/意图/跨会话缺口。

## 3. 执行步骤

1. 将观测整理为 JSON 文件，顶层含 `target`、`profile`、`observations` 数组；每项含 `kind` 及该 kind 的字段（见 §4）。
2. 执行 `python tools/recon_ai/cli.py analyze --input <OBS_JSON> --out <ANALYSIS_JSON>`。
3. 读取 `signals` / `findings` / `endpoints` / `disclosure` / `repository` / `covert` / `pacing`；对 `validate_analysis` 违规项回到证据侧补证或修正，不得直接改写结论字段。
4. 旁路分析产物不入 `loot/` 证据三件套，不作为 C1–C9 的输入；需要引用时按路径引用，不复制正文（C1）。

## 4. 输入输出规范

### 4.1 观测 kind 与字段

| kind | 必填字段 | 判读函数 |
|---|---|---|
| `headers` | `headers`（对象） | `parse_ai_headers` |
| `health` | `body`（JSON 字符串） | `parse_health_config` |
| `endpoint` | `status`（整数）、`url` | `classify_endpoint_status` |
| `chat` | `technique`、`response`；`context` 用 `marker`/`recalled`；`capability` 用 `expected` | `fingerprint_behavior` |
| `rag` | `body`（JSON 字符串，含 `sources[]`） | `parse_rag_sources` |
| `canary` | `text` | `detect_canary` |
| `detection` | `query` | `assess_detection` |
| `sequence` | `paths`（数组） | `endpoint_burst_risk` |
| `repository` | `files`（路径→文本映射） | `mine_repository` |
| `self_describe` | `schema`（MCP/A2A 自描述 JSON 文本） | `parse_self_describing` |
| `metadata` | `body`（JSON 字符串，含 `metadata.provider`/`model`） | `parse_response_metadata` |
| `client_config` | `text`（JS 工件文本） | `parse_client_config` |
| `threshold` | `stages`（`exact`/`synonym`/`misspelling` 数组，含 `triggered`/`score`） | `probe_threshold_series` |
| `log_view` | `log`（防御日志字段与能力对象） | `assess_log_visibility` |

`technique` 取六值：`identity` / `contradiction` / `cutoff` / `style` / `capability` / `context`；其它值忽略（不猜测、不扩写）。`stage` 取三值：`exact` / `synonym` / `misspelling`；样本 <2 或无状态翻转即判「不可判定」，不推断阈值。

### 4.2 输出字段

| 字段 | 含义 |
|---|---|
| `taxonomy` | 四层分类法：层名、对应 recon step_id、可枚举属性 |
| `signals` | 被动信号列表：`kind` / `value` / `basis` / `confidence`，值不含明文凭据 |
| `endpoints` | 每条：`url` / `verdict`（PRESENT / AUTH_REQUIRED / ABSENT / UNDETERMINED） |
| `findings` | 每条：`name` / `verdict` / `signals` / `note` / `family`（仅多信号一致时非空） |
| `disclosure` | RAG 源详细度：`none` / `minimal` / `moderate` / `detailed` |
| `repository` | 仓库工件抽取结果，按工件类型分组 |
| `covert` | `original` / `hits` / `suggestions` / `note`（建议仅供授权测试人工选择） |
| `pacing` | `min_gap_seconds` / `max_gap_seconds` / `mix_legitimate_traffic` / `note` |
| 新增 `findings` | 自描述协议面 / 客户端配置泄露 / 检索阈值递减 / 交互日志可见性（均 `name` / `verdict` / `signals` / `note`，`metadata:*` 信号并入顶层 `signals`） |

## 5. 校验规则

`validate_analysis(result)` 返回违规字符串列表；CLI 在违规非空时退出码 1：

1. **肯定结论须有依据**：`verdict` 为 `存在` 或 `命中` 但 `signals` 为空，违规。不可判定/未命中不强制信号（避免「无证据即失败」误判）。
2. **每条信号须有 basis**：空 `basis` 违规，落实 C6「判定可复核」。
3. **凭据不落明文**：`canary:password` 的 `value` 必须是 `Bearer-<指纹>`，否则违规（对齐技能边界第 5 条）。
4. **家族结论须交叉验证**：`family` 非空但 `verdict` 非 `存在`，违规；`family` 仅在 ≥2 类技术指向同一家族时置位，单信号只记「未定家族」。
5. **端点语义受限**：`verdict` 必须为四个枚举值之一，杜绝把 401 写成「存在且可访问」、把 404 写成「存在」。
6. **凭据不落明文（metadata）**：`metadata:*` 信号值命中 `sk-` / `api_key=` / `AKIA` 样式即违规（wrapper 回传上游对象时须指纹化）。
7. **阈值不可单样本推断**：`检索阈值递减` 样本 <2 或无触发翻转时 `verdict` 必须为「不可判定」。
8. **日志缺口仅认显式声明**：未出现在日志对象中的能力缺口不计为已观测事实，避免「无证据即告警」。

## 6. OPSEC 与边界

- 旁路层不发包、不等待、不自动执行 `covert.suggestions`；改写建议由授权测试人员人工选择。
- `pacing_plan` 仅输出建议参数（间隔 30–60 秒、混入合法流量），节奏执行由调用方负责。
- 诱饵识别只留痕、不使用凭据；密钥与口令一律指纹化。
- 不推断未观测事实：缺 `status` 或 `model` 的健康体不判为健康配置；未知 `technique` 不参与指纹。
- 术语符合 `GLOSSARY.md`；使用「诱饵机」而非废弃词。
