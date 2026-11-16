# recon-ai 三目标侦察报告（2026-11-16）

> 执行体：`skills/recon-ai` + `tools/recon_ai`；分级：`active`（只读 GET + 每目标一次无害回显 +
> recon-04 定向 4 端口探测，≤8）；
> 授权边界：合法授权、只读验证；active 端口探测已按本轮授权执行；未调用任何状态变更端点
> （`/api/reset`、`/api/attack-log/clear`、`/api/llm/configure`、`/api/scenarios/*/scan|fix`
> 均未请求），未做口令猜测、未做全端口扫描。

## 1. 目标范围

| 编号 | 目标 | 形态 | 结果 |
|---|---|---|---|
| ① | `http://ai-weekly.192.168.40.210.nip.io/reports/2026-11-15_ai_weekly.html` | 静态报告 + Streamlit 聊天 SPA | PASS，2 资产 |
| ② | `http://192.168.40.189` | AIVP 式 React SPA + SSE 聊天 | PASS，6 资产 |
| ③ | `http://192.168.40.183:9000` | DVAA 多智能体靶场 | PASS，5 资产 |

## 2. 侦察方法

1. **自适应发现（只读，≤12 请求）**：入口页 → 应用族/基路径/版本；识别 Streamlit
   （`/_stcore/health`、`host-config`、前端 bundle 版本）、AIVP 品牌标记、DVAA 编排面
   （`/health`、`/agents`、`/api/llm/status`）、Gradio/OpenAI/Ollama/OpenAPI 通用端点。
2. **独立聊天入口识别**：入口含路径时额外读取该页，提取浮动按钮（`#aiFab`）、直链
   `href="/chat"`、`iframe src="/chat"` 三类标记，并记入 `plan.basis` 与 recon-02 证据。
3. **7 步枚举 recon-01..07**：每步独立 `step_id`、独立证据片段、独立截图；
   仅 PRESENT 建资产，UNDETERMINED 进未决面与缺口台账。`active` 档仅在 recon-04
   追加 4 个定向端口 GET（6333/8080/19530/8000，上限 8），不做全端口扫描。
4. **证据三件套**：确切命令（copy/paste 可复现）+ 关键输出 + 截图；截图 `url` 直截或
   `transcript` 转录页；MANIFEST.jsonl 登记 sha256 与截图哈希。
5. **自校验 C1–C9 + C12**：运行目录隔离（`runs/<run_id>/`）、步骤覆盖、证据新鲜度、
   截图完整性、清单契约、结论一致性；任一门禁不过即 `BLOCKED` 且退出码 1。
6. **OPSEC**：被动优先；低门槛 agent 仅在清单声明字段基础上选择（`weak/critical/vulnerable`，
   优先 `helperbot`），不对 `hardened` agent 反复试探。

复现命令（任选目标）：

```bash
python tools/recon_ai/cli.py run --target <TARGET> --profile active --out-dir evidence/recon-20261116/<slot>
python tools/recon_ai/cli.py verify --run evidence/recon-20261116/<slot>/runs/<run_id>
```

## 3. 关键发现

### ① 静态报告站 + Streamlit 聊天（`streamlit`，基路径 `/chat`，v1.67.0）

- 报告页存在**独立聊天按钮**：浮动按钮 `#aiFab`（`aria-label="打开 AI 周报助手"`）→ `href="/chat"`；
  另含直链与 `<iframe class="ai-frame" src="/chat" title="AI 周报助手">`（见截图与命令）。
- `GET /chat/_stcore/health` → 200 `ok`；`/chat/_stcore/host-config` 可匿名读取；
  `GET /chat/_stcore/agent/openapi.json` 可读，`x-streamlit-agent-api: disabled`。
- 资产：`Streamlit 聊天前端`（模型服务）、`Streamlit agent MCP（disabled）`（MCP 工具面）。
- 不可判定：LLM 引擎（被动面无模型名）、RAG、agent 系统；护栏为**协议性缺口**
  （WebSocket 无法以只读 HTTP 完成一轮对话，recon-07 已注明）；向量库 **ABSENT**
  （定向 4 端口全关，属有证据的阴性结论）。
- 未判诱饵：发现 4 项应用族/健康面活体信号。

### ② AIVP 式聊天平台（`aivp`）

- `/api/config` 暴露 `llm_model_default: LongCat-2.5`；`POST /api/labs/MM_04/chat` 返回 SSE
  （事件 `meta`/`message`，含 `request_id`、`phase` 等元数据）。
- 前端 `/assets/index-BtcwQhVS.js` 命中检索链路痕迹（RAG 面存在，框架不可判定）。
- `/api/secrets/validate` 返回 200 + `success:false`（凭据校验预言机 / MCP 信任边界面）；
  错误语义不能按状态码判失败。
- 无害回显 `RECON-PROBE-OK` 被原样返回（护栏放行）；安全响应头有缺失（recon-07 注记）。
- 资产 6 条：LLM 引擎、SSE 聊天、RAG、agent 编排面（推断）、MCP 校验预言机、护栏。
- 不可判定：无（RAG 与 agent 的具体框架仍不可判定，属指纹级限制）；向量库 **ABSENT**
  （6333/8080/19530/8000 全关）。

### ③ DVAA 多智能体靶场（`dvaa`）

- `/health` 报告 21 个 agent；`/agents` 清单分布：15 api、4 mcp、2 a2a；
  含 `securebot(hardened)`、`helperbot(weak)`、`toolbot/pluginbot/proxybot(mcp)` 等。
- `/api/llm/status` 暴露 `provider=openai-compatible`、`model=LongCat-2.5`。
- 聊天面选择 `helperbot`（weak），单次无害回显原样返回（OpenAI 兼容 JSON）。
- MCP 工具面：4 个 agent 端口 `/mcp/tools` 均匿名可读——`:7010`
  （read_file/write_file/execute/fetch_url）、`:7011`（query_database/get_user/list_tables）、
  `:7012`（fetch_data/store_secret）、`:7013`（secure_query/sign_document/transfer_funds）；
  全部含 `vulnerable` 标记，`Access-Control-Allow-Origin: *`。资产按类别聚合 1 条，
  逐端口清单见证据（recon-06）。
- 资产 5 条：LLM 引擎、聊天 API、agent 运行时（21 agents）、MCP 工具清单、护栏。
- 不可判定：RAG；向量库 **ABSENT**（定向 4 端口全关）。未判诱饵（4 项发现信号）。

## 4. 证据清单

| 目标 | run_id | 片段 | 截图 | 门禁报告 |
|---|---|---|---|---|
| ① | `20261116T214509-ai-weekly.192.168.40.210.nip.io-7d7b` | `runs/<id>/recon-01..07.md` | 7 张 | `runs/<id>/verification-report.md` |
| ② | `20261116T212323-192.168.40.189-4055` | `runs/<id>/recon-01..07.md` | 7 张 | `runs/<id>/verification-report.md` |
| ③ | `20261116T214815-192.168.40.183-c0f3` | `runs/<id>/recon-01..07.md` | 7 张 | `runs/<id>/verification-report.md` |

根目录：`evidence/recon-20261116/{t1-chat,t2-aivp,t3-dvaa}/`；每目录含最新
`ai-assets.json`、`ai-assets.md`、`verification-report.md`，`runs/` 保留历次运行不覆盖。
证据清单 `MANIFEST.jsonl` 逐行记录 `step_id`、命令、sha256、时间窗、profile、件套状态、
截图哈希与 flag 双通道（本次无 flag 捕获）。

### 4.1 截图证据（内嵌）

> `collect_evidence.py` 片段的「截图（访问证明）」小节已内嵌原图；下表按步骤把 21 张截图
> 直接嵌入本报告（report-exam §3.2「直接 include」推荐方式，非仅路径引用）。
> 截图类型：`url` = 目标页面直截；`transcript` = 请求/响应转录页渲染。

**① ai-weekly（`20261116T214509-...-7d7b`）**

<table>
<tr>
<td align="center"><b>recon-01 不可判定</b><br><img src="../evidence/recon-20261116/t1-chat/runs/20261116T214509-ai-weekly.192.168.40.210.nip.io-7d7b/shots/recon-01-url.png" width="380" alt="recon-01"></td>
<td align="center"><b>recon-02 Streamlit 聊天前端</b><br><img src="../evidence/recon-20261116/t1-chat/runs/20261116T214509-ai-weekly.192.168.40.210.nip.io-7d7b/shots/recon-02-url.png" width="380" alt="recon-02"></td>
</tr>
<tr>
<td align="center"><b>recon-03 不可判定</b><br><img src="../evidence/recon-20261116/t1-chat/runs/20261116T214509-ai-weekly.192.168.40.210.nip.io-7d7b/shots/recon-03-url.png" width="380" alt="recon-03"></td>
<td align="center"><b>recon-04 不可判定</b><br><img src="../evidence/recon-20261116/t1-chat/runs/20261116T214509-ai-weekly.192.168.40.210.nip.io-7d7b/shots/recon-04-url.png" width="380" alt="recon-04"></td>
</tr>
<tr>
<td align="center"><b>recon-05 不可判定</b><br><img src="../evidence/recon-20261116/t1-chat/runs/20261116T214509-ai-weekly.192.168.40.210.nip.io-7d7b/shots/recon-05-url.png" width="380" alt="recon-05"></td>
<td align="center"><b>recon-06 agent MCP（disabled）</b><br><img src="../evidence/recon-20261116/t1-chat/runs/20261116T214509-ai-weekly.192.168.40.210.nip.io-7d7b/shots/recon-06-transcript.png" width="380" alt="recon-06"></td>
</tr>
<tr>
<td align="center"><b>recon-07 不可判定</b><br><img src="../evidence/recon-20261116/t1-chat/runs/20261116T214509-ai-weekly.192.168.40.210.nip.io-7d7b/shots/recon-07-transcript.png" width="380" alt="recon-07"></td>
<td></td>
</tr>
</table>

**② 192.168.40.189（`20261116T212323-...-4055`）**

<table>
<tr>
<td align="center"><b>recon-01 LongCat-2.5</b><br><img src="../evidence/recon-20261116/t2-aivp/runs/20261116T212323-192.168.40.189-4055/shots/recon-01-url.png" width="380" alt="recon-01"></td>
<td align="center"><b>recon-02 SSE 聊天</b><br><img src="../evidence/recon-20261116/t2-aivp/runs/20261116T212323-192.168.40.189-4055/shots/recon-02-transcript.png" width="380" alt="recon-02"></td>
</tr>
<tr>
<td align="center"><b>recon-03 RAG 痕迹</b><br><img src="../evidence/recon-20261116/t2-aivp/runs/20261116T212323-192.168.40.189-4055/shots/recon-03-url.png" width="380" alt="recon-03"></td>
<td align="center"><b>recon-04 不可判定</b><br><img src="../evidence/recon-20261116/t2-aivp/runs/20261116T212323-192.168.40.189-4055/shots/recon-04-url.png" width="380" alt="recon-04"></td>
</tr>
<tr>
<td align="center"><b>recon-05 agent 编排面</b><br><img src="../evidence/recon-20261116/t2-aivp/runs/20261116T212323-192.168.40.189-4055/shots/recon-05-url.png" width="380" alt="recon-05"></td>
<td align="center"><b>recon-06 凭据校验预言机</b><br><img src="../evidence/recon-20261116/t2-aivp/runs/20261116T212323-192.168.40.189-4055/shots/recon-06-transcript.png" width="380" alt="recon-06"></td>
</tr>
<tr>
<td align="center"><b>recon-07 护栏（放行回显）</b><br><img src="../evidence/recon-20261116/t2-aivp/runs/20261116T212323-192.168.40.189-4055/shots/recon-07-transcript.png" width="380" alt="recon-07"></td>
<td></td>
</tr>
</table>

**③ 192.168.40.183:9000（`20261116T214815-...-c0f3`）**

<table>
<tr>
<td align="center"><b>recon-01 LongCat-2.5</b><br><img src="../evidence/recon-20261116/t3-dvaa/runs/20261116T214815-192.168.40.183-c0f3/shots/recon-01-url.png" width="380" alt="recon-01"></td>
<td align="center"><b>recon-02 OpenAI 兼容聊天</b><br><img src="../evidence/recon-20261116/t3-dvaa/runs/20261116T214815-192.168.40.183-c0f3/shots/recon-02-transcript.png" width="380" alt="recon-02"></td>
</tr>
<tr>
<td align="center"><b>recon-03 不可判定</b><br><img src="../evidence/recon-20261116/t3-dvaa/runs/20261116T214815-192.168.40.183-c0f3/shots/recon-03-url.png" width="380" alt="recon-03"></td>
<td align="center"><b>recon-04 不可判定</b><br><img src="../evidence/recon-20261116/t3-dvaa/runs/20261116T214815-192.168.40.183-c0f3/shots/recon-04-url.png" width="380" alt="recon-04"></td>
</tr>
<tr>
<td align="center"><b>recon-05 多智能体运行时（21 agents）</b><br><img src="../evidence/recon-20261116/t3-dvaa/runs/20261116T214815-192.168.40.183-c0f3/shots/recon-05-url.png" width="380" alt="recon-05"></td>
<td align="center"><b>recon-06 MCP 工具清单</b><br><img src="../evidence/recon-20261116/t3-dvaa/runs/20261116T214815-192.168.40.183-c0f3/shots/recon-06-transcript.png" width="380" alt="recon-06"></td>
</tr>
<tr>
<td align="center"><b>recon-07 护栏（放行回显）</b><br><img src="../evidence/recon-20261116/t3-dvaa/runs/20261116T214815-192.168.40.183-c0f3/shots/recon-07-transcript.png" width="380" alt="recon-07"></td>
<td></td>
</tr>
</table>

## 5. 验证结果

- 三目标 `verify` 均为 `verdict: PASS`（C1 步骤覆盖、C2 新鲜度、C3 三件套、
  C4 截图、C5 清单一致、C6 判定基底、C7 契约、C8 报告结构、C9 结论一致、C12 哈希一致）。
- 离线回归：`python -m unittest discover -s tests -p "test_recon_ai*.py"` → **86 tests OK**
  （新增 MCP 逐端口、Streamlit 协议缺口、证据子进程重试）；断图校验 **4 tests OK**。
  新增覆盖：Streamlit 聊天 PRESENT、DVAA 家族发现/低门槛 agent、截图 IEND 等待与转录页回退。

## 6. 缺陷排查与修复（按优先级）

| 优先级 | 问题（含证据） | 修复 | 复验 |
|---|---|---|---|
| P0 | 截图写入竞态：T2 recon-03 的 MANIFEST 哈希与实际文件不一致（C12 FAIL） | `shot.py` 以 PNG `IEND` 块判断写完，原生路径重试 2 次；直截失败回落转录页 | 三目标截图哈希一致；新增单元测试 |
| P0 | 家族盲探测：T1 发现 Streamlit 但 0 资产（硬编码 AIVP 端点） | `probes.py` 家族感知（Streamlit 入口/健康、DVAA 聊天/清单）；`discovery` 结果按 step 合并 | T1 → 2 资产；新增 Streamlit 闭环测试 |
| P0 | DVAA 盲区误判诱饵：T3 旧跑 `decoy_suspected=true`、0 资产 | 新增 `/health`、`/agents`、`/api/llm/status`、`/mcp/tools` 发现与判据；`extra_signals` 纳入应用族信号 | T3 → 5 资产、`decoy=false` |
| P1 | 聊天面首选 `hardened` agent（SecureBot）易无效试探 | 依清单 `securityLevel` 选择 `weak/critical/vulnerable`，优先 `helperbot` | T3 回显成功、单次请求 |
| P1 | 资产端点回落到步骤模板而非实际证据 | `inventory.py` 优先 `judgement.context.endpoint` | T3 MCP 端点=`:7010/mcp/tools`，LLM 端点=`/api/llm/status` |
| P1 | 独立聊天按钮未进入证据基底 | `discovery.py` 读取入口页并提取 `#aiFab`/直链/iframe；`runner` 保留原始入口路径 | T1 `plan.basis` 与 run.json 留痕 |
| P1 | 向量库覆盖不足：passive 档一律 UNDETERMINED | recon-04 以 `--profile active` 定向 4 端口（6333/8080/19530/8000） | 三目标均为 ABSENT（阴性结论可复核） |
| P1 | MCP 只引用首个成功端口 | `judge_mcp` 汇总全部成功 `/mcp/tools`，逐端口工具名 + CORS | T3 四端口工具数 4/3/2/3 |
| P2 | 证据子进程一次性异常（`0xC000012D`）无重试 | 仅异常退出（NTSTATUS/负值 + 空 stderr）重试一次；质量门失败不重试 | 新增 2 例单测 |
| P2 | SKILL.md 与实现不一致（声称家族发现但实现仅 AIVP） | 更新 `skills/recon-ai/SKILL.md` 实现范围、DVAA/Streamlit 端点、截图完整性 | 文档与 86 测试一致 |

## 7. 未决事项与决策

| # | 事项 | 决策 | 状态 / 依据 |
|---|---|---|---|
| 1 | T1 护栏面 | 保留 UNDETERMINED，属 **WebSocket 协议性缺口**，不以无证据推断；如需实测，授权下用浏览器点 `#aiFab` 发一次无害回显并留痕 | recon-07 已写明协议原因 |
| 2 | T1 agent API 为 disabled | 维持资产但降级为暴露面，不作为可攻击工具面；下游 `attack-mcp-tool` 先复核状态 | recon-06 |
| 3 | 向量库覆盖 | 已关闭：active 定向 4 端口（6333/8080/19530/8000），三目标均 ABSENT；不做全端口扫描 | 三次 active run PASS |
| 4 | DVAA 多 MCP 端口 | 已关闭：逐端口列出工具清单（4/3/2/3）；资产仍按类别聚合 1 条，避免虚增 | recon-06 |
| 5 | 证据子进程一次性异常 | 已关闭：仅异常退出且空 stderr 时重试一次；质量门失败不重试 | 单测 2 例 |
| 6 | 交互式验证授权 | 保留：本轮仅执行只读 active 端口探测；WebSocket 对话需另行确认授权 | 待授权 |

## 8. 提交前校验（OSAI §6.1 / §6）

- 断图校验：`python scripts/check_report_assets.py report/recon-ai-3targets-20261116.md`
  → `PASS`（21/21 引用可解析且 PNG 完整）。
- 规则单一源：`docs/operations/osai-submission-compliance.md` §6（R1–R5）；
  `report-exam` §3.3 与主线工作流 §5 第 7 条已引用。
- 提交形态：整包 `report/` + `evidence/` 保持相对结构，或直接 include 片段后导出 PDF；
  禁止 base64 / 复制截图字节（C1 + C4）。