# recon-ai 闭环工作流设计记录

> 阶段 6 交付物 · 输入：issue #259 v2 · 事实依据 `docs/research/recon-ai-closed-loop-research.md`
> 结论先行：在既有 `cli → runner → {probes, evidence, inventory, policy, shot} → {transport, fingerprint, model}` 上新增两个单向 seam（S4 发现、S5 自校验），不改变既有 7 步判据语义。

## 1. 模块职责与公开接口

| 模块 | 单一职责 | 公开接口（新增/变更） |
|---|---|---|
| `discovery`（新） | 被动识别应用族并生成端点计划 | `discover(target, transport, timeout) -> DiscoveryPlan`；`apply(spec, plan) -> Tuple[RequestSpec, ...]` |
| `probes` | 7 步声明式探测与判据 | `Judgement` 增加 `basis: list[str]`、`tried: list[dict]`（默认空，向后兼容） |
| `verifier`（新） | 运行产物自校验 C1–C9 | `verify_run(run_dir) -> VerificationResult`；`render_gate_table(result) -> str` |
| `evidence` | 证据落盘（委托共享收集器） | `emit()` 增加 UTF-8 双保险与错误摘要；新增 `sha256(path)` |
| `runner` | 编排：发现 → 执行 → 证据 → 清单 → 自校验 → 报告 | `run_recon()` 增加 `run_id`/`run_dir`；`RunReport` 增加 `verification`、`run`、`gaps` |
| `inventory` | 资产清单组装 | `build()` 仅 PRESENT 入表；`undetermined`/`gaps` 独立记录；空表允许但须有缺口记录 |
| 报告渲染（runner 内） | 全量验证报告 | `_render_report()` 五节 + 门禁表；结论由 `VerificationResult` 派生 |
| `cli` | 入口与退出码 | 新增 `verify --run <dir> [--json]`；`run` 退出码由 verification 决定 |

## 2. 依赖方向（无环）

```
cli ──> runner ──> {discovery, probes, verifier, evidence, inventory, policy, shot}
                         │            │           │
                         └──> fingerprint, model <┘
verifier 仅依赖 model（纯文件读取），不依赖 runner/probes/discovery。
discovery 仅依赖 probes.RequestSpec 与 transport 响应结构，不依赖 runner。
```

## 3. 数据流与运行目录

```text
<out>/runs/<run_id>/
  recon-01.md … recon-07.md      # 证据片段（共享收集器格式）
  shots/recon-0x-*.png           # 访问证明
  MANIFEST.jsonl                 # 本轮证据清单（每步 1 条）
  run.json                       # 运行元数据（run_id/target/profile/窗口/steps/失败/告警）
  verification.json              # C1–C9 检查结果与 verdict
<out>/ai-assets.md|json          # 最新清单（PRESENT-only）
<out>/verification-report.md     # 最新全量报告
```

- `run_id = <YYYYmmddTHHMMSS>-<host-slug>`；生产路径按轮隔离，旧轮片段不可能混入。
- 注入 `writer`（测试）时以 `writer.out_dir` 作为运行目录，保持既有测试语义。

## 4. S4 发现设计

1. 入口探测：GET 目标根（或给定路径），解析同源链接与脚本；候选基路径 = 根 + 最多 3 个应用型链接。
2. 族识别（只读）：
   - Streamlit：`{base}/_stcore/health` 200 文本 + `host-config` 可选 + 入口含 `Streamlit`/静态 index；版本从 bundle `version:\`x.y.z\``。
   - Gradio：`{base}/config` JSON 含 `version`/`dependencies`。
   - Ollama：`/api/tags` JSON 含 `models`。
   - OpenAI 兼容：`/v1/models` JSON。
   - OpenAPI：`/openapi.json` JSON 含 `openapi`/`paths`。
3. 端点计划 = **固定模板（保持原顺序） + 族附加请求（去重追加）**；保证既有 `results[0]`/`results[1]` 索引不变。
4. 每个失败请求进入 `tried`（method/url/status/error），供判据与缺口台账引用。
5. 发现异常不阻断：记录 warning，回退固定模板。

## 5. S5 自校验设计（C1–C9 布尔）

`verify_run(run_dir)` 纯文件读取，不联网：

- C1：`run.json.steps` 覆盖 7 步且每步有终态原因；时间盒/失败隔离须有 reason。
- C2：每步片段存在、非空、mtime ∈ [started, finished+60s]、路径在 run_dir 内。
- C3：片段含「确切命令/关键输出/截图/分析注记」小节。
- C4：截图 provided（截图文件存在）或 pending（片段含「待补录」且含钩子命令）；missing 失败。
- C5：MANIFEST 每步恰 1 条且 target 一致。
- C6：每类 judgement 有 basis；UNDETERMINED 的 tried 非空。
- C7：资产清单契约通过且仅 PRESENT。
- C8：报告含五节标题与门禁表。
- C9：verdict = 全部通过；报告结论与退出码只消费 verdict。

## 6. 错误处理

- 证据写入失败（退出码非 0/超时/编码异常）：记 `quality_failures`，C4/C9 失败 → BLOCKED。
- 子进程编码：环境注入 `PYTHONUTF8=1`/`PYTHONIOENCODING=utf-8`；父进程 `errors="replace"`；共享收集器 stdin 显式 UTF-8。
- 无头浏览器缺失：C4 接受 pending + 钩子，报告显式标注，不伪造。

## 7. 被否决方案

1. **扩展 `collect_evidence.py` 增加 run_id 字段**：影响全部 P0 共享契约，风险大于收益；改用 run 目录隔离 + run.json。
2. **重写 STEP_SPECS 为多候选**：会改变既有结果索引与判据语义，回归面大；改用「固定模板 + 族附加」。
3. **强制实网端口扫描补覆盖**：违背 passive 默认与 OPSEC；覆盖以「已试端点 + 依据」表达，不强判存在。

## 门禁记录（阶段 6 · G0）

| 基线 | 判定 | 证据（命令 + 摘要） |
|---|---|---|
| B1 | 符合 | 模块职责单一、接口明确；`python scripts/validate_skill.py` 后续复跑 |
| B2 | 符合 | 新术语（应用族/基路径/缺口台账/运行标识/自校验/覆盖矩阵）阶段 7 入 GLOSSARY |
| B7 | 符合 | 设计无 PyRIT 对象；`grep -rn "pyrit\\." tools/recon_ai` 无命中 |
| B8 | 符合 | 设计映射 issue #259 v2 AC-01..24、S4/S5 seam 与用户 2026-11-16 批准记录 |
| 验收① | 符合 | seam 数量 2（S4/S5），位置与 v2 §4 一致 |
| 验收② | 符合 | 每个公开接口含职责/输入/输出/错误行为（§1/§4/§5/§6） |
| 验收③ | 符合 | 依赖方向单向（§2） |
| 验收④ | 符合 | 传输/截图/证据/发现均可注入替身 |
| 验收⑤ | 符合 | 与 ADR 无冲突；ADR-0006 隔离与 ADR-0005 预算已对齐 |

**结论：PASS**（不符合项 0）。复验：`python scripts/check_glossary.py`（阶段 7）。
