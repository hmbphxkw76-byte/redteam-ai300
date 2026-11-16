# recon-ai 闭环改造：一手源事实核实

> 核验日期：2026-11-16（GMT+8）　|　目标实测：`http://ai-weekly.192.168.40.210.nip.io`　|　性质：阶段 1 research 交付物
> 框架组合（B9）：recon-ai = garak 首扫 + Kali 侦察 + 许可 AI（`docs/research/osai-skill-framework-matrix.md` §⑥）；本次改造属 Kali/自定义脚本层，不引入 PyRIT，B9 合规。

## 1. 目标技术栈实测（一手：现场响应）

| # | 事实 | 实测证据 |
|---|---|---|
| T1 | 站点根为报告服务，`/reports/*.html` 为静态报告 | `GET /` → 200 `<title>AI 领域周报 · 报告服务</title>`；`GET /reports/2026-11-15_ai_weekly.html` → 200, 47302B, `X-App-Version: de5b9173` |
| T2 | `/chat` 307 跳转 `/chat/`，后者是 Streamlit 应用 | `GET /chat` → 307 `location: .../chat/`；`GET /chat/` → 200 `<title>Streamlit</title>`，`src="./static/js/index.DormvYxC.js"` |
| T3 | Streamlit 健康与主机配置挂在**基路径**下 | `GET /chat/_stcore/health` → 200 `ok`（2B）；`GET /chat/_stcore/host-config` → 200 JSON，键 `allowedOrigins/blockErrorDialogs/...` |
| T4 | 根路径同端点不存在；未知路径回落 SPA 页 | `GET /_stcore/health` → 404 `not found`；`GET /chat/healthz` → 200 HTML（SPA 回退，非健康端点） |
| T5 | 存在独立 `/healthz` 返回 `ok`（应用/网关层，非 Streamlit） | `GET /healthz` → 200 `ok` |
| T6 | Streamlit 版本可从静态产物识别 | 前端 bundle 含 `version:\`1.67.0\``；`host-config` 不含版本 |
| T7 | 聊天面为 Streamlit WebSocket 前端，后端模型/检索面未直接暴露 | `/chat/` 仅静态入口与 `_stcore` 路由；无 `/v1/models`、`/api/*` 直接响应 |

## 2. Streamlit 端点事实（一手：官方源码）

来源：`streamlit/streamlit@develop` `lib/streamlit/web/server/starlette/starlette_routes.py`
（`gh api repos/streamlit/streamlit/contents/...`）

- `BASE_ROUTE_CORE = "_stcore"`；`ROUTE_HEALTH = "_stcore/health"`；`ROUTE_HOST_CONFIG = "_stcore/host-config"`；另有 `_stcore/script-health-check`。
- 路由会前置 `base_url`（源码注释示例 `/myapp/_stcore/health`），故**必须先发现基路径**再拼健康端点。
- 健康端点返回 200 纯文本；`host-config` 返回 JSON（跨域/父消息策略），**不含模型或版本信息**。

## 3. 其他 AI 应用族端点（一手源）

| 族 | 端点 | 判定依据 | 来源 |
|---|---|---|---|
| Gradio | `/config`（200 JSON 含 `version/components/dependencies`）、`/queue/join`、`/gradio_api/*` | 路由源码 | `gradio-app/gradio@main` `gradio/routes.py` L1205-1206, L1700 |
| Ollama | `/api/tags`（JSON `models[]`） | 官方 API 文档 | `ollama/ollama` `docs/api.md` |
| OpenAI 兼容（vLLM/TGI/Open WebUI 等） | `/v1/models` | OpenAI API 参考；仓库既有探测 | `platform.openai.com/docs/api-reference/models` |
| LangServe/FastAPI 系 | `/openapi.json` | FastAPI 框架默认 | `fastapi.tiangolo.com` |
| Qdrant | `/healthz`、`/readyz`、`/collections` | 路由源码 | `qdrant/qdrant@dev` `src/actix/mod.rs` L94-95 |
| Chroma | `/api/v2/heartbeat`、`/api/v1/heartbeat`（旧版） | 路由源码 | `chroma-core/chroma@main` `chromadb/server/fastapi/__init__.py` L279-282 |
| URL 健康探测 | 对任意候选端点做 GET，2xx 且非 SPA 回退即视为存活 | 现有 `probes.is_spa_fallback` | 本仓库代码 |

## 4. 证据工具契约（一手：本仓库源码）

`tools/collect_evidence.py`：

- 三件套 `REQUIRED_PIECES = ["确切命令", "关键输出", "截图"]`；五件套另加「AI 交互日志」「flag 双通道」（可选）。
- `--strict`：三件套不全或 flag 不一致 → 退出码 1；片段仍会写出（先写后判），调用方必须自行校验退出码与新鲜度。
- `--manifest` 为**追加** JSONL；记录含 `step_id/command/sha256/timestamp/profile/retention/target/screenshot/pieces/flag_dual/complete`，**无 run_id**。
- `--shot-cmd` 仅记录钩子、不计为「已提供」；无截图时状态为缺失。

## 5. Windows 编码事实（一手：Python 官方文档）

- `PYTHONUTF8=1` 启用 UTF-8 模式；`PYTHONIOENCODING=utf-8` 指定标准流编码（`docs.python.org/3/using/cmdline.html`）。
- 子进程继承环境；`subprocess.run(text=True, encoding="utf-8")` 读取管道时若子进程按控制台代码页（cp936）输出，父进程解码崩溃（`UnicodeDecodeError`）。修复须**双向**：子进程注入 UTF-8 环境 + 父进程容错解码。

## 6. 与 `skills/recon-ai/SKILL.md` 七路径映射

| 路径 | 现状 | 本次结论 |
|---|---|---|
| recon-01 LLM 引擎 | 依赖 `/api/config` 固定路径 | 新增应用族发现：Streamlit 版本、Gradio/Ollama/OpenAI 兼容指纹；固定路径保留为回退 |
| recon-02 模型服务 | 依赖 `/api/labs/{lab}/chat` | 基路径发现 + 候选聊天端点；无端点时如实 `UNDETERMINED` 并列出已试端点 |
| recon-03 RAG 库 | 依赖 `/explore` + bundle | 改为从落地页/根页提取 bundle 并扫描检索痕迹 |
| recon-04 向量库 | 端口存活即 PRESENT | 主动档增加 HTTP 指纹（Qdrant `healthz`、Chroma `heartbeat`）；被动档保持不可判定 |
| recon-05 agent | 依赖 `/api/labs/DE_01/summary` | 保留；新增 OpenAPI/工具面痕迹 |
| recon-06 MCP 工具面 | 依赖 `/api/secrets/validate` | 保留；新增 `/openapi.json` 工具定义面 |
| recon-07 护栏 | 复用 recon-02 响应 | 无聊天响应时降级为「安全响应头 + 显式不可判定」，不臆造 |

## 7. 清单

- **已核实**：T1–T7；Streamlit 路由；Gradio /config；Ollama /api/tags；Qdrant healthz/readyz；Chroma heartbeat；collect_evidence 契约；Python UTF-8 环境变量。
- **待核实（不纳入本次实现）**：Weaviate readiness 路径（官方页为 JS 渲染，未取到源码级证据）；Milvus :9091/healthz（无源码级复核）；Streamlit 后端 RAG/LLM 的远程探测方式（WebSocket 协议级，超出被动分级）。
- **已排除**：目标存在 `/v1/models`、`/api/config` 等 DVAA 风格接口（实测无响应/404）；将 SPA 回退页计为组件存在（判据禁止）。

## 门禁记录（阶段 1 · G0）

| 基线 | 判定 | 证据（命令 + 摘要） |
|---|---|---|
| B7 | 符合 | 未引入 PyRIT 对象；`grep -rn "pyrit\\." tools/recon_ai` 无命中 |
| B8 | 符合 | 每条结论附来源：现场 curl / GitHub 源码 / 官方文档 / 本仓库代码 |
| B9 | 符合 | 组合取自矩阵 §⑥（garak+Kali+AI）；本次仅 Kali/脚本层 |
| 验收① | 符合 | 结论均可定位到 URL/源码位置（§1–§5） |
| 验收② | 符合 | 版本明确：Streamlit 1.67.0、Gradio/Ollama/Qdrant/Chroma 源码分支、Python 文档 |
| 验收③ | 符合 | §6 七路径逐条映射 |
| 验收④ | 符合 | 待核实项已命名并给出取证方式（§7） |
| 验收⑤ | 符合 | 文档位于 `docs/research/` |

**结论：PASS**（不符合项 0）。复验：`python scripts/check_glossary.py`（阶段 7 复跑）。
