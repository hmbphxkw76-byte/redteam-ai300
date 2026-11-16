# attack-multi-agent 修复回归验证报告

> 验证对象：PR #250（`e6a9f24`）合并的 F1/F2/F3 三项修复
> 基线：`origin/main` @ `e6a9f24`（干净 worktree `feat/attack-ma-regression-verify`）
> 验证时间：2026-11-15

## 一、结论先行

三项修复（F1 拓扑解析假阳性、F2 前后对照假阳性、F3 截图状态虚报）**均已确认修复且未引入回归**。全量 628 测试通过、覆盖率与静态门禁全绿、真实目标现场复验定级正确。另发现一处**低严重度**残余边界（F1-edge，空值标签可跨行"借用"下一行词），建议后续一行修复。

## 二、验证范围与方式

| 层级 | 内容 | 结果 |
|---|---|---|
| 静态核对 | 合并代码中 F1/F2/F3 落点逐行确认 | 语义正确 |
| 单元测试 | attack-multi-agent 4 文件 54 例 + collect_evidence 6 例 | OK |
| 全量回归 | `unittest discover -s tests` | **628 OK（skipped=2）** |
| 覆盖率 | `--target attack-multi-agent` / `--target all` | 93.0% / 91.3% |
| 静态门禁 | validate_skill / check_glossary / check_token_budget | 全 PASS |
| 现场复验 | DVAA `192.168.40.183:9000` 实跑 8 步 | 定级修正 |

## 三、逐项验证结果

### F1 — 拓扑解析假阳性（`model.py` `parse_topology`）

**修复**：`_AGENT_RE` 增加负向后顾 `(?<![A-Za-z0-9_])` 且冒号由可选改为必选 `[:：]`。

| 边界用例 | 期望 | 实际 | 结果 |
|---|---|---|---|
| `agent: agentA\nagent: agentB\nbus: kafka` | 2 agents / bus | 2 / True | PASS |
| `The AI agent you're supposed to break`（原假阳性） | 0 | 0 | PASS |
| `break the agent you trust` | 0 | 0 | PASS |
| 驼峰词 `agentYou` | 0 | 0 | PASS |
| `智能体: alpha\n智能体: beta` | 2 | 2 | PASS |
| `节点: node-1` | 1 | 1 | PASS |
| 无冒号 `we have an agent network` | 0 | 0 | PASS |
| 空输入 | 0 | 0 | PASS |
| **`agent: \nagent:`（空值标签）** | 0 | **1** | **FAIL（F1-edge）** |

现场复验：DVAA 上 `a2a-01` 由误判「完全生效」→ 正确「已跳过」（`agent 数=0`）。

### F2 — 前后对照假阳性（`runner.py` `_step_a2a_04`）

**修复**：`judge = det and before_after_diff(...)`，前后对照判据门控于「写入被受理」。

| 场景 | 期望 | 实际 | 结果 |
|---|---|---|---|
| 写入被拒（404，det=False） | 未生效 | 未生效 | PASS |
| 写入被接受 + 有差异 | 完全/部分生效 | 完全生效 | PASS |
| 单元：`message_accepted('404')` | False | False | PASS |
| 单元：`before_after_diff('x','x')` | False | False | PASS |
| 单元：`before_after_diff(None,'b')` | False | False | PASS |

现场复验：DVAA 上 `a2a-04` 由误判「部分生效」→ 正确「未生效」（记忆写入未接受）。

### F3 — 截图状态虚报（`collect_evidence.py`）

**修复**：新增 `shot_status` 三态字段（已提供/待补录/缺失），校验表如实标注；`complete` 语义保持不变。

| 场景 | 期望 shot_status | 实际 | 结果 |
|---|---|---|---|
| `shot_cmd` 单独存在 | 待补录 | 待补录（钩子命令已记录） | PASS |
| 有真实截图文件 | 已提供 | 已提供 | PASS |
| 两者皆无 | 缺失 | 缺失 | PASS |
| 待补录仍 `complete=True`（保持 attack-mcp-tool AC-13 契约） | True | True | PASS |

## 四、回归确认

- 全量测试 628 例（较修复前 626 例 +2，来自 F1/F2 新增回归用例），`OK（skipped=2）`，exit 0。
- 覆盖率 `--target all` 91.3%（≥80%）、`--target attack-multi-agent` 93.0%。
- `validate_skill`（16 技能）、`check_glossary`（50 废弃术语）、`check_token_budget` 全 PASS。
- 现场复验 8 步定级均诚实，无新增假阳性（a2a-02/03/05/06/07「未生效」、a2a-08「已跳过」符合非总线目标预期）。

## 五、发现的问题与后续处理建议

| 编号 | 严重度 | 问题 | 建议 |
|---|---|---|---|
| F1-edge | 低 | `_AGENT_RE` 冒号后 `\s*` 允许跨行，空值标签（如行尾 `agent:`）可"借用"下一行首词作为值，导致 `agent_count` 虚增 1 或误认总线/其它标签词为 agent | 将冒号后的 `\s*` 收紧为水平空白 `[ \t]*`（一行改动），使值必须与标签同行；补 1 个回归用例（`agent: \nbus: kafka` 期望 0 agent） |

其余无遗留问题。

## 六、修改闭环判定

- 原问题 F1/F2/F3：**已解决**（静态核对 + 边界验证 + 现场复验三重确认）。
- 回归：**未引入**（全量 628 测试、覆盖率、门禁、现场降级均正常）。
- 新发现 F1-edge：低严重度、一行修复，**不阻塞**当前功能，建议随下次 skill 变更一并修复。
