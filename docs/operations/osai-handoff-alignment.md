# 候选 A 实施对齐矩阵（阶段 10–11）

> **用途**：逐条核对 `docs/research/osai-skill-handoff-design.md` 的候选 A 设计条款是否落地，验证「无偏离」。
> **机读源**：`tools/osai_orchestrator/handoff.py#ALIGNMENT_CLAIMS` 与 `#verify_alignment()`。
> **结论口径**：缺失项为空 = 对齐；任何缺失即 BLOCKED，停留原阶段重跑。

## 1. 对齐条款（A1–A8）

| ID | 设计条款 | 实现锚点 | 测试用例 | 判定 |
|---|---|---|---|---|
| A1 | 以 `step_id` 为贯穿六段交接的唯一关联键 | `handoff.py#derive_panel_flags`、`#recon_fragments_for_report`（按 step/host 关联） | `test_handoff.py::PanelFlagsTest`、`::ReconMappingTest` | 符合 |
| A2 | 派生式交接索引，不新增权威存储 | `handoff.py#all_checks`（纯函数，随用随算，无落盘） | `test_handoff.py::HandoffChecksTest` | 符合 |
| A3 | 三份契约为路径指针，不复制正文 | `handoff.py#ASSET_FIELDS`（指针到 `recon_ai/model.py#ASSET_FIELDS`）、`registry.py#parse_dual`、`contract.md#3` | `test_orchestrator_evidence_contract.py` | 符合 |
| A4 | H1–H6 旁路校验，输出 GateResult PASS/BLOCKED | `handoff.py#check_h1..check_h6` | `test_handoff.py::HandoffChecksTest`（每 H 一通过一失败） | 符合 |
| A5 | tracer bullet 落在 D11 报告提交边界 | `d11_gateway.py#run_d11_gateway`（仅 H5/H6） | `test_d11_gateway.py::GatewayTest` | 符合 |
| A6 | 零破坏：既有 skill/tool 语义不修改 | `git diff --name-only` 不含既有实现目录；仅新增两模块 + 清单登记 | 工作树核验 + 全量测试 | 符合 |
| A7 | P0 优先断图/时间锚/加密与双通道字段分离 | `d11_gateway.py#check_h6_submission`、`handoff.py#check_h3_dual_channel` | `test_d11_gateway.py`、`test_handoff.py::test_h3_*` | 符合 |
| A8 | 可机读对齐矩阵验证无偏离 | `handoff.py#ALIGNMENT_CLAIMS` + `#verify_alignment` | `test_handoff.py::AlignmentTest` | 符合 |

## 2. 机读验证

```text
python -c "from tools.osai_orchestrator.handoff import ALIGNMENT_CLAIMS, verify_alignment; print(verify_alignment(ALIGNMENT_CLAIMS, set(ALIGNMENT_CLAIMS)))"
```

预期输出：`[]`（空列表 = 无缺失 = 无偏离）。

## 3. 偏差处置

- 任何条款缺失：结论 BLOCKED，停留阶段 10 重跑，不以后续补做替代。
- 若确需偏离候选 A：按 GOVERNANCE §8.3 显式声明理由与影响半径，并重新走阶段 2/3 规格。

## 4. 与既有工具的关系

本模块只读取既有产物（登记簿文本、证据片段、报告路径、时间锚文件），调用 `scripts/check_report_assets.py`，不修改 `collect_evidence.py` / `report_exam` / `verify_evidence` 的任何判据或默认值。设计文档 §8 所列「确需改既有消费者」的情形本次未发生。
