# A2A Ch4 对齐全量主线：阶段 9 TDD 记录

> 对应父工单 #292、规格 v2 #294。本文是阶段 9 `tdd` 交付物与 G0 记录。

## 1. 红—绿—重构

| 轮次 | 动作 | 命令 | 输出摘要 |
|---|---|---|---|
| 红 | 新增 `tests/recon_ai/test_recon_ai_a2a.py`，断言 recon-05 声明 Agent Card 探针、合法 card 判 PRESENT、坏 JSON/404 不判存在 | `python -m unittest tests.recon_ai.test_recon_ai_a2a -v` | Ran 4 tests；2 FAIL：`'/.well-known/agent.json' not found`；`UNDETERMINED != PRESENT` |
| 绿 | `tools/recon_ai/probes.py` 增加 `_agent_card()` 纯函数、recon-05 追加只读 RequestSpec、judge_agent 增 card 分支 | 同上 | Ran 4 tests；OK |
| 重构 | 将 card 判定的 `context` 统一为既有 `agent_inventory` 的嵌套形态（`agent_card` + `endpoint`），保持外部行为不变 | 同上 + `python -m py_compile tools/recon_ai/probes.py` | 4 tests OK；py_compile 退出码 0 |
| 阶段10补测 | 双轴审查要求补足优先级共存用例（request_id 信号与 Card 同时存在） | 同上 | Ran 5 tests；OK；判据优先级与设计一致 |

测试只断言外部行为：请求声明与 `Judgement` 输出；不断言内部函数结构。

## 2. 覆盖矩阵

| 验收条件 | 测试 / 检查 |
|---|---|
| AC-RC-1 | `tests/recon_ai/test_recon_ai_a2a.py`：探针声明 + PRESENT + 坏 JSON/404 不判存在 + request_id 优先级（5 tests OK） |
| AC-RC-3 | `python -m unittest discover -s tests/recon_ai -t . -q` → Ran 93 tests，OK（既有 /agents、/health、request_id 判据未破坏） |
| AC-MA-2 | `python -m unittest tests.attack_multi_agent.test_attack_multi_agent_evidence_contract -q` → Ran 3 tests，OK |
| AC-ALL-3 | 全量 unittest Ran 897 tests，OK (skipped=3)；覆盖率复跑见阶段 10/11 |
| AC-ALL-2 | validate_skill / check_glossary / contract manifest+consumers / tools_compile / evidence_contract / markdownlint 全 PASS |

## 3. 阶段 9 G0（B3/B4/B6/B8）

| 项 | 结果 | 证据 |
|---|---|---|
| B3 | 符合 | py_compile 0；full unittest 897 OK；recon group 93 OK |
| B4 | 符合 | 新增 A2A 证据契约测试；attack-multi-agent 8 步契约未变 |
| B6 | 符合 | S1 静态项与 S2 测试/覆盖率全绿；`checkout_lock` 复跑 PASS（外部并发已消解） |
| B8 | 符合 | 红/绿/重构命令与输出摘要逐轮留痕 |
| 覆盖率 | 符合 | 9820/10985 = 89.4%，门槛 80% |
| 上游复核 | 符合 | `check_glossary` PASS；v1/v2 未被阶段 8/9 改写 |

**阶段 9 G0：PASS**。进入阶段 10 `code-review`。

## 4. 外部阻断记录与消解

首次 `checkout_lock.py --check` 曾检出其它 worktree 并发修改 `GLOSSARY.md`；本任务未改 GLOSSARY，按三层隔离纪律未取并集、未绕过锁。阶段 10 复跑 `python scripts/checkout_lock.py --check` → PASS（无并发修改共享文件、无契约落后基线），阻断消解。
