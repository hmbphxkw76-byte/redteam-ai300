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

U-1 已由 CI 验证关闭；U-2 见 §7。

## 7. 三项遗留收口（2026-11-27）

### U-2 长连接后的重绑窗口

新增用例 `test_rebind_while_slow_clients_hold_connections`：8 个客户端只发一半请求体，使 handler 阻塞在读取，再 `stop()` 并计时重绑。实测 **0.504 s**（窗口 2 s），**产品无需改动**；`stop()` 不主动断连在途连接属可接受设计，已由用例锁定。

### D-4 SKILL.md 补齐 mcp-09..11

按 `STEP_SPECS` 增补路径 D（mcp-10 MCP Apps UI 投毒）、E（mcp-09 沙箱逃逸）、F（mcp-11 工具链注入），含命令与 `collect_evidence` 取证行。SKILL.md 8,592B → **10,995B**（上限 14,000B），`validate_skill.py` PASS。

### D-12 主线留痕回填

13 个技能新增 **152 份文件**（11 技能补规格 v1/v2 共 22 份；13 技能各补 10 份门禁记录共 130 份）。口径为「**历史留痕回填**」：每份标注「不代表原流程按序执行」，数字均为本次复跑或既有产物，阶段 4/5/10 无独立产物者记 `替代（回溯）` 并写明「未发生」。

- `validate_skill_mainline.py --strict` → **退出码 0，20/20 PASS，根层影子规格 0**
- 覆盖率（本次复测）：attack-ai-agent 86.1%、attack-embeddings 89.4%、attack-infra 90.8%、attack-mcp-tool 94.4%、attack-multi-agent 89.4%、attack-rag 92.0%、decoy-detect 95.3%、loot-manage 91.6%、osai-orchestrator 93.1%、recon-ai 85.3%、report-exam 97.0%、threat-model 87.3%
- 口径差异已如实标注：manifest 登记的测试模块少于实际目录（如 attack-ai-agent 66 vs 93、recon-ai 123 vs 180）；`foothold-traditional` **未登记覆盖率目标**，其记录写明「无覆盖率数值」，未编造百分比

### 残余项（2026-11-27 已全部收口）

- 覆盖率目标：`foothold-traditional` 与 `capstone-rehearse` 已登记，`osai-orchestrator` 补 `skill` 字段；实测 97.6% / 90.2%。同时修掉 `measure_coverage` 的两处缺陷（硬编码目标白名单、`reload` 致 `isinstance` 失效），并新增守卫用例 `tests/shared_tools/test_coverage_targets.py`。
- 超 2KB 记录：`capstone-rehearse-gate-stage11.md` → 1,985B、`tooling-automate-gate-stage9.md` → 1,974B，判定与证据列完整保留。
- 阶段 9 / 11 真实留痕：`docs/operations/mainline-residuals-gate-stage{9,11}.md`，以本轮变更域为对象，非技能级回填。
