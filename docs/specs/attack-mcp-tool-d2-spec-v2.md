# 规格 v2（工程定稿）：MCP server 生命周期与端口独占

- 对应 v1：GitHub issue #464（行为规格），本文为其工程定稿，版本递增、内容不同
- 归档路径：`docs/specs/attack-mcp-tool-d2-spec-v2.md`（v1 为 `-spec-v1.md`）
- 阶段：主线阶段 3 `to-spec` ②

## 0. v1 → v2 差异清单

| # | v1 表述 | v2 收敛 | 理由 |
|---|---|---|---|
| 1 | US-1「不产生第二个监听」 | AC-01 量化为「端口不变 + 监听线程对象同一 + 可连接」 | 可判定化 |
| 2 | US-2「能查询是否在监听」 | AC-02 定义三态序列（未启动/已启动/已停止） | 消除时点歧义 |
| 3 | US-4「不关闭不是自己的」 | AC-04 改为「运行后该实例仍可服务且端口未释放」 | 用外部行为判定，免断言内部标志 |
| 4 | US-8「有限退避窗口」 | AC-05 定阈值为 2 s 内成功、成功率 100% | 阈值来自 spike（1 ms）留 3 个数量级余量 |
| 5 | US-10「可捕获错误」 | AC-03 只断言 `OSError`，不绑定 `errno` | Linux 侧错误码待 CI（U-1） |
| 6 | 未涉及公开 API | 新增 AC-12「既有断言不得因实现改动而放宽」 | 防止以改测试换取绿灯 |

## 1. 布尔验收条件

| ID | 验收条件（全部为可判定布尔式） | 判定方式 |
|---|---|---|
| AC-01 | 对已监听实例再次调用启动后：端口号不变、`is_running` 为真、监听线程对象与首次相同、可成功建立 HTTP 连接 | T1 |
| AC-02 | 未启动 → `is_running` 假；启动后真；关闭后假 | T1 |
| AC-03 | 端口已被本进程占用时，同端口另起实例的启动调用抛 `OSError`；且首个实例仍可服务 | T2 |
| AC-04 | 注入已监听实例运行完整步骤后：该实例 `is_running` 仍为真、端口仍可连接（编排层未关闭它） | T3 |
| AC-05 | 注入未启动实例运行结束后：`is_running` 为假；2 s 内可重新绑定同一端口（重试间隔 50 ms） | T4 |
| AC-06 | 未注入 server 时：编排层自建并关闭，运行结束后 2 s 内端口可重绑 | T4 |
| AC-07 | 构造端口冲突时执行 mcp-02：等级为「已跳过」，且理由文本含「端口」 | T5 |
| AC-08 | 连续两次关闭、以及未启动直接关闭，均不抛异常 | T1 |
| AC-09 | `python -m unittest discover -s tests -t . -q` 退出码 0，失败 0 | 命令 |
| AC-10 | `python scripts/measure_coverage.py --target attack-mcp-tool --min 90` 退出码 0 | 命令 |
| AC-11 | `check_tools_compile.py`、`check_glossary.py`、`check_token_budget.py --check`、`markdownlint-cli2` 均 PASS | 命令 |
| AC-12 | 既有测试的断言未被放宽：diff 中不得出现删除既有 `assert*` 行的改动（新增除外） | `git diff` 人工判据 |

## 2. 测试决策

- **只测外部行为**：端口号、`is_running`、能否连接、异常类型、证据等级；不断言 `_thread` 之外的私有字段（AC-01 的线程同一性以对象身份断言，属可观测的生命周期事实）。
- **参考测试**：`tests/attack_mcp_tool/test_attack_mcp_tool_poison.py`（真实 server 端点）、`test_attack_mcp_tool_runner.py::RunnerBranchTests`（注入与降级）、`tests/attack_mcp_tool/test_attack_mcp_tool_units.py`（替身用法）。
- **T 用例与 AC 映射**：T1→AC-01/02/08；T2→AC-03；T3→AC-04；T4→AC-05/06；T5→AC-07；T6→U-2；T7→AC-09/10/11。
- **平台**：T2/T6 在 Windows 断言 `OSError`；CI（ubuntu / Python 3.11）自然验证 U-1，不写死 `errno`。
- **不做**：不引入睡眠式等待（除 AC-05 的显式重试循环）、不使用固定端口、不 mock socket。

## 3. 门禁映射

| 门禁 | 覆盖的 AC | 命令 |
|---|---|---|
| CI S1（编译 + 静态） | AC-11 | `check_tools_compile.py`、`check_glossary.py`、`markdownlint-cli2` |
| CI S2（测试 + 覆盖率） | AC-09、AC-10 | `unittest discover`、`measure_coverage --min 90` |
| 本地 C4 预算 | AC-11 | `check_token_budget.py --check` |
| 证据契约 | 不适用（本变更不产证据片段） | — |

## 4. 核实闸

| 闸 | 触发条件 | 处置 |
|---|---|---|
| G-U1（Linux 语义） | CI 上 T2 未抛 `OSError` | 判 `BLOCKED`，回阶段 8 调整 C 的平台分支，重跑阶段 9 |
| G-U2（重绑窗口） | T6 在 2 s 内重绑失败率 > 0 | 记录实测值并放宽 AC-05 阈值（须同步改 v2 并留痕），不得回退独占配置 |

## 5. 风险与回滚

| 风险 | 影响 | 回滚 |
|---|---|---|
| 独占地址在 CI 上导致既有 server 用例失败 | 阶段 9 红 | 单独回退 C 提交，保留 A/B |
| 所有权变更影响未识别的调用方 | 阶段 10 审查项 | 回退 B 提交 |
| `is_running` 引入对线程对象的依赖 | 低（只读判定） | 退化为 `_server is not None` |

## 6. 对象图与 seam

- seam 数量：3（既有），新增 0。
- 生命周期对象：`PoisonedMcpServer`（持有 `_server` / `_thread` / 平台绑定策略）。
- 编排对象：`_Session`（持有 `started_server` 与 `_owns_server`）。
- 注入点：`Runtime.client` / `Runtime.writer` / `Runtime.capture` 不变。
