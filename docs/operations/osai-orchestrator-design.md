# osai-orchestrator 设计记录

> **性质**：阶段 6 `codebase-design` 产物。范围：纯增量、零外部依赖、零既有技能改动。
> **唯一 seam**：`Orchestrator` 类 + `CommandRunner` 协议；CLI 与库调用共用。

## 1. 模块与职责

| 模块 | 职责 | 依赖方向 |
|---|---|---|
| `models.py` | 值类型：Verdict/Decision/Record/GateResult/配置 | 无 |
| `supervision.py` | 执行监控、反思、上限、栅栏 | → models |
| `planning.py` | 规划、增量精化、人在环 | → models |
| `governance.py` | 摘要标记、压缩、匿名化、白名单、复核、模板、本体 | → models |
| `tooling.py` | 类型化注册、ID 归一化、错误分类、重试、受限检索 | → models |
| `runner.py` | S-1 组合入口 | → 上述全部 |
| `cli.py` | 命令行薄封装 | → runner |

依赖单向：`cli → runner → 能力域 → models`。无环。

## 2. 公开接口与错误行为

- `ExecutionMonitor.observe(tool, advancing)`：返回 `MonitorVerdict`；无效阈值在构造时拒绝。
- `Reflector.reflect(failures, has_action, near_limit)`：返回 `Decision`；不修改外部状态。
- `ToolCallBudget.check(role, used, pending)`：负数入参抛 `ValueError`；超限返回 BLOCKED 与重排建议。
- `Barrier.decide(...)`：仅四条件全满足才放行 `done`。
- `Planner.build / wrap`、`Refiner.apply`、`HumanInLoop.apply`：纯数据操作。
- `Anonymizer.anonymize`、`ContextCompactor.compact`、`IndependentReviewer.review`：纯字符串/数据。
- `TypedRegistry.check`、`CallIDNormalizer.normalize`、`ErrorClassifier.classify`、`RetryPolicy.decide`：纯规则。

## 3. 注入点

`CommandRunner` 协议由 `SubprocessRunner` 实现，测试用 `FakeRunner`。CLI 的 `main(argv, runner=None)` 可注入。

## 4. 复用与被否决方案

- 复用：`tooling-automate` 的 S-1 入口思想、`pyrit_compat` 的注册表规则思想、`collect_evidence.py` 的证据语义。
- 否决：逐一散改 16 个既有技能（破坏风险高、违反不破坏约束）；引入 Go 服务（C 类）；Graphiti/Langfuse（C 类）。

## 5. 与既有技能的关系

本模块不含攻击逻辑，不替代任何既有技能；仅提供可选增强能力，调用方按提示词分册映射使用。
