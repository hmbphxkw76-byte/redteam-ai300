# 共享工具契约清单：tools/collect_evidence.py

> **contract_version**: v5
> **性质**：单一事实源（`AGENTS.md` C1）。消费者与报告器只引本文件 `路径#锚点`，不转抄契约正文。
> **维护规则**：每次改动 `tools/collect_evidence.py` 语义，必须同步本清单元素并递增 `contract_version`，并在 CHANGELOG 追加一条「commit + PR + before→after + 兼容性判定」。

## 1. CLI 标志（接口面）

| 标志 | 语义 | 版本 |
|---|---|---|
| `--step` | 步骤标识 `step_id`（必需） | v1 |
| `--cmd` | 确切命令（必需，可 copy/paste） | v1 |
| `--out` | 输出 markdown 路径；`-` = stdout（必需） | v1 |
| `--output` / `--stdout` | 命令输出（内联文本） | v1 |
| `--output-file` | 命令输出文件；`-` = stdin | v1 |
| `--screenshot` | 截图本地路径 | v1 |
| `--shot-cmd` | 截图捕获钩子命令（仅记录不执行；**不满足截图必需件**） | v1 |
| `--shot-kind` | 截图类型：`url` / `transcript` | v2 |
| `--script` / `--script-src` / `--script-note` | 脚本/PoC 副本 / 来源 / 修改说明 | v1 |
| `--note` | 分析注记 | v1 |
| `--ai-log` / `--ai-log-file` | AI 交互日志（内联 / 文件） | v1 |
| `--flag` | flag 单值（兼容：面板=截图） | v1 |
| `--flag-panel` / `--flag-shot` | flag 双通道 | v1 |
| `--target` | 目标标识 | v1 |
| `--profile` | 执行分级 | v1 |
| `--manifest` | 证据清单 JSONL（追加一行） | v2 |
| `--retention` | 留存入径 | v2 |
| `--append` | 追加模式 | v1 |
| `--strict` | 三件套不全或 flag 不一致时退出码 1 | v1 |
| `--exam` | 考试模式：截图必需件须为真实 PNG(IEND)/JPEG(EOI) 文件；`--shot-cmd` 只记待补录，不计入完整 | v5 |
| `--scored-target` | 计分目标模式：`flag_status != 一致` 时 `complete=false`；`--flag` 单值仍视为一致 | v5 |
| `--glossary` | GLOSSARY.md 路径 | v1 |

**运行期注入（单源声明）**：`--output` / `--output-file` 是「关键输出」必需件的唯一注入通道。各 skill 的证据命令模板为骨架（含占位符），运行期**必须**以实测输出注入 `--output-file <文件>`（或 `--output <文本>`）；缺失时 `--strict` 必退出 1（§5）。各 skill 按路径引用本声明，不另立平行说明（C1）。

## 2. build_fragment 参数与 report 键

`build_fragment(step_id, command, output, screenshot, shot_cmd, ai_log, flag, flag_panel, flag_shot, target, title, timestamp, out_path, avoid_terms, script, script_src, script_note, profile, shot_kind, note, exam=False, scored_target=False)`

report 键（消费者 / 报告器依赖，字段名与语义即契约）：

- `complete`（bool）：三件套是否齐全；v5 起在 `--exam` 下要求真实截图文件、在 `--scored-target` 下要求 flag 双通道一致（默认语义不变）
- `missing`（list[str]）：缺失的必需件名；v5 考试模式使用标签「截图（真实文件）」，计分目标模式追加「flag 双通道（面板+截图）」
- `required_status`（dict）：`{"确切命令": bool, "关键输出": bool, "截图": bool}`
- `optional_status`（dict）：`{"AI 交互日志": bool, "flag 双通道": bool}`
- `shot_status`（str）：`已提供` / `待补录` / `缺失`（v3 引入）
- `flag_status`（str）：`一致` / `不一致` / `未提供`
- `avoid_terms`（list[str]）
- `shot_missing`（bool）：声明了截图路径但文件不存在
- `script`（bool）：是否登记脚本
- `hashes`（dict）：`{"output", "screenshot", "script"}` 三个 sha256

## 3. build_manifest_record 字段

`step_id, command, sha256, timestamp, profile, retention, target, screenshot, screenshot_sha256, shot_kind, shot_status, script, script_sha256, pieces{确切命令, 关键输出, 截图, AI 交互日志, flag 双通道, 脚本/PoC}, flag_dual, complete`

`shot_status`（v3 引入，取值同 §2）：manifest 行与片段 report 同源落盘。

v4 追加变更登记字段（均默认空串，向后兼容）：`change_kind`（变更类型，如 `module-hijack` / `disable-defender`）、`change_target`（被改系统/文件）、`change_ts`（变更时间）、`cleanup_state`（取值域 `pending` / `done` / `n/a`；登记变更未声明清理时诚实记 `pending`）、`cleanup_owner`（清理责任人）。

传值方式：复用既有 `--note` 标志。当 `--note` 为 JSON 对象且含 `change_kind` 时按 `parse_change_note(note)` 解析为上述字段；否则保持为普通分析注记（既有语义不变，不新增 CLI 标志）。这是跨技能 RoE 变更登记/清理的唯一字段来源（Ch11 L48/L820/L914/L1213）；各攻击技能按路径引用本节，不另立平行清单（C1）。`--strict` 对 `cleanup_state=pending` 不阻断（诚实标注）。

## 4. 片段节标题（tools.report_exam.index.parse_fragment 下游契约）

- `### 步骤 <step_id>：<title>`
- `#### 确切命令`（bash fenced 块）
- `#### 关键输出`（text fenced 块）
- `#### 截图（访问证明）`（`![<step_id> 截图](<path>)` 图片引用）
- `#### 分析注记（可选）`
- `#### 脚本 / PoC（来源与修改说明）`
- `#### AI 交互日志`
- `#### flag 取证（双通道一致）`（fenced 原值块 + 双通道明细表）
- `#### 证据校验（五件套 / 三件套）`（表列 `| 截图 | 是 | … |`）

## 5. 退出码语义

- `0`：成功
- `1`：错误（缺必需输入 / 严格三件套不全 / 严格 flag 不一致 / 写入失败）
- `2`：用法错误

## CHANGELOG

- `v5`（2026-11-25）commit:待合入后回填 PR:待回填 破坏性:否（默认语义不变） 变更:新增 `--exam` / `--scored-target` 两个显式开关；`--exam` 下仅真实 PNG/JPEG 文件计入截图必需件，`--scored-target` 下双通道一致才计入完整；节标题与 manifest 字段不变。before→after:钩子-only 片段仅在显式考试模式判为不完整 → 演练模式仍判完整；兼容性:消费端无需改动，考试模式为 opt-in。消费者:report-exam、verify-evidence、tooling-automate。
- `v4 勘误`（2026-11-25）审查 P7 收口 破坏性:否 变更:§3 清单补记 `shot_status`（v3 已实现并落盘，契约文档漂移修复，无实现变更）；`tools/_evidence_contract.py` emit 退出码 docstring 改引本契约 §5（消除「2 用法/运行错误」矛盾口径）。before→after:§3 缺 shot_status → 与实现一致；兼容性:纯文档同步，消费者无感。

- `v4`（2026-11-22）commit:`15803c5` PR:#413 破坏性:否 变更:新增变更登记字段 `change_kind`/`change_target`/`change_ts`/`cleanup_state`/`cleanup_owner`（默认空串）；`--note` 结构化 JSON 时经 `parse_change_note` 注入；`--strict` 对 `cleanup_state=pending` 不阻断。before→after:manifest 行无 change_* 字段 → 含 5 字段（默认空）；兼容性:旧调用签名/返回键形态不变，普通 `--note` 语义不变。消费者:tooling-automate、attack-rag（upload_manifest 改指向本节）。
- `v3`（2026-11-15）commit:`e9f8bdd` PR:#250 破坏性:是 变更:`shot_status` 三态字段新增（`已提供`/`待补录`/`缺失`）；`--shot-cmd` 单独存在时「截图」由「已提供」改为「待补录（钩子命令已记录）」，`complete` 语义不变。
- `v2`（历史）变更:引入 `--shot-kind`、`--manifest`、`build_manifest_record` 与证据清单 JSONL。
- `v1`（历史）变更:初始契约。
