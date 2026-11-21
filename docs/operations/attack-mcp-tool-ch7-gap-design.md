# attack-mcp-tool Ch7 增量 — 模块与接口设计

> **版本** v1.0 · **输入** 规格 v2（issue #293）+ 工单 #315..#320 + 调研 `docs/research/attack-mcp-tool-ch7-gap.md`
> **性质** 阶段 6 交付物：深层模块边界、公开接口、依赖方向、seam 清单与注入点
> **行为唯一来源** `skills/attack-mcp-tool/SKILL.md`（本设计不改写）

## 1. 设计结论（先读）

1. **一个公开入口 + 既有三缝 + 1 新缝**：`run_attack()` 仍为唯一对外入口；既有三缝（传输 `HttpClient`、证据 `EvidenceWriter`、截图 `ShotCapture`）不变；新增 1 个「UI/资源交互缝」（`UiHostClient`），置于 runner 高层，测试可注入假 host（阶段 2 用户已核对认可）。
2. **新步骤标识 mcp-09/10/11**（沙箱逃逸 / MCP Apps UI 投毒 / 工具链 SSTI），与既有 mcp-01..08 并列，不改写其契约、不改 STEP_IDS 既有值。
3. **定级仍为纯函数**：`grade.py` 扩展 3 个 step_id 的 `derive()` 分支，仍无 IO/网络/框架依赖；本地 mock 自证经 `capped_partial` 封顶。
4. **诚实边界**：目标侧无对应 lab 时，一律本地 mock 自证 + note 标注「目标侧未验证」，等级封顶「部分生效」；不伪造截图、不编造 flag。

## 2. 模块职责与依赖方向

```
cli.py ──▶ runner.py ──▶ steps.py（新增 mcp-09/10/11 StepSpec）
                  ├──▶ mcp.py ──▶ transport.py ──▶ model.py
                  ├──▶ poison.py ──▶ model.py（扩展 UI 资源构造）
                  ├──▶ escape.py（新）──▶ model.py（路径穿越/symlink 判据，纯函数+注入 FS）
                  ├──▶ chain.py（新）──▶ model.py（三工具串联载荷构造，纯字符串）
                  ├──▶ uihost.py（新缝）──▶ model.py（resourceUri/postMessage 取证）
                  ├──▶ grade.py ──▶ model.py（新增 3 分支）
                  ├──▶ evidence.py / shot.py（复用）
```

依赖方向单向无环；`model.py`/`transport.py` 仍为叶节点。新模块 `escape.py`/`chain.py`/`uihost.py` 只依赖 `model.py`，不互相依赖。

| 模块 | 职责（单一） | 对外接口 | 错误行为 |
|---|---|---|---|
| `steps.py`（改） | 新增 3 条 StepSpec 与提示词模板 | `STEP_SPECS`/`STEP_IDS`（既有值不变，追加新值） | 未知标识抛 `ValueError`（沿用） |
| `uihost.py`（新） | UI 资源构造 + postMessage/AppBridge 取证（新缝） | `UiHostClient.probe(resource_uri, tool_desc) → Observation`；`make_ui_resource(uri) → dict` | 假 host 不可用返回结构化失败并带原因 |
| `escape.py`（新） | 路径穿越 + symlink 判据（注入 FS 可离线） | `prefix_bypass(path, allowed) → bool`；`symlink_escape(path, allowed, fs=None) → bool`；`realpath_fix_check(path, allowed, fs=None) → bool` | 路径参数非法返回 False + detail |
| `chain.py`（新） | store→aggregate→render 载荷构造与探针 | `build_chain(stage, payload) → dict`；`ssti_probe(expr) → str`；`cmd_inject(sep, cmd) → str` | 载荷非法返回空串，不抛 |
| `poison.py`（改） | 增 UI 资源 tool 描述符与 shadow 变体 | `ui_poisoned_surface()`；`shadow_surface()`；沿用 `diff_surfaces` | 沿用既有 |
| `grade.py`（改） | 新增 mcp-09/10/11 定级分支 | 沿用 `grade()`/`derive()` | 输入缺失 → 已跳过 + 依据 |
| `runner.py`（改） | 新增 3 个 handler + Runtime 增 `uihost` 注入点 | `run_attack()`（签名不变）、`Runtime.uihost` 字段 | 单步异常收敛为未生效/已跳过 |

## 3. 公开接口契约

### 3.1 `run_attack(request, runtime=None) → AttackReport`（不变）

- `AttackRequest` 增可选 `paths` 值 `"D"`(UI)/`"E"`(逃逸)/`"F"`(工具链)；既有 A/B/C 默认行为不变。
- `Runtime` 增 `uihost: Optional[UiHostClient] = None`（默认生产实现，单测注入假 host）。
- 输出 `AttackReport` 结构不变；新步骤 verdict 追加进 `verdicts`，既有步骤顺序不变。

### 3.2 注入点与测试替身

| 缝 | 生产实现 | 替身 | 保障 AC |
|---|---|---|---|
| 传输（既有） | `UrllibHttpClient` | `FakeHttpClient` | AC-01/05/07/09 |
| 证据（既有） | `EvidenceWriter` | `RecordingWriter` | AC-11 |
| 截图（既有） | 无头截图实现 | `NullCapture` | AC-11 |
| UI/资源交互（新） | `UiHostClient`（本地 mock host） | `FakeUiHost` | AC-02/03/04/10 |

## 4. 对象图（B7 对齐）

沿用既有 `OBJECT_GRAPH`：`pyrit==1.1.0` / `HTTPTarget` / `SubStringScorer` / 无专用 MCP 策略。新增能力以标准库实现，不引入 pyrit 运行时依赖，不在 CI 导入框架（ADR-0004）。

## 5. 权衡与被否决方案

| 方案 | 结论 | 理由 |
|---|---|---|
| 新增 3 个独立 seam | 否决 | 仅 UI 渲染需新缝；路径/工具链可复用 HttpClient + 注入 FS，压到 1 个新缝 |
| 用 Jinja2 运行时执行 SSTI 载荷 | 否决 | 引入三方依赖违反 AC-17/ADR-0003；载荷以字符串构造，探针经目标侧回显判定 |
| 改写 mcp-04 既有差分实现 | 否决 | 保护 S2 夹具机器判据与 report-exam 复用；以新 ctx 标记增强而非改写 |
| 目标侧无 lab 时跳过新步骤 | 否决 | 本地 mock 自证仍有技术价值，但封顶部分生效并标注，不夸大 |
| 引入 MCP ext-apps SDK | 否决 | 三方依赖 + 考试内网可用性风险；按官方 spec 字段自行构造（U-1） |

## 6. 与 ADR 的关系

- ADR-0003（零外部依赖）：新模块均标准库实现，无 Jinja2/MCP SDK 运行时导入。
- ADR-0004（PyRIT 对象图基准）：仅声明式记录，不导入框架。
- ADR-0006（三层隔离）：本阶段在 worktree `D:/_attack-mcp-tool_wt` + `feat/attack-mcp-tool` 落地。
- B9 框架选型：组合取自矩阵 §②，PyRIT 仅 HTTPTarget 补位。

## 7. 门禁记录（阶段 6 / G0）

| 编号 | 检查项 | 依据 | 实测结果 | 判定 |
|---|---|---|---|---|
| B2 | 术语一致 | `check_glossary` | PASS（57 废弃术语） | 符合 |
| B7 | 无旧版对象图 | 本文件 §4 | `HTTPTarget`/`SubStringScorer`，无 `orchestrator` | 符合 |
| B8 | 可追溯 | §1–§6 | 每模块含职责/接口/错误；§5 五方案各有否决理由 | 符合 |
| 验收① | seam 数与阶段2一致 | §1/§3.2 | 1 个新缝（UI/资源交互），沿用三缝 | 符合 |
| 验收② | 接口含职责/输入/输出/错误 | §2 表 + §3 | 5 模块全覆盖 | 符合 |
| 验收③ | 依赖单向 | §2 图 | 新模块仅依赖 model.py，无环 | 符合 |
| 验收④ | 替身可替换外部依赖 | §3.2 | 4 缝各有替身并映射 AC | 符合 |

**结论：PASS**。不符合项 0。seam 从 3 → 4（新增 1 个），已记录理由并与阶段 2 用户核对结论一致。
