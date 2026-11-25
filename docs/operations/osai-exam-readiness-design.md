# OSAI 考试就绪优化：工单 / 分类 / 设计 / 术语（阶段 4–7）

> 主线阶段 4 `to-tickets`、5 `triage`、6 `codebase-design`、7 `domain-modeling` 合并留痕于一份文档；
> 各阶段门禁独立记录于 `docs/operations/osai-exam-readiness-gates.md`。

## 1. 阶段 4 — 工单拆解

父工单 #446（规格 v1 正文 + v2 评论），子工单：

| 子工单 | 切片 | 覆盖 AC | 阻塞边 |
|---|---|---|---|
| #447 | 证据判定（考试模式） | AC-01..05 | 无 |
| #448 | 目标映射与只读证据管线 | AC-06/07 | #447 |
| #449 | 阶段状态机与报告提交预检 | AC-08..10 | #448 |
| #450 | 治理校验与孤儿项收口 | AC-11/12 | 无 |

依赖图：`#447 → #448 → #449`；`#450` 独立。无环。每张工单可单独验收，验收命令见 v2 §1。

## 2. 阶段 5 — 分类定级

四张子工单均标 `ready-for-agent`，无 `ready-for-human`（本轮不接触真实考试凭据与门户）。brief 摘要：

- **#447 brief**：仅改证据 CLI 与单测；约束：节标题不可变、演练语义不变；验收：AC-01..05。
- **#448 brief**：新增映射表与只读校验；约束：不写证据、不填 flag；验收：AC-06/07。
- **#449 brief**：新增状态机与提交预检；约束：不执行攻击、不联网；验收：AC-08..10。
- **#450 brief**：新增独立校验脚本与状态标注；约束：不改共享长行；验收：AC-11/12。

## 3. 阶段 6 — 模块与接口设计

### 3.1 seam 与依赖方向

沿用两个既有 seam，不新增外部 seam：

1. `collect_evidence.py` CLI：唯一证据产物入口。新增两个布尔标志：`--exam`（截图必须为真实图片文件）、`--scored-target`（计分目标必须双通道）。默认均关闭，保持 v3/v4 行为。
2. `tools/osai_orchestrator/handoff.py` 的 H1–H6：唯一交接判据来源。新增状态机只消费其返回值，不复制判据。

依赖方向单向：`target-map(md) → evidence-pipeline → report-preflight → submission-check`；`state-machine → handoff`。无反向依赖。

### 3.2 公开接口

| 模块 | 公开入口 | 输入 | 输出 | 错误行为 |
|---|---|---|---|---|
| 证据 CLI | `main(argv)` | 既有参数 + `--exam` / `--scored-target` | markdown 片段、manifest 行 | 严格模式退出 1；错误走 stderr |
| 目标映射 | `docs/operations/osai-target-map.md` | 人工在考试窗口填写 | 8 行目标记录 | 缺列/缺行由管线报 BLOCKED |
| 证据管线 | `check_targets(target_map, fragments_dir, root)` | 路径三元组 | `(ready: bool, gaps: list[str])` | 只读，不修改任何文件 |
| 阶段状态机 | `ExamPipeline(stage).advance(results)` / `run_with_handoffs(...)` | 阶段号 + H1–H6 `GateResult` | 新阶段号或停留 | 失败停留并返回 False |
| 报告预检 | `scan_report_placeholders(path)` | 报告文本路径 | `[(line, token)]` | 文件不存在返回空并报错 |
| 提交校验 | `check_submission(pdf, archive, expected_md5)` | 三条路径/值 | 判定字典 | 任一官方规则不满足即 False |

### 3.3 权衡与被否决方案

- 否决「直接把 `complete` 默认改为严格」：会令 17 技能既有演练片段与测试同时变红，破坏兼容；改为显式考试模式。
- 否决「新增第四种截图状态」：契约 v3 的三态已下沉到 manifest 与报告器，新增状态会扩散到所有消费者。
- 否决「让编排器直接执行攻击」：考试环境不可在本仓库代跑，且会引入外部依赖与安全边界问题；状态机只编排与判定。

## 4. 阶段 7 — 术语建模

本轮引入的实现标识符均可由既有术语表达（证据片段、目标、阶段、门禁、提交件），不新增 `GLOSSARY.md` 条目。禁用同义词沿用既有基准；`check_glossary.py` 全量通过作为本阶段门禁。

## 5. 阶段 4–7 门禁摘要

| 阶段 | B 判定 | 结论 |
|---|---|---|
| 4 | B2/B8 符合：覆盖矩阵无空格、依赖无环 | PASS |
| 5 | B8 符合：4/4 恰一标签且 brief 完整 | PASS |
| 6 | B2/B7/B8 符合：无旧版 PyRIT 对象，seam 未增加 | PASS |
| 7 | B1/B2/B8 符合：新增术语 0，`check_glossary` 通过 | PASS |
