# attack-infra 设计记录（模块与接口 / seam）

> 版本 v1 · 阶段 6（codebase-design）交付物 · 对齐规格 #213 v2 §1/§2 与 §4 差异清单。
> 技能：`skills/attack-infra/SKILL.md`（P1/D9）。事实源：`docs/research/attack-infra-canonical.md`（F/P/R/D）。
> 对象图：**无 PyRIT 对象**（攻击面为基础设施与部署配置，canonical §0 结论 6）；下游影响取证走原生 HTTP。
> seam 决策：4 个，已与用户核对（2026-11-15），与规格 v1 Implementation Decisions 一致。

## 1. 设计目标

把「发现基础设施面 → 利用 → 取证」这条链实现为**可离线重放、可注入外部依赖、单向依赖**的模块集合，落点 `tools/attack_infra/`。三项目标：

1. 判定与网络/命令执行解耦——判据是纯函数，输入是「状态码 + `Content-Type` + 请求体」。
2. 每个步骤的**降级结局**是一等公民（`ABSENT`/`AUTH_REQUIRED`/`BLOCKED`…），不是异常。
3. 证据格式不重实现——一律委托仓库共享证据容器。

## 2. 模块职责与公开接口

| 模块 | 单一职责 | 公开接口（签名级，共 14 模块） | 错误行为 |
|---|---|---|---|
| `model` | 领域类型唯一定义处；不 import 本项目任何模块 | `Outcome`（五值枚举）、`Endpoint`、`Finding`、`StepVerdict`、`RunReport` | 构造非法枚举值 → `ValueError` |
| `transport` | **seam ①**：HTTP 唯一出口 | `Transport.request(method, url, json_body=None, headers=None, timeout=30) -> HttpResponse`；`HttpResponse(status, body, headers, content_type, error, elapsed_ms)` | 网络层失败返回 `error` 非空、`status=0`，不抛异常 |
| `command` | **seam ②**：外部命令唯一出口 | `Command.run(argv: list[str], timeout=60, env=None) -> CommandResult(code, stdout, stderr, elapsed_ms)` | 超时 → `code=-1`、`stderr="timeout"`；不抛异常 |
| `evidence` | **seam ③**：证据落盘委托共享容器 | `EvidenceWriter.emit(step_id, command, output, **kw) -> (path, exit_code, err)` | 子进程失败 → 原样返回退出码，由调用方判 `BLOCKED` |
| `shot` | **seam ④**：截图仅记录计划，不执行 | `ShotPlanner.plan(step_id, url, region) -> ShotPlan(cmd, path, kind)` | 无 URL → `kind="transcript"` 回退 |
| `fingerprint` | 指纹表 + 三元组判据（纯函数） | `detect(resp) -> str | None`；`shape_of(resp)`；`classify(probe, resp) -> str`；`CANDIDATE_PORTS`；`PROBES` | 体不可解析 → `None`（判 `ABSENT`） |
| `inventory` | recon-ai 清单复用：抽端点，不做网络 | `load_endpoints(path)`、`host_ports(values)`、`split_endpoint(value)` | 文件缺失/非法 JSON → `()`，不抛异常 |
| `path_a` | infra-01..03：面发现（含 recon 清单端点）、云存储配置错误、模型服务器暴露/推理 | `discover(ctx) -> StepVerdict`（内嵌 `findings`）、`cloud_misconfig(ctx) -> StepVerdict`、`model_server(ctx) -> StepVerdict` | 无候选端口响应 → `ABSENT(reason=network)` |
| `path_b` | infra-04..05：容器越权、网关凭据线索 | `container(ctx) -> StepVerdict`、`gateway(ctx) -> StepVerdict` | 命令不存在 → `ABSENT(reason=no_tool)` |
| `path_c` | infra-06..08：提权回显归属、影响对照、flag 双通道 | `privesc(ctx) -> StepVerdict`、`impact(ctx) -> StepVerdict`、`flag(ctx) -> StepVerdict` | 缺 AI 日志/flag 通道 → `BLOCKED(reason=evidence_incomplete)` |
| `provenance` | SKILL.md「示意脚本，须记录来源」唯一事实源（infra-02..06 官方 URL + 适配说明） | `SCRIPT_SOURCES`、`provenance(step_id)` | 非示意脚本步骤返回 `None` |
| `report` | 报告渲染（摘要 + 逐步骤表 + 转技能建议 + 复现命令） | `render(report: RunReport) -> str`、`summary(report) -> str` | 空报告 → 输出「无步骤结果」，不抛异常 |
| `runner` | 编排：步骤 → 判定 → 证据 → 汇总 | `run(request: RunRequest) -> RunReport` | 未知 step_id → `ValueError`（CLI 转退出码 2） |
| `cli` | 参数解析与退出码语义 | `main(argv) -> int` | 0 全绿；1 存在非 `EXPLOITED`/`ABSENT` 的阻断项或证据门失败；2 用法错误 |

`ctx`（`RunContext`，定义于 `model`）承载注入依赖：`transport`、`command`、`evidence`、`shot`、`target`、`out_dir`、`allow_inference`、`allow_write`、`timeout`。

## 3. 依赖方向（单向，无环）

```
cli ──> runner ──┬──> path_a ──┐
                 ├──> path_b ──┤──> fingerprint ──> model
                 ├──> path_c ──┘
                 └──> report ─────────────────────> model
path_* ──> transport / command / evidence / shot ──> model
path_a ──> inventory ──> model
```

- `model` 不 import 本项目任何模块；seam 四模块只 import `model`。
- `path_*` 不互相 import；跨路径共享的判定一律下沉到 `fingerprint` 或 `model`。
- `cli` 不被任何模块 import（避免测试经 CLI 绕行）。

## 4. seam 与注入点

| seam | 生产实现 | 测试替身 | 替换方式 |
|---|---|---|---|
| ① 传输 | `UrllibTransport`（显式空 `ProxyHandler({})`，绕开环境代理） | `FakeTransport`（路由表：`"GET /v1/models"` → `HttpResponse`） | 构造 `RunContext(transport=FakeTransport(routes))` |
| ② 执行 | `SubprocessCommand`（`subprocess.run(argv, ...)`，禁 `shell=True`） | `FakeCommand`（`argv` → `CommandResult`） | 同上 |
| ③ 证据 | `EvidenceWriter`（子进程调 `tools/collect_evidence.py`） | `FakeEvidence`（记录入参，返回 `(path, 0, "")`） | 同上 |
| ④ 截图 | `ShotPlanner`（只产出计划字符串） | 无需替身（纯函数） | 同上 |

注入点只有一处：`RunContext`。不在模块内部读环境变量、不读全局配置 → 代理规避、开关策略全部由 `cli` 组装后注入。

## 5. 关键设计决策与权衡

1. **三元组判据下沉为纯函数**：`detect()` 只吃三元组，不吃 URL/端口。理由：端口可配置（RK-1），而「服务是什么」由响应结构决定（canonical P-1、P-3）。
2. **降级是返回值而非异常**：五值 `Outcome` 让「面存在但需凭据」与「面不存在」在测试中可断言；异常仅用于编程错误（未知 step_id、非法枚举）。
3. **按工单切模块**：`path_a/b/c` 与 T2/T3/T4 一一对应，验收矩阵可直接映射到测试文件名。
4. **凭据指纹化在 seam 之上**：`gateway` 产出 `CredentialHint(prefix, length, location)`，避免「先落盘再脱敏」的二次风险。
5. **截图不执行**：与 `recon-ai` 的 `shot` 同构；执行截图会把浏览器/网络耦合进单测（AC-19）。

## 6. 被否决方案

| 方案 | 否决理由 |
|---|---|
| 并入 `recon-ai` 的 `probes.py` | recon 面向 HTTP 资产面，无命令 seam 与 K8s 语义；混入会让 recon 的判据面扩散（B1 五要素边界） |
| 单一 `exploit.py` 聚合 8 步 | 与 T2/T3/T4 工单不对齐，单文件超 600 行，红—绿循环粒度变粗 |
| 在模块内读环境代理变量 | 与 AC-02（默认绕代理）和 AC-19（离线可测）冲突；注入才能让两种策略都测到 |
| 用 `requests`/`httpx` | 违反 AC-23（仅标准库），且引入代理默认行为差异（F-14 陷阱） |
| 引入 PyRIT 评分器做影响判定 | 本技能无对抗性模型对象；`SubStringScorer` 对基础设施回显无判定力（B7 不适用，非豁免） |

## 7. 与 ADR 的关系

- ADR-0005（token 预算）：本设计不新增长文档，设计记录单文件 ≤6KB。
- ADR-0006（三层隔离）：设计不改 `GLOSSARY.md` 以外的共享文件；若阶段 7 需改 `GLOSSARY.md`，推送前过 `checkout_lock.py --check`。
- ADR-0004（PyRIT 1.1.0）：本技能不使用 PyRIT 对象，仅需保证 B7 禁用名零命中（AC-24）。

## 8. 门禁记录（阶段 6）

| 编号 | 检查项 | 依据 | 实测（命令 + 摘要） | 判定 | 结论 |
|---|---|---|---|---|---|
| B2 | 术语与决策一致 | §2.1 | 术语取自 `GLOSSARY.md` + canonical；新增术语于阶段 7 归一（模型服务器/推理网关/降级结论） | 符合 | PASS |
| B7 | 无旧版 PyRIT 对象 | §2.1 | 本文对象图段声明「无 PyRIT 对象」；`grep -n "Orchestrator\|pyrit.orchestrator\|AzureOpenAIChatTarget"` 仅命中 §6 否决理由与 ADR-0004 引用 | 符合 | PASS |
| B8 | 可追溯性 | §2.1 | 每个模块接口对齐 AC 编号；canonical F/P 编号在 §2/§5 引用 | 符合 | PASS |
| AC-① | seam 数量与位置明确且与阶段 2 一致 | §3.6 验收① | §4 四 seam，与规格 v1「已核对」结论一致 | 符合 | PASS |
| AC-② | 每个公开接口有职责/输入/输出/错误行为 | 验收② | §2 表四列齐全（14 模块） | 符合 | PASS |
| AC-③ | 依赖方向单向 | 验收③ | §3 图无回边；`# 依赖方向` 断言由 `validate_skill` 之外的 review 复核 | 符合 | PASS |
| AC-④ | 测试替身可替换外部依赖 | 验收④ | §4 四替身 + 单一注入点 `RunContext` | 符合 | PASS |
| AC-⑤ | 与 ADR 冲突已标注 | 验收⑤ | §7 三条 ADR 逐条标注 | 符合 | PASS |

**阶段结论**：`PASS`（不符合项 0）。复验命令：`python scripts/check_glossary.py && python -m unittest discover -s tests`。
