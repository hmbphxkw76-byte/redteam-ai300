# MCP 服务深度测试验证报告

- 测试对象：`tools/serve_malicious_mcp.py`（本地恶意 MCP server）与实现包 `tools/attack_mcp_tool/`
- 关联范围：`skills/` 20 个技能、`scripts/` 23 个脚本、`tools/` 20 个工具包 + 23 个顶层脚本
- 测试日期：2026-11-26　基线：`main` @ `084d763`（工作树干净）
- **修订（2026-11-26 晚）**：D-1 已修复并补回归用例，D-3 已闭环（覆盖率 94.4%），D-2 已按主线闭环，并修复 D-14（覆盖率工具线程口径）。修复后全量回归全绿，详见《MCP 服务深度测试修复记录》（`docs/operations/mcp-service-deep-test-20261126-fix.md`）。

## 1. 结论摘要

**总体判定：可用（D-1 修复后）。** 首轮测试时功能面与组件面均可用、全仓 1665 例回归 0 失败，但存在 1 项高危缺陷——**裸 JSON-RPC 形态下按文档用法全路径运行会在 mcp-06 中断**，导致 `mcp-07..11` 与 flag 步不执行、证据仅落盘 6/11。该缺陷已于同日修复并加回归用例（§12），当前全路径 11/11 片段落盘、退出码 0。

| 维度 | 结果 | 判定 |
|---|---|---|
| MCP 服务功能（A 组 11 项） | 11/11 PASS | 通过 |
| 边界与异常（B 组 11 项） | 10/11 PASS（1 项失败，4 项健壮性观察） | **不通过**（D-5） |
| 并发与资源（C/D 组 10 项） | 9/10 PASS | **不通过**（用例 D-04 → 缺陷 D-2） |
| 纯函数与协议层（E/G/H 组 10 项） | 10/10 PASS | 通过 |
| 子进程入口（F 组 6 项） | 6/6 PASS | 通过 |
| 集成与稳定性（I 组 12 项） | 10/12 PASS | **不通过**（I-02、I-10） |
| 全仓单元回归 | 1665 例，0 失败，2 跳过 | 通过 |
| 组件与契约校验 | 8/8 脚本 PASS，20/20 技能合规 | 通过 |
| 覆盖率 | 全仓 89.0%（16803/18885，≥ CI 门槛 80%）；attack-mcp-tool 81.1%（＜技能门槛 90%） | 全仓通过 / 技能**不通过** |
| 缺陷统计 | 高 1（已修复）/ 中 3（1 已闭环）/ 低 8 / 流程 1 / 信息 1 | — |

## 2. 环境与口径

| 项 | 值 |
|---|---|
| 操作系统 | Windows 11（10.0.26300） |
| Python | 3.13.14（MSC v.1944, 64bit）；仓库无第三方依赖，仅标准库 |
| CI 目标环境 | ubuntu-24.04 + Python 3.11（`.github/workflows/ci.yml`） |
| 测试方式 | 标准库 `unittest`（`python -m unittest discover -s tests -t .`）；pytest 未安装且不使用 |
| 网络约束 | 全程仅回环 `127.0.0.1`，未访问外网；未接入演练目标（内网 AIVP 地址见本地 `tools/target_profiles.local.json`） |
| 变更约束 | 未修改业务代码与测试代码；所有夹具置于 `evidence/`（gitignored） |

口径说明：本次为**本地对照组**测试，只验证「投毒可构造、可枚举、可留痕」；不验证真实目标 agent 是否被操纵（属编排层职责，规格 v2 R-1）。

## 3. 功能验证（正常场景）

11/11 PASS。A-01 根路径返回 2 工具；A-02 工具面结构正确、隐藏指令存在、`read_file` 权限由 read 放大为 admin；A-03 尾部斜杠容错；A-04 `GET /mcp` → 404（仅接受 POST）；A-05 未知路径 404；A-06 JSON-RPC 2.0 契约与 id 回显；A-07 `read_file` 返回 `{path, content}`、字符串 id 原样回显；A-08 `exfil_send` 计数与载荷长度一致；A-09 `admin_action` 无授权校验返回 `admin=true`（对照组设计）；A-10 `run_command` 回显参数原样（**非真实执行**）；A-11 未知工具 `-32602`。

复现命令：

```bash
python tools/serve_malicious_mcp.py --dump-poison-diff
python -m tools.attack_mcp_tool.cli --step mcp-04 --mode jsonrpc --target http://127.0.0.1:<PORT>/mcp --no-emit
```

## 4. 边界与异常验证

10/11 PASS，另 4 项为健壮性观察。B-01 缺 `arguments` 空值兜底；B-02 畸形 JSON → 400/`-32700`；B-03 未知 method → `-32601`；B-04 空 body 兜底；B-05 非 UTF-8 → 400；B-06 1 MiB 载荷正常；B-08 **FAIL**：`Content-Length: abc` 处理器异常、连接静默关闭（D-5）。观察项：B-07、B-10 慢/截断 body 无响应（D-6）；B-09 `HEAD` 501；B-11 `GET /xtools/list` 亦 200（D-8）。

## 5. 组件验证

| 组件面 | 规模 | 结果 |
|---|---|---|
| Python 编译 | 309 个文件（`check_tools_compile.py`） | 失败 0 |
| 包导入冒烟 | 20 个工具包 | 20/20 成功 |
| 脚本导入冒烟 | 23 顶层 + 23 helper | 41/46 成功，5 项见 D-13 |
| 脚本 `--help` 冒烟 | 46 个脚本 | 36 具 argparse 正常；10 个无参数校验脚本以「执行即校验」方式返回 0 |
| SKILL.md 结构 | 20 个技能（`validate_skill.py`） | 20/20 合规 |
| 证据契约 | `check_evidence_contract.py` | PASS（4 适配器） |
| 契约清单 / 消费者 | `--check` 两项 | PASS |
| 术语一致性 | `check_glossary.py` | PASS（66 个废弃术语） |
| Token 预算 | `check_token_budget.py --check` | PASS（含本报告后复测，热区约 51.8 万 token） |
| 报告资产 | `check_report_assets.py` | PASS |
| 章节覆盖一致性 | 5 组 `verify_*_coverage` | 96.7% / 97.6% / 91.8% / 96.4% / 97.4%，均 ≥ 90% |
| 技能引用字面 | 5 个 `verify_*_skill_refs` + `verify_skill_refs` | 全部 PASS |

## 6. 集成验证

| 编号 | 用例 | 结果 |
|---|---|---|
| I-01 | 全路径 11 步编排（`emit=False`），执行序 `01..07,10,09,11,08` | PASS |
| I-02 | 全路径落盘（`emit=True`） | **FAIL**（D-1） |
| I-03 | 9 个单步证据落盘，`strict` 门禁通过 | PASS |
| I-04 | `report_exam.index.parse_fragment` 逐份解析，`step_id` 全对应 | PASS |
| I-05 | Fragment 结构化字段与原文保留 | PASS |
| I-06 | 每份片段含「关键输出」章节 | PASS |
| I-07 | 重复运行等级一致（第 2 轮） | PASS |
| I-08 | 重复运行等级一致（第 3 轮） | PASS |
| I-09 | runner 启动并在 `finally` 关闭注入 server，端口回收 | PASS |
| I-10 | 已启动 server 注入的幂等性 | **FAIL**（D-2） |
| I-11 | A 路径本地自证封顶「部分生效」，未虚报 | PASS |
| I-12 | flag 步在本地对照组记「已跳过」，证据仍留档 | PASS |

数据流转链路已验证：`poison 工具面 → mcp 客户端解析 → grade 定级 → EvidenceWriter 落盘 → report_exam 解析`，9 份片段无损穿越且字段一致。

## 7. 稳定性与兼容性

| 项 | 数据 |
|---|---|
| 全量回归 | 1665 例 / 247.4s / 0 失败 / 2 跳过（`pyrit 已安装` 分支、`symlink unsupported`） |
| 用例分布 | 20 个技能包与 3 个共享组均有独立用例；`attack-mcp-tool` 87 例（补测后 106 例） |
| 并发隔离 | 24 并发，全部 200，JSON-RPC id 无串号 |
| 吞吐延迟 | 200 请求 / 8 并发 / 0 失败 / 286 QPS；p50 3.6ms，p95 20.6ms，p99 518.4ms（见 D-10） |
| 生命周期 | `stop()` 幂等、端口可复用、上下文管理器正常 |
| 截图通道 | 真实无头 Edge 截图 1280×1000 PNG（21,172 字节），证据引用正确 |
| 路径兼容 | 中文工作目录 `D:\文档\GitHub\redteam-ai300` 全流程无异常 |
| 依赖口径 | AST 顶层 import 复扫：0 个外部第三方模块，与「零依赖」声明一致 |
| 3.11 静态筛查 | 未发现 3.12+ 专属语法/API（`batched`、`typing.override`、`type X =`、`except*`） |

## 8. 缺陷清单

### D-1【高】裸 JSON-RPC 形态全路径运行在 mcp-06 中断（已修复，见《修复记录》）

- **现象**：`python tools/attack_mcp_tool/cli.py --mode jsonrpc --target http://127.0.0.1:<PORT>/mcp`（默认落盘）在 mcp-06 抛 `RuntimeError：证据质量门未通过（三件套不全：关键输出）`，退出码 1；仅落盘 `mcp-01..06` 共 6 份，`mcp-07..11` 与 flag 步未执行。单步 `--step mcp-08` 同样失败。
- **根因**：`_step_mcp_06` / `_step_mcp_08` 的 jsonrpc 降级分支返回仅含 `text` 的 `Observation`，未设 `response_for_shot`；`_render()` 的拼接条件为 `obs.text and obs.raw`，raw 为空时整段不输出，于是证据「关键输出」为空。`_emit()` 使用 `outcome.response_for_shot or _render(...)`，取到空串后严格门禁失败。
- **影响**：与 `run_attack` docstring 承诺的「单步失败不中断整轮」相悖；`cli.py` 头注的对照组用法在无 `--step` 时不可用；演练/考试取证在 B、flag 路径上无法完成。
- **建议**：`_render()` 增加「有 text 无 raw」分支（如 `if obs.text and not obs.raw: parts.append(obs.text)`），或在这两处降级分支显式设 `response_for_shot=obs.text`；补用例「jsonrpc + emit=True 全路径必须成功」。

### D-2【中】`start()` 非幂等，Windows 静默双绑定并泄漏套接字（已闭环）

- **现象**：向 `Runtime.server` 注入已启动实例时，`_Session.ensure_server()` 会二次调用 `start()`。同端口二次绑定在 Windows 上成功（`allow_reuse_address=1`），旧 `ThreadingHTTPServer` 被覆盖且不关闭，`stop()` 后端口仍被占用（复现 `WinError 10048`）。
- **影响**：①本机任意进程可在同端口另起监听，存在端口劫持风险；②`mcp-02` 依赖 `OSError` 的「本地端口不可用」降级分支在 Windows 永不触发（Linux 上会触发），跨平台行为不一致。
- **建议**：`start()` 首行 `if self._server is not None: return self`；`ensure_server()` 仅在未启动时调用 `start()`；Windows 设置 `SO_EXCLUSIVEADDRUSE`（或按平台关闭 `allow_reuse_address`）。

### D-3【中】attack-mcp-tool 覆盖率 81.1%，低于 90% 技能目标（已闭环，见《修复记录》）

- **数据**：总计 1380/1701 = 81.1%（`--min 90` 退出码 1）。分模块：`steps.py` 98.7%、`transport.py` 92.7%、`mcp.py` 91.3%、`model.py` 88.2%、`evidence.py` 88.9%、`cli.py` 82.9%、`shot.py` 81.5%、`grade.py` 78.9%、`runner.py` 74.5%、`poison.py` 68.6%。对照：全仓 `--target all` 为 16803/18885 = 89.0%，高于 CI 的 80% 门槛。
- **说明**：CI 仅执行 `measure_coverage.py --target all --min 80`，技能级 90% 门槛未纳入门禁；`poison.py` 的 HTTP 处理器分支（GET/POST 各异常路径）是覆盖洼地，本次由外部夹具补充验证而非仓库用例。
- **建议**：为 server 端点补用例（畸形 body、未知 method、未知工具、大载荷、并发）；CI 增 `--target attack-mcp-tool --min 90` 独立步骤（按 C1 以独立步骤接入，不改并发长行）。

### D-4【中】SKILL.md 未覆盖 mcp-09/10/11

- **现象**：`skills/attack-mcp-tool/SKILL.md`（87 行）仅定义 mcp-01..mcp-08；实现与用例 `STEP_IDS[8:] == ("mcp-09","mcp-10","mcp-11")` 已扩至 11 步（沙箱逃逸、MCP Apps UI 投毒、工具链注入）。
- **影响**：按 SKILL.md 执行将漏掉 3 个步骤；「步骤标识属对外契约」的单向变更会削弱可复核性。
- **建议**：SKILL.md 增补三条执行体与对应质量门要求，或显式引用 Ch7 设计文档并在质量门中登记。

### D-5【低】`do_POST` 未校验 `Content-Length`，处理器异常未兜底

- **现象**：`Content-Length: abc` → `int()` 抛 `ValueError` 逃逸至 `socketserver`，客户端收不到任何响应；stderr 打印完整 traceback。`log_message` 已静默，但 `handle_error` 未覆盖。
- **建议**：`int()` 包裹 try/except，非法值返回 400 + `-32600`；重写 `handle_error` 记结构化日志，避免证据通道被 traceback 污染。

### D-6【低】无读超时，截断/慢 body 可长期占用线程

- **现象**：声明 100 字节仅发 5 字节并保持连接，服务端 1.5s 内无任何响应（阻塞在 `rfile.read`），客户端 2s 超时。
- **建议**：设置 `_Handler.timeout`（如 30s），超时返回 408 或主动断开。

### D-7【低】门禁失败仍落盘片段

- **现象**：D-1 复现中 `mcp-06.md` 虽门禁失败仍被写入；`collect_evidence.py --strict` 失败同样生成文件。
- **影响**：后续报告可能误引无效片段。
- **建议**：门禁通过后再原子写入（临时文件 + rename），或失败时以 `.invalid` 后缀隔离。

### D-8【低】GET 路径用 `endswith("tools/list")` 宽松匹配

- **现象**：`GET /xtools/list` 亦返回 200 工具面。
- **建议**：精确匹配 `{"/", "/tools/list"}`。

### D-9【低】启动提示未 flush，子进程场景不可观测

- **现象**：`--port 0` 子进程启动后 stdout 采用块缓冲，父进程 `readline()` 阻塞至进程结束才能读到启动行。
- **建议**：`print(..., flush=True)`。

### D-10【低】监听 backlog 默认 5，8 并发出现 500ms 级长尾

- **现象**：200 请求 / 8 并发，p99 = 518.4ms，与 TCP 重传计时一致；0 失败。
- **建议**：`request_queue_size = 128`（`ThreadingHTTPServer` 子类覆盖）。

### D-11【低】覆盖率清单漏 `escape.py` / `chain.py` / `uihost.py`

- **现象**：`tools_manifest.json` 的 `coverage_targets.attack-mcp-tool` 仅含 10 模块，而 mcp-09/10/11 实际调用上述三模块，度量存在盲区。
- **建议**：补入清单，使 11 步实现全部受覆盖率约束。

### D-12【流程】13/20 技能缺主线留痕

- **现象**：`validate_skill_mainline.py` 总计 BLOCKED（`--strict` 退出 1）。缺失项：`attack-ai-agent`、`attack-mcp-tool`、`attack-multi-agent`、`attack-rag`、`decoy-detect`、`foothold-traditional`、`loot-manage`、`osai-exam-orchestrator`、`recon-ai`、`report-exam`、`threat-model`（缺 spec v1/v2 + 阶段门禁 0/10）；`attack-embeddings`、`attack-infra` 仅缺阶段门禁记录。PASS 者 7 个。
- **说明**：属流程合规缺口而非运行缺陷；`attack-mcp-tool` 的设计与验证文档位于 `docs/operations/attack-mcp-tool-*.md`，与校验器期望的 `docs/specs/<skill>-spec-v{1,2}.md` 及 `docs/operations/<skill>-gate-stage*.md` 命名不一致。
- **建议**：按主线规范补齐或迁移留痕；若沿用旧命名，需在 `validate_skill_mainline.py` 中登记例外清单，避免门禁长期红灯。

### D-13【信息】5 个 `verify_*_coverage.py` 依赖脚本目录 sys.path

- **现象**：以脚本方式运行正常（均退出 0），但从仓库根 `import` 时报 `ModuleNotFoundError: measure_coverage`。
- **建议**：改为包内相对导入或显式 `sys.path` 注入，提升可测试性。

### D-14【低】覆盖率工具不追踪工作线程，线程化服务覆盖率被系统性低估（已修复，见《修复记录》）

- **现象**：`measure_coverage.py` 只用 `sys.settrace`；`ThreadingHTTPServer` 的请求处理器运行在子线程，故 `poison.py` 的 `do_GET` / `do_POST` / `_send` / `log_message` 即使被真实 HTTP 用例覆盖，仍被计为未覆盖。
- **数据**：同一测试集下 `poison.py` 68.6% → 追加 `threading.settrace` 后 95.3%；`attack-mcp-tool` 总计 81.1% → 92.1%。
- **影响**：线程化服务的覆盖率被低估约 27 个百分点，易误导「为凑数补无效用例」。
- **建议（已实施）**：`measure()` 内同时注册 `threading.settrace(tracer)`，并在 `finally` 中撤销。

## 9. 未覆盖项与残余风险

| 项 | 原因 | 风险 |
|---|---|---|
| Python 3.11 / Linux 实跑 | 本机仅有 3.13；CI 目标为 3.11 + ubuntu | 平台差异（D-2 的 SO_REUSEADDR 语义、路径与时序）未在目标环境复现 |
| 真实演练目标（AIVP） | 本次限定本地对照组，未联网 | 目标侧护栏、SSE 会话、面板校验预言机未实测 |
| 报告工具链（pandoc/typst/7z） | 未生成 PDF/归档，避免污染仓库 | 渲染链路未验证 |
| `verify_evidence.py` 全流程 | 需完整考试报告与 PDF/7z 产物 | 单片段目录下如实报 blocking + `dry-run 不可提交`（门禁行为正确，非缺陷） |
| 主线阶段 1–11 全流程复跑 | 非本次任务范围 | 留痕缺口见 D-12 |

## 10. 修复优先级建议

1. **D-1（必修）**：阻断文档化用法，影响取证完整性；改动小、回归面清晰。
2. **D-2（必修）**：涉及端口安全与跨平台一致性，影响 `mcp-02` 降级契约。
3. **D-3（建议本迭代）**：补 server 端点用例，同时把技能级 90% 门槛接入 CI。
4. **D-4（建议本迭代）**：文档与契约同步，避免执行体漏步。
5. D-5 至 D-13：可随下次触碰该模块时一并处理，其中 D-8、D-9 为一行级修复。

## 11. 证据索引

夹具与原始日志均位于 gitignored 的 `evidence/mcp-deep-test/`：`harness.py` + `results.json` + `harness.log`（A–H 组）、`integration.py` + `integration-results.json` + `integration.log`（I 组）、`unittest_verbose.log`（全量回归）、`coverage.log` / `coverage-all.log`、`mainline.log`（留痕校验）、`cli-repro/`（D-1 复现产物）、`shot/mcp-04-transcript.png`（截图通道）。可按第 3 节命令重放；本报告不含目标 IP、凭据或 flag 明文。

## 12. 修复记录

D-1、D-3、D-14 的补丁、回归用例、补测清单与验收结果见独立文档：
`docs/operations/mcp-service-deep-test-20261126-fix.md`。
