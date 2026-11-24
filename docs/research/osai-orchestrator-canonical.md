# osai-orchestrator 一手源核实记录

> **性质**：阶段 1 `research` 产物。每条结论附源码路径锚点，版本明确。
> **核验日期**：2026-11-24（GMT+8）。
> **范围**：PentAGI 迁移清单 A/B 类判据的一手源定位与既有实现核对。

## 1. 已核实（源码锚点）

| 判据 | 一手源 | 事实 |
|---|---|---|
| 执行监控阈值 | `backend/pkg/config/config.go:311-313` | 同工具 5 次 / 总 10 次；默认关闭 |
| 工具硬上限 | `backend/pkg/config/config.go:316-317` | 通用 100 / 受限 20 |
| 反思三振 | `backend/pkg/providers/performer.go:162-189` | 连续 3 次无工具调用触发 |
| 规划清单 | `templates/prompts/question_task_planner.tmpl` | 3–7 步 checklist |
| 人在环控制 | `backend/pkg/tools/flow_manager.go:43,534,613,686,829` | 状态/停止/提交/改步/等待 |
| 匿名化占位符 | `templates/prompts/pentester.tmpl:56-66` | IP/域名/凭据/令牌/端口占位 |
| 双通道语言 | `templates/prompts/pentester.tmpl:15-45` | 交互日志本地语言、技术通道英文 |
| 类型化工具 | `backend/pkg/tools/registry.go:11,56-130` | 7 类工具类型映射 |
| 确定性错误不重试 | `backend/pkg/providers/retry.go:20-93` | 确定性错误绕过重试 |
| 栅栏终止 | `backend/pkg/tools/registry.go:12-13` | `done` / `ask` 终止工具 |
| 本体分类 | `templates/prompts/pentester.tmpl:76-110` | 固定节点标签与边类型 |

## 2. 既有实现核对（不重写）

| 能力 | 本仓库锚点 | 判定 |
|---|---|---|
| 11 阶段 G0 | `docs/operations/skill-mainline-workflow.md` §3 | 已落地 |
| to-spec 两遍 | 同上 §3.2 / §3.3 | 已落地 |
| 三/五件套 | `tools/collect_evidence.py:40-42` | 已落地 |
| 五段式报告 | `skills/report-exam/SKILL.md:95` | 已落地 |
| PyRIT 内核 | `tools/attack_ai_agent/paths.py:102` | 已落地 |
| 令牌预算 | `scripts/check_token_budget.py` | 已落地 |
| 三层隔离 | `docs/governance/adr/0006-three-layer-isolation.md` | 已落地 |
| flag 双通道 | `skills/report-exam/SKILL.md:106-108` | 已落地 |

## 3. 已排除

- C-01～C-08：新语言栈（Go）、图数据库、可观测栈、容器守护进程、多 provider、前端、镜像选择、BAS 剧本（上游未实现）。
- 任何连接真实目标 `http://192.168.40.189` 或读取真实凭据的实现。

## 4. 待核实

- 无。19 项能力域均可由上述一手源与纯 Python 逻辑实现，无需 PyRIT 运行时。
