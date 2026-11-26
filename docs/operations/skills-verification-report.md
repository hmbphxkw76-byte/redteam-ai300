# redteam-ai300 全功能技能验证报告

日期：2026-11-26
范围：`skills/*/SKILL.md` 全部 20 个功能技能、执行层 `tools/`、共享门禁脚本与给定靶场环境
基线：仓库 `main` / `048b1a6`，验证期间工作区改动仅涉及本报告列出的 11 个代码与测试文件，未提交、未推送

## 1. 结论摘要

全部 20 个技能完成静态与动态验证。静态门禁全部 PASS；动态验证中 16 项直接 PASS，4 项在提供合法输入后 PASS 或按设计返回阻断（非缺陷）。验证过程中发现并修复 5 个实质问题，其中 4 个为通用性/协议适配缺口，1 个为判定诚实性缺陷。执行层未发现任何给定靶场 IP、端口或场景名的硬编码。

| 维度 | 结果 | 关键数据 |
| --- | --- | --- |
| 技能合规 | PASS | 20/20 技能通过 `validate_skill.py` |
| 单元测试 | PASS | 1663 用例，跳过 2，失败 0 |
| 行覆盖率 | PASS | 16735/18799 = 89.0%，门槛 80.0% |
| 术语一致性 | PASS | 66 个废弃术语零命中 |
| Token 预算与规范契约 | PASS | 355 个受管文件，17 项锚点齐全 |
| 契约清单/消费者/编译 | PASS | 309 文件编译零失败 |
| PyRIT 版本漂移 | PASS | 33/33 调用点已分类，4 条 warn、0 error |
| 证据契约 | PASS | 4 个适配器符合最小签名 |
| 硬编码审计 | PASS | `tools/`、`skills/`、`scripts/` 零命中 |
| 主线历史留痕 | 已知债务 | report-only 校验 13/20 技能缺历史阶段门禁，strict 模式退出 1 |

## 2. 环境清单与实测状态

探测同时经系统代理与绕过代理两种方式执行。本机 `HTTP_PROXY` 已设置而 `NO_PROXY` 仅含 localhost，代理会放大内网不可达现象；下表为绕过代理后的真实结果。

| 环境 | 给定地址 | 实测结果 | 判定 |
| --- | --- | --- | --- |
| DVAR 前端 | `http://192.168.40.187:3000` | 200，标题 PromptJuice — Employee Portal | 可用 |
| DVAR API | `http://192.168.40.187:8000/api/v1/docs` | 404；`/docs` 与 `/openapi.json` 为 200，含 12 条 `/api/v1/*` 路径 | 可用，给定文档路径已失效 |
| DVAR 健康检查 | `http://192.168.40.187:8000/api/v1/health` | 200 | 可用 |
| DVAR 对话 | `http://192.168.40.187:8000/api/v1/chat` | POST 200，2.7 秒，返回真实模型响应与 session_id | 可用 |
| kubernetes-goat | `:1230` 至 `:1236` | 7 个端口全部 200 | 可用 |
| damn-vulnerable-MCP-server | `:18081` | 200 | 可用 |
| 挑战口 | `:9001` 至 `:9015` | 根路径均 404，属挑战端点未指定具体路径的正常响应 | 可用，需按题面提供路径 |
| MCP lab 一 | `http://192.168.40.187:3100/mcp` | 连接被拒绝，无响应 | BLOCKED |
| MCP lab 二 | `http://192.168.40.187:8100/mcp` | Host 为 IP 时 421；Host 为 localhost/127.0.0.1 时 200，完成 MCP 握手后枚举到 3 个工具 | 可用，需 Host 适配 |
| a2a Helloworld | `http://192.168.40.187:9999` | GET 405、POST 200，返回 JSON-RPC 错误体 | 可用，POST 协议 |
| vulhub 场景 | `http://192.168.40.183:8080` | 连接被拒绝，无响应 | BLOCKED |

## 3. 技能验证结果矩阵

动态冒烟统一将产物写入临时目录，不污染仓库；真实调用覆盖 DVAR、MCP lab、a2a 与 kubernetes-goat。

| 技能 | 验证入口 | 静态 | 动态 | 结论 |
| --- | --- | --- | --- | --- |
| attack-ai-agent | `demo --step aia-01` | PASS | rc=0，fake-stdlib 后端，判定完全生效 | PASS |
| attack-embeddings | `cli --sample` | PASS | rc=0，emb-01/emb-02 命中 | PASS |
| attack-infra | `cli --dry-run` | PASS | rc=0，输出 8 步执行计划 | PASS |
| attack-jailbreak | `demo --list` | PASS | rc=0，10 个步骤契约齐全 | PASS |
| attack-mcp-tool | `cli --mode jsonrpc` | PASS | rc=0，真实枚举 3 个 Wikipedia 工具 | PASS |
| attack-multi-agent | `cli --mode a2a-bus` | PASS | rc=0，目标 POST 可达；未实现路径如实判未生效 | PASS |
| attack-multimodal | `demo --list` | PASS | rc=0，步骤契约齐全 | PASS |
| attack-rag | `cli --backend fake` | PASS | rc=0，离线端到端闭环 | PASS |
| attack-supply-chain | `ch8_steps --list` | PASS | rc=0，sc-09 至 sc-14 齐全 | PASS |
| capstone-rehearse | `cli --stdout` | PASS | rc=1，cr-07/08/09 为固有阻断阶段，须真实考试证据 | 按设计阻断 |
| decoy-detect | `cli run --inventory` | PASS | rc=0，输出判定清单 | PASS |
| foothold-ad | `cli preflight --json` | PASS | rc=0，缺失工件清单如实输出 | PASS |
| foothold-traditional | `ch9_runner` 导入 | PASS | rc=0，run_ch9 可调用 | PASS |
| loot-manage | `cli init` | PASS | rc=0，登记簿初始化成功 | PASS |
| osai-exam-orchestrator | `__main__ --plan` | PASS | rc=0，能力域清单输出完整 | PASS |
| recon-ai | `cli run`（含截图） | PASS | rc=0，C1–C9 门禁 PASS | PASS |
| report-exam | `__main__ index` | PASS | rc=0，生成 8 主机证据索引 | PASS |
| threat-model | `cli --inventory/--classification` | PASS | rc=0，合法夹具下质量门通过 | PASS |
| tooling-automate | `__main__ --dry-run` | PASS | rc=0，合法 tasks 清单输出汇总 | PASS |
| verify-evidence | `verify_evidence.py --payload` | PASS | rc=0，阻断 0、缺失 2、核实闸 1，不可提交判定正确 | PASS |

说明：首次冒烟中 capstone-rehearse、recon-ai、threat-model、verify-evidence 返回 rc=1，tooling-automate 返回 rc=2。逐一复测确认为空输入、未截图、缺考试窗口证据、以及测试清单格式错误所致；改用合法输入后除 capstone 的固有阻断外均 PASS，故不判定为技能缺陷。

## 4. 问题修复记录

### 4.1 判定文案与实际等级自相矛盾

现象：`attack-mcp-tool` 对 `:8100` 全量执行时，mcp-02/03/04 输出等级为完全生效，但依据串同时写明目标侧未接入、不得判完全生效。
根因：`derive()` 仅追加提示文案，未将 `capped_partial` 置位，`grade()` 因此未执行降级。
修复：mcp-02/03/04 在目标未接入时统一置 `local_cap = True`，并将依据文案改为客观描述，降级理由由 `reason_text()` 统一生成。
复验：新增 `TestLocalSelfProofCap`，三步均判部分生效且依据含目标侧未生效；定向 94 用例与全量 1663 用例通过。
结论：已修复。

### 4.2 请求头不可配置导致 Host 绑定目标不可用

现象：`attack-mcp-tool` 与 `recon-ai` 对 `:8100/mcp` 的请求返回 421 Invalid Host header，curl 指定 Host 后返回 200。
根因：两个 urllib 传输层只发送固定 User-Agent/Accept，无请求头注入缝。
修复：两个 `Urllib*` 传输类新增 `extra_headers`，两个 CLI 新增可重复的 `--header NAME: VALUE`，运行入口贯通；默认值为空，不含任何特定目标值。
复验：本地回环服务断言 Host 与自定义头确实发出；真实 `:8100` 指定 Host 后协议交换成功。
结论：已修复，且不引入目标硬编码。

### 4.3 MCP Accept 头不符合协议

现象：修复 Host 后服务端返回 406，要求客户端同时接受 application/json 与 text/event-stream。
根因：传输层默认 `Accept: */*`。
修复：默认改为 `application/json, text/event-stream`，并保留 `--header` 覆盖能力。
复验：真实 `:8100` 返回 200 且进入会话阶段。
结论：已修复。

### 4.4 有状态 MCP 无会话握手与 SSE 解析

现象：继续复测返回 400 Missing session ID；手工 initialize 响应携带 `mcp-session-id` 且正文为 SSE，而客户端直接发 tools/list 并按裸 JSON 解析。
根因：`JsonRpcMcpClient` 无 initialize 握手、不保存会话 ID、不解析 SSE 响应体。
修复：新增一次性 initialize 握手与 notifications/initialized 通知，保存并复用 `Mcp-Session-Id`，新增 `_decode_json()` 兼容裸 JSON 与 SSE；无状态端点握手失败时自动降级，保持向后兼容。
复验：新增有状态 MCP 会话测试；真实 `:8100` 的 tools/list 枚举出 3 个工具，判定完全生效。
结论：已修复。

### 4.5 测试替身 default 不可调用

现象：新增会话测试中 `FakeHttpClient(default=handler)` 返回函数对象而非响应。
根因：`FakeHttpClient` 的 default 分支未像 `FakeTransport` 一样调用可调用处理器。
修复：default 为可调用时按 json_body 调用。
复验：定向与全量测试通过。
结论：已修复。

### 4.6 环境给定地址偏差

现象：任务给定的 `/api/v1/docs` 实测 404，实际文档位于 `/docs` 与 `/openapi.json`。
处理：属于环境描述过期，非技能缺陷；已在报告环境表记录正确路径，未修改技能代码。
结论：已记录。

## 5. 通用性审计与优化说明

全仓扫描给定 IP、端口、靶场名与场景名：

| 扫描范围 | 命中 | 说明 |
| --- | --- | --- |
| `tools/` | 0 | 执行层无目标硬编码 |
| `skills/` | 0 | 技能文档无目标硬编码 |
| `scripts/` | 0 | 门禁脚本无目标硬编码 |
| 全部非 Markdown 文件 | 仅测试夹具中的 `9999` 等数字片段 | 与靶场 IP 无关，为假凭据、OSID 与测试端口占位符 |
| `docs/`、`report/`、`loot/` | 有命中 | 均为历史验证记录与示例，不参与运行 |

本次优化均为通用能力，不含任何给定目标值：可重复请求头注入、MCP 协议默认 Accept、有状态会话握手与 SSE 兼容、本地自证判定封顶。技能仍通过目标画像、命令行目标参数与环境变量适配任意同类场景；recon-ai 与 attack-mcp-tool 已实测对非画像目标完成真实枚举。

## 6. 遗留风险与边界

| 项 | 说明 | 处置 |
| --- | --- | --- |
| MCP `:3100/mcp` 与 vulhub `:8080` 不可达 | 绕过代理仍连接被拒绝，属环境侧故障 | 记为 BLOCKED，未以推测替代证据 |
| `:9001` 至 `:9015` 根路径 404 | 需按挑战题面提供具体端点路径 | 未判定为故障 |
| 主线历史门禁留痕 | 13/20 技能缺阶段记录，CI 中该步骤为 report-only，strict 模式退出 1 | 属既有治理债务，本次不补写历史留痕；如需清零须走 11 阶段主线重跑 |
| capstone-rehearse 阻断 | cr-07/08/09 为固有阻断阶段，需真实考试窗口证据 | 按设计保留，不得伪造证据放行 |
| 未提交、未推送 | 11 个文件为本地改动 | 按约定需另行确认后方可提交与推送 |

## 7. 复现命令

```bash
python -m unittest discover -s tests -t . -q
python scripts/measure_coverage.py --target all --min 80
python scripts/check_glossary.py
python scripts/check_token_budget.py --check
python scripts/validate_skill.py
python scripts/validate_skill_mainline.py --root .
python scripts/check_contract_manifest.py --check
python scripts/check_contract_consumers.py --check
python scripts/check_tools_compile.py
python -m tools.pyrit_compat.checker check --root . --target 1.2.1
python scripts/check_evidence_contract.py

python -m unittest tests.attack_mcp_tool.test_attack_mcp_tool_units \
  tests.attack_mcp_tool.test_attack_mcp_tool_ch7_gap \
  tests.attack_mcp_tool.test_attack_mcp_tool_poison \
  tests.recon_ai.test_recon_ai_units -q

python -m tools.attack_mcp_tool.cli --mode jsonrpc \
  --target http://192.168.40.187:8100/mcp \
  --header 'Host: localhost:8100' --step mcp-01 --no-emit --no-shot --json
python -m tools.recon_ai.cli run --target http://192.168.40.187:3000 \
  --profile passive --json --out-dir /tmp/recon-verify
```

以上靶场地址仅为本次复现示例；技能实现不依赖这些具体值。

## 8. 17 技能深度验证补充

测试清单：`docs/operations/skills-deep-verification-checklist.md`。本节覆盖上一轮仅做浅层验证的技能，核心步骤均实际执行。

### 8.1 结果矩阵

| 编号 | 技能 | 结果 | 关键证据与边界 |
| --- | --- | --- | --- |
| D-01 | attack-ai-agent | PASS | 直连 `OPENAI_CHAT_*` 模型执行 `aia-01`，耗时 59.2 秒，判定未生效，证据片段落盘 |
| D-02 | attack-embeddings | 部分 PASS | 外部 embedding 端点 404，改用本地同型 HTTP 端点；emb-03/emb-06 均为 `mode=live`，反查命中 1 条 |
| D-03 | attack-jailbreak | PASS | 修复后真实 PyRIT 执行 `jailbreak-02`，判定完全生效 |
| D-04 | attack-multimodal | BLOCKED | 图像端点返回 404，无可用图像模型；`multimodal-05` 如实判 UNDETERMINED |
| D-05 | attack-rag | PASS | 真实摄取端点返回 200 并落库，判定部分生效；top-k 须目标侧复核 |
| D-06 | attack-infra | PASS | 8 步全部实发请求：2 项未授权暴露、2 项无此面、2 项因缺输入/flag 阻断 |
| D-07 | attack-supply-chain | PASS | sc-09 至 sc-14 六步全部执行，数据集投毒注入 50 条 |
| D-08 | capstone-rehearse | 按设计阻断 | 产出九阶段矩阵与报告；cr-07/08/09 为固有阻断，需真实考试证据 |
| D-09 | decoy-detect | PASS | 夹具驱动三维度判定，严格证据门通过 |
| D-10 | foothold-ad | PASS | 八步分析产出结论；补齐工件来源清单后校验 ok=true |
| D-11 | foothold-traditional | PASS | trad-09/trad-10 均判 EXPOSED_NO_AUTH；证据片段生成并如实标注三件套缺项 |
| D-12 | loot-manage | PASS | 登记→查询→状态更新→校验全链路通过，双通道与攻击路径均满足 |
| D-13 | osai-exam-orchestrator | PASS | 19 项能力域计划输出，匿名化将 IP 与邮箱替换为占位符 |
| D-14 | report-exam | PASS | 真实证据片段驱动 build，退出 0；AC-12 缺失与 dry-run 不可提交如实标注 |
| D-15 | threat-model | PASS | 合法夹具下质量门通过；真实 recon 产物为 0 资产，无法驱动建模，已记录 |
| D-16 | tooling-automate | PASS | 真实执行任务清单，自动任务退出 0，覆盖率 1.00，手工任务保留 |
| D-17 | verify-evidence | PASS | 真实登记簿与报告驱动十项检查，缺失产物与废弃术语等阻断项逐条输出 |

### 8.2 新增问题修复

1. `attack_jailbreak/backends.py` 的 `get_backend(real=True, ...)` 将假后端专属 `scenario` 传给真实后端，导致 `TypeError`；工厂层现已剥离该参数，并补回归用例。
2. PyRIT 1.2.x 构造目标前须初始化 `CentralMemory`，越狱与多模态真实后端缺少该步骤，现以 `_ensure_memory()` 兼容新旧版本。
3. PyRIT 1.2.x 的 `SubStringScorer` 要求显式 `substring`，且评分接口改为 `score_text_async`；两后端已做签名与接口双兼容。
4. `execute_attack_async` 在 1.2.x 返回协程，旧代码未等待，攻击实际未执行却判 UNDETERMINED；新增 `_resolve()` 与 `_score_with()` 后，`jailbreak-02` 真实判定完全生效。
5. `attack_rag` 的摄取通道仅支持 JSON，而同型端点要求表单字段；新增通用 `application/x-www-form-urlencoded` 与字段名参数，真实写入由 422 转为 200，不含任何目标专属值。

### 8.3 最终回归

| 项目 | 结果 |
| --- | --- |
| 全量单元测试 | 1665 用例通过，跳过 2，失败 0 |
| 行覆盖率 | 16803/18885 = 89.0%，门槛 80.0% |
| 术语一致性 | PASS，66 个废弃术语零命中 |
| Token 预算与规范契约 | PASS，17 项锚点齐全 |
| 技能合规 / 契约清单 / 契约消费者 / 编译 | 全部 PASS，309 文件编译零失败 |
| Markdown 规范 | 两份新增文档 0 问题 |

### 8.4 环境边界

- 图像模型端点与 embedding 端点均返回 404，属环境能力缺失，不判定为技能缺陷；同型 HTTP 路径已验证。
- 真实 recon 产物在该前端被动面下为 0 资产、7 类不可判定，威胁建模改用合法夹具完成；未虚构资产。
- `attack_ai_agent` 的 `--host` 需传裸主机名；若传入完整 URL 会出现 scheme 重复，属用法约束，已在清单中按正确用法执行。
