# attack-multi-agent 双轴代码审查（阶段 10）

> **基线**：`git merge-base origin/main HEAD` 之后的攻击面新增（`tools/attack_multi_agent/` 全新、未跟踪）。
> **两轴并列**：Standards（编码规范）与 Spec（规格忠实度）。**硬违规阻断交付；判断项记录为改进项**。
> **判据源**：`docs/operations/attack-multi-agent-design.md`（v2 AC-01..AC-15 + 设计）、`GOVERNANCE` §6/§8.2、`CI-CD` S0–S4、`GLOSSARY.md`。

---

## 轴 1 — Standards（代码写得对不对）

| # | 检查 | 结果 | 分类 |
|---|---|---|---|
| S1 | `python -m py_compile tools/attack_multi_agent/*.py` | 通过 | — |
| S2 | 全量 `unittest`（attack-multi-agent 41 项） | 通过 | — |
| S3 | `python scripts/validate_skill.py` | 16 技能全部合规 | — |
| S4 | `python scripts/check_glossary.py`（本技能文件） | 无废弃术语（涉事两处已按 GLOSSARY 规范词改写） | — |
| S5 | 依赖方向单向、无第三方 HTTP 库 | `transport` 抽象 + `urllib`；`pyrit` 懒导入 | — |

### Standards 判断项（不阻断）
- **J1** `pyrit_attack.py` 行覆盖率 44%：仅测「未安装即显式报错」分支；成功路径依赖真实 `pyrit` 环境，按设计（B7 懒导入，CI 不装）留作带取证方式的核实路径。
- **J2** `shot.py` 覆盖率 79.3%（近门槛）：`HeadlessCapture` 真实浏览器分支仅以 mock 子进程验证成功写盘，未测超时/失败分支。
- **J3** `scanner.py` 变量名 `_UNEXPECTED_Egress` 命名不规范（功能正确），保留以免扰动调用面，登记为改进项。
- **J4** `runner.py` 多处内联 `__import__("re")`，建议提升为模块级 `import re`（可读性）。
- **S-硬违规：0**。

---

## 轴 2 — Spec（做的是不是要求的）

覆盖矩阵（AC → 实现 → 测试）：

| AC | 实现位置 | 测试证据 |
|---|---|---|
| AC-01 拓扑 | `runner._step_a2a_01` + `a2a.A2ABusClient.discover_topology` + `scanner.analyze` | `RunnerTests.test_full_run_all_eight_evidence`、`test_capability_missing_single_agent` |
| AC-02 消息操纵 | `_step_a2a_02` / `inject_message` | 全量运行 a2a-02 完全生效 |
| AC-03 冒充 | `_step_a2a_03` / `impersonate` | `A2AClientTests.test_bus_actions` |
| AC-04 记忆投毒 | `_step_a2a_04` / `read_memory`+`poison_memory` | `test_memory_and_orchestrator` |
| AC-05 上下文投毒 | `_step_a2a_05` / `poison_context` | 全量运行 |
| AC-06 工作流破坏 | `_step_a2a_06` / `disrupt_workflow` | 全量运行 |
| AC-07 下游取证 | `_step_a2a_07` / `get_trace` + `_ai_log` | 全量运行（trace 差异） |
| AC-08 flag 双通道 | `_step_a2a_08`（`flag_value`/`flag_panel` 同源） | `test_full_run_all_eight_evidence` 断言 flag |
| AC-09 证据三件套严格 | `runner._emit(strict=True)` 委托 `collect_evidence.py` | `test_evidence_gate_failure_raises`（门失败抛错） |
| AC-10 对象图 PyRIT 非主演 | `runner.OBJECT_GRAPH`（`lead=A2ASecBench/a2a-scanner`） | `PackageSurfaceTests` + 全量断言 `framework` |
| AC-11 框架缝 + 懒导入 | `scanner.py` seam、`pyrit_attack.py` 懒导入 | `ScannerTests`、`PyritSeamTests` |
| AC-12 四值互斥 + 封顶 | `grade.py` 纯函数 | `GradeTests`（四值/capped/consent） |
| AC-13 截图缺失不伪造 | `shot.NullCapture` + `_emit` 标「待补录」 | `EvidenceShotTests.test_captures` |
| AC-14 覆盖率 ≥80% | — | `measure_coverage.py --target attack-multi-agent`：**91.7%** |
| AC-15 单 agent 回退 | `_step_a2a_01` capability_missing 分支 | `test_capability_missing_single_agent`（已跳过 + 建议 attack-ai-agent） |

### Spec 判断项
- **P1** AC-07 的「AI 交互日志」在离线路径恒为 `prompted=True` 生成的构造串；真实目标的 AI 日志需在演练环境以实测响应替换（非缺陷，属取证环境约束）。
- **Spec 硬违规：0**。规格覆盖矩阵无空格。

---

## 门禁套件结果

| 命令 | 结果 |
|---|---|
| `python -m py_compile tools/attack_multi_agent/*.py` | 通过 |
| `python -m unittest discover -s tests -p "test_attack_multi_agent*.py"` | 41 通过 / 0 失败 |
| `python scripts/measure_coverage.py --target attack-multi-agent --min 80` | 841/917 = **91.7%**（≥80） |
| `python scripts/validate_skill.py` | PASS（16 技能） |
| `python scripts/check_glossary.py`（本技能文件） | 干净 |

---

## 结论

- **硬违规总数：0** → 本阶段判定 **PASS**（就本技能交付面而言）。
- 判断项 J1–J4、P1 记录为改进项，不阻断。
- **外部阻塞（非本技能缺陷，独立于本 PR）**：共享工作树正被并行多技能任务写入，`GLOSSARY.md` 与 `docs/operations/skill-mainline-workflow.md` 触发 token 预算 `BLOCKED`（+6039 / +908 字节，均非本技能改动）；`scripts/measure_coverage.py`、`.github/workflows/ci.yml` 亦被他方未提交修改占用。推送/建 PR 前须与并行任务串行，避免纠缠。

---

## 复审：SKILL.md 逐条对齐（2026-11-15 收尾轮）

按「SKILL.md 所列 tool 与功能逐项核对」重跑比对，发现并修复 2 处规范—实现不一致（其余 8 步、三路径、质量门、失败与豁免均一致）：

| 编号 | 差异 | 修复 |
|---|---|---|
| G1 | SKILL.md 攻击路径 A/B/C 点名的 5 个示意脚本（`msg_inject.py` / `agent_impersonate.py` / `memory_poison.py` / `context_poison.py` / `workflow_disrupt.py`）不存在，命令不可字面执行 → 违反「copy/paste 可复现」校验标准 | 新增 5 个顶层薄壳 + 共享 `poc.py`（逻辑全委托 `a2a.py`，C1）；`DryRunClient` 支持离线 `--dry-run` 且命令同源；注册 `ci.yml` py_compile 与覆盖率目标 |
| G2 | 设计 R5「疑似诱饵机 ≤30 分钟结束」无落地痕迹 | `_step_a2a_01` 无协同面分支补注记（改走 `attack-ai-agent` + 依 `decoy-detect` 判定后 ≤30 分钟结束） |

复审后门禁：`py_compile` 通过；`unittest` **52 通过 / 0 失败**（新增 `test_attack_multi_agent_tools.py` 11 例）；覆盖率 **93.0%**（964/1037，门槛 80%）。
SKILL.md 20 项规范点（7 前置/8 步骤/2 收尾/3 质量门组/3 校验标准/4 豁免条款）逐条有实现或证据落点，**遗漏 0**。
