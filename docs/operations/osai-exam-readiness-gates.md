# OSAI 考试就绪优化：阶段门禁记录（G0）

> 增量留痕（C2/T2）：只列本阶段变更项、判定、复验命令、结论；B1–B9 全量定义在 `docs/operations/skill-mainline-workflow.md:47-57`。
> 规格源：issue #446（v1 正文 + v2 评论）；子工单 #447–#450。

## 阶段 1 research

| 检查 | 结果 | 命令/证据 |
|---|---|---|
| B7/B8/B9 | 符合 | `docs/research/osai-exam-readiness-canonical.md`；F-1..F-14 均有路径锚点；框架组合取自矩阵 P0→P2 |
| 结论 | PASS | 已核实 14 项、待核实 6 项、假设 5 项 |

## 阶段 2 to-spec ①

| 检查 | 结果 | 命令/证据 |
|---|---|---|
| B1/B2/B8 | 符合 | `docs/specs/osai-exam-readiness-spec-v1.md`，七节齐全，`python scripts/check_token_budget.py --artifact spec-v1 ...` PASS（4613/8000B） |
| 结论 | PASS | issue #446 正文同步（术语漂移已按 §8.3 修正并回同步） |

## 阶段 3 to-spec ②

| 检查 | 结果 | 命令/证据 |
|---|---|---|
| B1/B2/B6/B7/B8 | 符合 | `docs/specs/osai-exam-readiness-spec-v2.md`，AC-01..15 布尔化；artifact PASS（5064/10000B）；v2 作为 issue #446 评论追加 |
| 结论 | PASS | v1 未被取代，互链完整 |

## 阶段 4 to-tickets

| 检查 | 结果 | 命令/证据 |
|---|---|---|
| B2/B8 | 符合 | 父 #446 + 子 #447–#450；依赖 `#447→#448→#449`、`#450` 独立；覆盖矩阵见 design 文档 §1 |
| 结论 | PASS | 无环、无空格 |

## 阶段 5 triage

| 检查 | 结果 | 命令/证据 |
|---|---|---|
| B8 | 符合 | 4/4 子工单 `ready-for-agent`，brief 见 design 文档 §2；无人工项 |
| 结论 | PASS | — |

## 阶段 6 codebase-design

| 检查 | 结果 | 命令/证据 |
|---|---|---|
| B2/B7/B8 | 符合 | design 文档 §3：seam 沿用 2 个、依赖单向、无旧版 PyRIT 对象；签名与实现已对齐 |
| 结论 | PASS | — |

## 阶段 7 domain-modeling

| 检查 | 结果 | 命令/证据 |
|---|---|---|
| B1/B2/B8 | 符合 | 新增术语 0；`python scripts/check_glossary.py` PASS（66 个废弃术语） |
| 结论 | PASS | — |

## 阶段 8 implement-spec

| 检查 | 结果 | 命令/证据 |
|---|---|---|
| B1,B2,B3,B4,B5,B7,B8,B9 | 符合 | `python -m py_compile` 全绿；`check_token_budget --check` PASS；golden 片段解析 PASS；演练模式未变 |
| 结论 | PASS | 新增 4 模块 + 1 校验脚本；无 PyRIT 对象图变更 |

## 阶段 9 tdd

| 检查 | 结果 | 命令/证据 |
|---|---|---|
| B3/B4/B6/B8 | 符合 | `python -m unittest discover -s tests -t .`：Ran 1469 tests，OK (skipped=3)；`python scripts/measure_coverage.py --target osai-exam-readiness --min 80`：272/305 = 89.2% PASS |
| 结论 | PASS | 红阶段输出留痕见 tests 新增用例；契约漂移测试 PASS |

## 阶段 10 code-review

| 轴 | 发现数 | 最严重项 | 处置 |
|---|---:|---|---|
| Standards | 9（初检 4 硬违规） | 契约 v5 CHANGELOG 无真实 commit/PR；签名未同步；未注册覆盖率目标 | 全部修复；复检见下 |
| Spec | 10（初检 4 硬违规） | 考试模式 `shot_status` 误报复发；AC-09 缺文件名；AC-13 覆盖盲区；AC-14 缺五列表 | 全部修复；复检见下 |
| 复检 | 硬违规 0 | 契约消费者/清单门禁 PASS；`check_glossary` PASS；覆盖率 89.2% | PASS |

**§8.3 声明**：AC-11 字面「git diff 仅出现新增脚本与独立测试」与 AC-01..05 必需的既有 CLI/契约修改冲突；按 GOVERNANCE §8.3 显式声明其实际解释为「不修改 CI 并发长行」，改动限定为新增独立脚本/测试 + 必要契约同步。

结论：PASS。

## 阶段 11 pr-push-review

| 检查 | 结果 | 命令/证据 |
|---|---|---|
| B1–B9 | 待推送后回填 | 本地门禁全绿；PR 正文与推送记录在后续段落回填 |
| 结论 | 待回填 | — |
