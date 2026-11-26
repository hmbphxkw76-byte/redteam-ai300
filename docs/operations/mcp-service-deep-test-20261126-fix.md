# MCP 服务深度测试修复记录（2026-11-26 晚）

- 上游报告：`docs/operations/mcp-service-deep-test-20261126.md`（缺陷编号 D-1…D-14 沿用该报告 §8）
- 修复范围：D-1（高危中断）、D-3（覆盖率不达标）、D-14（覆盖率工具口径）；关联 D-11 清单补齐
- 变更约束：未改步骤契约 `STEP_IDS`、未改证据格式、未改公共 API 签名

## 1. D-1 最小修复补丁

- **改动点**：`tools/attack_mcp_tool/runner.py::_render()`，新增「有 text 无 raw」分支，共 4 行。

```python
    if obs.text and not obs.raw:
        # 纯文本降级观测（如 jsonrpc 形态的「本步不适用」说明）没有原始响应，
        # 仍须作为「关键输出」落盘；否则证据三件套判定为空，严格门禁会中断整轮。
        parts.append(obs.text)
```

- **为何选此点**：根因在渲染层；一处改动同时修复 mcp-06 与 mcp-08 两个症状，且仅在 `raw` 为空的降级场景追加文本，既有分支的输出顺序与内容不变。
- **回归用例**：`tests/attack_mcp_tool/test_attack_mcp_tool_runner.py::JsonRpcFullEmitTests.test_jsonrpc_full_path_emits_all_eleven_steps`。修复前红灯（`RuntimeError: 证据质量门未通过：mcp-06`），修复后绿灯。
- **行为对比（真实 CLI，`--mode jsonrpc`）**：

| 场景 | 修复前 | 修复后 |
|---|---|---|
| `cli.py --mode jsonrpc`（默认 A/B/C + flag） | 退出码 1，落盘 6 份，中断于 mcp-06 | 退出码 0，落盘 8 份 |
| `cli.py` 加 `--path A..F` 全路径 | 不可用（同上中断） | 退出码 0，落盘 11 份 |
| 单步 `--step mcp-08` | 退出码 1 | 退出码 0 |

## 2. D-3 补测与 D-14 口径修复

- **口径修复（D-14）**：`scripts/measure_coverage.py` 增加 `threading.settrace(tracer)` 并在 `finally` 撤销；否则线程化 handler 恒判未覆盖，`poison.py` 被低估约 27 个百分点。
- **清单补齐（D-11 关联）**：`scripts/tools_manifest.json` 的 `coverage_targets.attack-mcp-tool.tests` 补入 `test_attack_mcp_tool_ch7_gap`，使 Ch7 用例计入该目标。
- **新增用例 19 条**：

| 文件 | 覆盖点 |
|---|---|
| `test_attack_mcp_tool_poison.py::ServerHandlerEdgeTests` | 404 详情、根路径与尾部斜杠、畸形 JSON（-32700）、未知 method（-32601）、未知工具（-32602）、`stop()` 幂等与未启动调用、shadow schema 名集/字段漂移、反序差分 `removed` |
| `test_attack_mcp_tool_runner.py::RunnerBranchTests` | 默认 capture 构造、`_curl` GET 形态、`paths` 覆盖参数、`prompt_for` 注入、单步异常收敛（不记「已跳过」）、证据门失败上抛、jsonrpc `tools/list` 错误降级、本地端口不可用降级、按目标工具面解析 admin 角色 |
| `test_attack_mcp_tool_runner.py::JsonRpcFullEmitTests` | D-1 回归：全路径 11 份片段、每份含非空「关键输出」、mcp-06/08 记已跳过 |
| `test_attack_mcp_tool_flag.py` | 目标存在 flag 文件时切换官方双通道（含候选文件探测的不可达 `continue` 分支） |

## 3. 覆盖率修复前后

| 模块 | 修复前 | 补测后 |
|---|---|---|
| `poison.py` | 68.6% | **99.4%** |
| `runner.py` | 74.5% | **98.0%** |
| `mcp.py` | 91.3% | 92.7% |
| `grade.py` | 78.9% | 97.0% |
| `shot.py` | 81.5% | 83.7% |
| 总计（阈值 90%） | 81.1%（退出码 1） | **94.4%，1608/1703（退出码 0）** |

剩余洼地：`cli.py` 82.9%、`shot.py` 83.7%、`model.py` 88.2%、`evidence.py` 88.9%（单行适配层），不影响总门槛。

## 4. 验收结果

| 命令 | 结果 |
|---|---|
| `python -m unittest discover -s tests -t . -q` | 1684 例，全部通过（0 失败 / 2 跳过） |
| `python scripts/measure_coverage.py --target attack-mcp-tool --min 90` | 退出码 0，94.4% |
| `python tools/attack_mcp_tool/cli.py --mode jsonrpc --path A..F` | 退出码 0，11/11 片段 |
| `check_tools_compile.py` / `check_glossary.py` / `check_token_budget.py --check` | PASS |
| `npx markdownlint-cli2`（两份文档） | 0 issue |

## 5. 未随本次修复处理

- D-2（`start()` 非幂等 / Windows 同端口双绑定）：**已按主线 11 阶段闭环**，见 §6。
- D-4（SKILL.md 未覆盖 mcp-09/10/11）：文档变更需与质量门条款同步评审。
- D-5 至 D-13：低危/流程项，建议随下次触碰该模块处理。

## 6. D-2 收口（主线 11 阶段）

- 规格：issue #464（v1 + v2 同 issue 追加）；归档 `docs/specs/attack-mcp-tool-d2-spec-v{1,2}.md`
- 工单：#465（A）/ #466（B）/ #467（C），`blocked-by` 链 465→466→467
- 调研：`docs/research/mcp-server-lifecycle-winsock-posix.md`
- 设计：`docs/operations/attack-mcp-tool-d2-server-lifecycle.md` §12
- 门禁记录：`docs/operations/attack-mcp-tool-d2-gate-stage{1..11}.md`
- PR 正文草稿：`docs/operations/attack-mcp-tool-d2-pr-body.md`（1,749B）；**未推送、未开 PR**

| 提交 | 内容 | 验证 |
|---|---|---|
| `0df38d4` | A：`start()` 幂等 + `is_running` | 1686 例全绿 |
| `d458f19` | B：所有权「谁启动谁关闭」 | 1689 例全绿 |
| `29736fe` | C：Windows `SO_EXCLUSIVEADDRUSE` | 1691 例全绿；覆盖率 94.3% |
| `08d6b85` | 审查修复：启动失败不留就绪态 | 1693 例全绿；覆盖率 94.4% |

阶段 10 双轴审查发现并修复的关键缺陷：`ensure_server` 原先先登记 `started_server` 再 `start()`，端口冲突抛错后会留下端口为占位 0 的死实例供后续步骤复用；现改为「先启动后登记」，并新增断言禁止复用 `:0/mcp`。

未关闭项：U-1（Linux `EADDRINUSE` 由 CI 验证）、U-2（长连接后重绑窗口仅以 50 次短连接近似）。
