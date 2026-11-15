# attack-multi-agent 主线闭环实测验证报告

- **日期**：2026-11-15
- **目标**：`http://192.168.40.183:9000`（DVAA，OpenA2A「故意可攻破 AI Agent」靶场）、`http://192.168.40.189/explore`（AIVP）
- **验证对象**：`/主线 attack-multi-agent` 全流程闭环——攻击执行 → 证据收集 → 报告撰写 → 字段衔接 → 状态追溯

## 一、结论先行

**闭环成立**：攻击执行、证据收集、报告撰写三节点数据传递无断点，`step_id / command / target / evidence_path / flag` 跨节点一致、可追溯。但在**非 A2A 总线形态**的目标上暴露出 **3 处定级/证据正确性缺陷**（F1–F3），其中 F3 导致严格门「三件套齐全」虚报。详见第四节。

## 二、目标侦察（执行前置）

| 目标 | 形态 | 判定 |
|---|---|---|
| `192.168.40.183:9000` | DVAA：21 个 Agent（各端口 7001/7002/…），OpenAI 兼容 `/v1/chat/completions` + MCP `/mcp/tools|execute`；含 A2A 场景（`a2a-identity-replay`/`agent-impersonation-a2a`/`a2a-trust-chain-poisoning` 等 40+） | **HTTP/API 型多智能体**，非 Kafka/Redis 总线 |
| `192.168.40.189/explore` | AIVP（55 lab / 4 phase） | 演练场（未深入） |

关键事实：DVAA 的 A2A 面是「每 Agent 独立端口 + chat/MCP」，与 `attack-multi-agent` 的 `a2a.py` 抽象契约（`/topics`、`/publish`、`/set`、`/context`、`/task`、`/trace` 总线形态）**不匹配**。因此实测主路径产生的是「诚实降级」而非「完全生效」——这本身是闭环应验证的异常分支。

## 三、闭环实测结果

### 3.1 攻击执行（8 步，真实 HTTP）

```
a2a-01 发现拓扑        完全生效  ← 误判（F1）
a2a-02 消息操纵        未生效    （404，正确）
a2a-03 智能体冒充      未生效    （404，正确）
a2a-04 共享记忆投毒    部分生效  ← 误判（F2）
a2a-05 上下文投毒      未生效    （404，正确）
a2a-06 工作流破坏      未生效    （404，正确）
a2a-07 下游取证        未生效    （404，正确）
a2a-08 flag 取证       已跳过    （无实测 flag，正确）
```

### 3.2 证据收集

- `evidence/attack-multi-agent/`：8 个片段（`a2a-01.md`…`a2a-08.md`）+ `manifest.jsonl`（8 条）。
- 每条 manifest 含 `step_id/command/sha256/timestamp/retention/target/screenshot/pieces/flag_dual/complete`，可追溯。

### 3.3 报告撰写

- `report_exam.index.parse_fragment` 对 8/8 片段解析成功，产出 `Fragment`（字段 `step_id/target/title/command/output/screenshot/ai_log/flag/raw/source_path/host`）。
- flag 双通道实测（注入 `AIVEC-TEST-1234`）：`fragment.flag == AIVEC-TEST-1234`，`manifest.flag_dual == "一致"`，fenced 原值块与双通道表均落盘。

### 3.4 字段衔接一致性矩阵

| 校验项 | 结果 |
|---|---|
| `step_id` 三方一致（verdict ↔ manifest ↔ fragment） | ✅ 8/8 |
| `command` 一致（manifest == verdict.command） | ✅ 8/8 |
| `target` 一致 | ✅ 8/8 |
| `evidence_path == manifest.retention`（真实运行） | ✅ 8/8 |
| `flag` 双通道 round-trip | ✅（注入时） |
| `screenshot` 字段一致（manifest `screenshot=""` ↔ 实际无 .png） | ✅ 值一致，但 `complete/截图` 语义错误（F3） |

## 四、发现（F1–F3）与建议修复

### F1：a2a-01 拓扑解析假阳性 → 误判「完全生效」
- **现象**：目标返回 SPA HTML，`parse_topology` 的正则 `(?:agent|智能体|节点)\s*[:：]?\s*([A-Za-z0-9_\-]{2,})` 命中标题文案 "The AI **agent you**'re supposed to break"，把 `you` 当 agent，`agent_count=1` → 完全生效。
- **根因**：对非结构化 HTML 做启发式正则，未按 `Content-Type`/JSON 结构门控。
- **建议**：`parse_topology` 仅在响应为 JSON 且含 `agent`/`id`/`name` 等结构化键时解析；否则 `agent_count=0` → 已跳过。

### F2：a2a-04 前后对照判据假阳性 → 误判「部分生效」
- **现象**：`/set` 返回 404（写入未受理，`deterministic=False`），但 `before_after_diff(before=SPA HTML, after=payload JSON)` 恒为 True → `judge=True` → 部分生效。
- **根因**：`before_after_diff` 未要求「写入确实被接受」就判定差异成立。
- **建议**：`judge` 必须以 `deterministic`（写入被受理）为前提；`deterministic=False` 时不得进入前后对照判据。

### F3：严格门「截图」件被钩子命令满足 → 三件套虚报（最高优先级）
- **现象**：`manifest` 中 `screenshot=""`、`screenshot_sha256=""`、`shot_kind=""`，但 `pieces["截图"]=true`、`complete=true`，片段尾部「三件套齐全：是」。
- **根因**：`collect_evidence.py` 第 168 行 `has_shot = bool(screenshot) or bool(shot_cmd)`；runner 每步恒传 `shot_cmd`，故「截图」恒判已提供，严格门失效。与 SKILL.md 质量门「截图缺失即未过门禁」矛盾。
- **触发条件（环境异常）**：本沙箱 Windows 下 Edge 无头截图静默失败（`--headless=new/old`、`--user-data-dir`、`file://` 均 rc=0 但不落盘），截图实际为空。
- **建议**：`has_shot = bool(screenshot)`；`shot_cmd` 单独标「待补录」状态（不满足必需件）。**涉及共享工具 `collect_evidence.py`，须跨技能回归**（recon-ai/decoy-detect/loot-manage 均依赖）。

## 五、闭环成功判定标准（明确）

1. **执行无崩溃**：8 步均产出 `Observation`（含命令 + 原始响应或诚实错误）。
2. **证据完整且可追溯**：8 片段 + manifest 8 条；`manifest.retention == fragment 路径 == verdict.evidence_path`；每条含 `sha256`。
3. **报告可无损消费**：`parse_fragment` 100% 成功，`step_id/command/flag` 可回读。
4. **定级诚实**：无真实受理/改写证据时不得判「完全/部分生效」（F1/F2 修复后满足）。
5. **三件套真实齐全**：命令 + 输出 + **真实截图文件**三者齐备（F3 修复后满足）。
6. **flag 双通道一致**：`fragment.flag == 面板值`，`flag_dual="一致"`；无 flag 时如实「已跳过」。

## 六、异常场景处理方式（明确）

| 场景 | 期望行为 | 现状 |
|---|---|---|
| 目标非 A2A 总线（单 agent / chat 形态） | a2a-01 判「已跳过」+ 建议改走 `attack-ai-agent` | ❌ F1 误判完全生效，需修复 |
| 写入被拒（404/护栏拦截） | `deterministic=False`，不得靠判据翻案 | ❌ F2 误判部分生效，需修复 |
| 无头浏览器不可用/截图失败 | `NullCapture` 标「待补录」，严格门**失败**或标「待补录」 | ❌ F3 虚报齐全，需修复 |
| 无实测 flag | a2a-08 判「已跳过」，不伪造 | ✅ 正确 |
| HTTP 错误/超时 | `transport` 返回 `Response.error`，定级「未生效」，不崩溃 | ✅ 正确 |
| 证据质量门失败（writer 返回非 0） | runner 抛 `RuntimeError`，证据链不静默 | ✅ 正确（单测覆盖） |

## 七、下一步建议

1. 优先修复 **F3**（共享工具，需跨技能回归 + 独立 PR）。
2. 修复 **F1/F2**（`tools/attack_multi_agent` 内，随 skill 修正 PR）。
3. DVAA 若需真正「完全生效」级演示，应在 `a2a.py` 的 `HttpClient` 缝上注入 DVAA 专用适配（OpenAI chat/MCP 形态），而非直接复用总线端点契约——这与 `scanner.py` 的 `A2ASecBenchAdapter` 同构。
