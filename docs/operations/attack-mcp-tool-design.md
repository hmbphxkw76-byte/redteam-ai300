# attack-mcp-tool 模块与接口设计

> **版本** v1.0 · **输入** 规格 v2（issue #130）+ `docs/research/attack-mcp-tool-canonical.md` + 工单 #132–#137
> **性质** 阶段 6 交付物：深层模块边界、公开接口、依赖方向、seam 清单与注入点

## 1. 设计结论（先读）

1. **一个公开入口 + 三缝**：`run_attack()` 是唯一对外入口；三缝为传输（`HttpClient`）、证据写入（`EvidenceWriter`）、截图（`ShotCapture`）。缝数与阶段 2 确认结论一致，未新增第四缝。
2. **两种形态在同一缝内分派**：裸 JSON-RPC 与 agent 会话形态都是「HTTP 请求 + 文本响应」，由 `mcp.py` 的两个客户端解释同一 `HttpClient` 的响应，步骤契约不变。
3. **定级是纯函数**：`grade.py` 不依赖传输、不依赖网络、不导入模型框架；输入是已解析的观测值 + 步骤期望，输出是 `(level, reason)`。
4. **投毒自证走本地 server 对象**：`PoisonedMcpServer` 是可启停的资源对象，不被 `run_attack` 隐式启动，由调用方或 CLI 显式启动，避免隐式网络副作用。

## 2. 模块职责与依赖方向

```
cli.py ──▶ runner.py ──▶ steps.py
                  ├──▶ mcp.py ────▶ transport.py ──▶ model.py
                  ├──▶ poison.py ─▶ model.py
                  ├──▶ grade.py ──▶ model.py
                  ├──▶ evidence.py
                  └──▶ shot.py
```

依赖方向单向，无环。`model.py` 与 `transport.py` 为叶节点，不依赖包内其它模块。

| 模块 | 职责（单一） | 对外接口 | 错误行为 |
|---|---|---|---|
| `model.py` | 值对象与常量（工具描述、工具面、差分、观测、信号、报告数据） | 数据类构造器；`LEVELS`；秘密值正则 | 构造非法值抛 `ValueError` |
| `transport.py` | 唯一网络出口 | `HttpClient.request(method, url, json_body, timeout) → HttpResponse` | 网络失败返回 `HttpResponse.error` 非空，**不抛** |
| `mcp.py` | 协议解释：SSE 解析、JSON-RPC 客户端、agent 会话客户端 | `parse_sse(text) → list[Event]`；`JsonRpcMcpClient.list_tools()/call_tool(name,args)`；`AgentSseClient.probe(lab,prompt) → Turn` | 协议不符返回结构化失败并带原因串，不抛 |
| `poison.py` | 投毒能力：基线/投毒工具面构造、差分、可启停本地 server | `baseline_surface()`；`poisoned_surface()`；`diff_surfaces(a,b)`；`PoisonedMcpServer(host,port).start()/stop()/url` | 端口占用抛 `OSError`（由调用方记录为「不可用」） |
| `grade.py` | 定级纯函数与判据 | `grade(signals) → (level, reason)`；`find_secrets(text)`；`has_admin_scope(telemetry)` | 输入缺失 → `已跳过` + 依据，不抛 |
| `steps.py` | 步骤契约（标识、标题、目标、命令模板、截图钩子） | `STEP_IDS`、`STEP_SPECS`、`steps_for_paths(paths)`、`build_command(step_id,target,mode)` | 未知标识抛 `ValueError` |
| `evidence.py` | 委托共享证据工具写入片段与清单 | `EvidenceWriter.emit(...) → (path, code, err)` | 非 0 退出码原样返回，由 `runner` 决定是否失败 |
| `shot.py` | 截图缝的薄适配：复用既有渲染与无头截图实现 | `make_capture(enabled)`；`capture(...)` | 无浏览器返回空路径（降级「待补录」），不伪造 |
| `runner.py` | 编排：按步骤执行 → 定级 → 落盘 → 汇总报告 | `run_attack(request, runtime=None) → AttackReport` | 单步异常收敛为「未生效/已跳过」并记原因，不中断整轮 |
| `cli.py` | 命令行薄壳 | `main(argv)` | 参数错误退出码 2；质量门失败 1 |

## 3. 公开接口契约

### 3.1 `run_attack(request, runtime=None) → AttackReport`

- **输入** `AttackRequest`：`target`、`mode`（`agent-sse` / `jsonrpc`）、`labs`、`paths`、`step`（空串=全量）、`evidence_dir`、`emit`。
- **输入** `Runtime`（注入点集合，全部有默认实现）：`client`（HttpClient）、`writer`（证据）、`capture`（截图）、`prompt_for`（按步骤给提示词的可调用对象，默认内置）。
- **输出** `AttackReport`：`verdicts`（每步 `step_id`/`path`/`level`/`reason`/`command`/`observation`/`evidence_path`）、`object_graph`、`manifest`、`backend`。
- **错误行为**：未知 `step` → `ValueError`；单一目标不可达 → 该步「已跳过」；证据严格模式失败 → 抛出带片段路径的 `RuntimeError`（证据链断裂不得静默）。

### 3.2 形态分派（不新增缝）

| 形态 | 客户端 | 步骤语义 |
|---|---|---|
| `jsonrpc` | `JsonRpcMcpClient.list_tools()/call_tool()` | mcp-01 枚举；mcp-02/03 对我方 server；mcp-04 差分；mcp-05 越权调用；mcp-06 伪造块；mcp-07 提权调用 |
| `agent-sse` | `AgentSseClient.probe()` | 同一批步骤，观测值取自 `mcp_result.tool_result` + `mcp_telemetry` |

## 4. 注入点与测试替身

| 缝 | 生产实现 | 替身 | 替身保障的 AC |
|---|---|---|---|
| 传输 | `UrllibHttpClient`（标准库，禁用重定向跟随） | `FakeHttpClient(routes)` | AC-03/04/05/11/19 |
| 证据 | `EvidenceWriter`（子进程委托共享工具） | `RecordingWriter`（内存记录，断言契约参数） | AC-12/16 |
| 截图 | 既有无头截图实现（经 `shot.py` 适配） | `NullCapture` / `FakeCapture` | AC-13 |

`Runtime` 默认构造为「生产三件套」，单测通过 `Runtime(client=FakeHttpClient(...), writer=RecordingWriter(), capture=NullCapture())` 全离线运行（AC-17）。

## 5. 对象图（B7 对齐）

报告 `object_graph` 固定字段：

| 字段 | 取值 | 依据 |
|---|---|---|
| `framework` | `pyrit==1.1.0` | ADR-0004 |
| `target` | `HTTPTarget` | 工具面为 HTTP JSON-RPC / SSE，非对话模型端点 |
| `scorer` | `SubStringScorer` | 确定性判据（秘密值形态 + 遥测字段），无 LLM judge（C6） |
| `strategy` | `（无专用策略）` | MCP 无专用攻击策略，以 `HTTPTarget` + 回调对接（调研 §2 S-7） |
| `notes` | 一句说明形态与判据来源 | — |

声明式记录即可，不在运行时导入框架（ADR-0004：CI 以可注入假后端替代真实对象）。

## 6. 权衡与被否决方案

| 方案 | 结论 | 理由 |
|---|---|---|
| 直接复用 `tools/recon_ai` 的传输与证据模块 | **部分采纳**（仅复用截图渲染） | 传输语义不同（SSE 流 vs 单次响应），强行复用会把 recon 的判定耦合进来；截图是纯渲染，复用可消除重复实现（C1） |
| 引入 MCP 官方 Python SDK | **否决** | 引入第三方依赖，违反 AC-17 与 ADR-0003 的零外部依赖取向 |
| 只实现 agent 会话形态 | **否决** | SKILL.md 的 copy/paste 命令是 `tools/list`、`tools/call`；缺 JSON-RPC 形态则命令不可复现（AC-18） |
| 只实现 JSON-RPC 形态 | **否决** | 演练目标不暴露裸端点（调研 T-1），会直接失效 |
| 把投毒 server 隐式启动在 `run_attack` 内 | **否决** | 隐式开监听端口属未声明副作用，且使测试需要真实端口 |
| 定级引入 LLM judge 复核 | **否决** | C6：确定性判据命中即判；LLM judge 既慢又不可复现 |

## 7. 与 ADR 的关系

- **ADR-0004**：PyRIT 仅作对象图基准，`pyrit==1.1.0`；本设计不导入框架，符合「CI 以可注入假后端替代真实对象」。
- **ADR-0005**：设计产物 ≤10KB，门禁记录增量，设计不复述规格正文（本文件只写结构与权衡）。
- 无新增 ADR 需求；无与既有 ADR 的静默冲突。
## 阶段 6 门禁记录（codebase-design）

| 编号 | 检查项 | 依据 | 实测结果 | 判定 |
|---|---|---|---|---|
| B1 | 技能解剖结构 | `python scripts/validate_skill.py` | `PASS：共校验 16 个技能` | 符合 |
| B2 | 术语与决策一致 | `python scripts/check_glossary.py` | `PASS：检查 29 个废弃术语` | 符合 |
| B7 | 对象图无旧版名称 | `grep -nE "orchestrator\|Orchestrator\|AzureOpenAIChatTarget\|XpiaAttack" docs/operations/attack-mcp-tool-design.md` | 无命中；§5 用 `HTTPTarget` + `SubStringScorer` | 符合 |
| B8 | 可追溯性 | 人工判据：§2 每模块含职责/接口/错误；§4 注入点映射 AC；§6 记录被否决方案与理由 | 5 项被否决方案各有理由 | 符合 |
| 验收① | seam 数量与位置明确且与阶段 2 一致 | §1、§4 | 3 缝（传输/证据/截图），未增缝 | 符合 |
| 验收② | 每个公开接口有职责/输入/输出/错误行为 | §2 表 + §3.1 | 10 模块全覆盖 | 符合 |
| 验收③ | 依赖方向单向 | §2 依赖图 | 无环 | 符合 |
| 验收④ | 测试替身可替换外部依赖 | §4 | 三缝各有替身并映射 AC | 符合 |
| 验收⑤ | 与 ADR 冲突显式标注 | §7 | ADR-0004/0005 显式对齐，无冲突 | 符合 |

## 8. 门禁记录（阶段 6 / G0）

**结论：PASS**。不符合项 0。上游复核：`validate_skill` + `check_glossary` 均通过，规格 v2（#130）未被本阶段改动。
