# osai-handoff-gateway 设计记录（阶段 6–7）

## 1. 模块与职责

纯增量扩展已合入的 `tools/osai_orchestrator/`，新增两个模块：

| 模块 | 职责 | 依赖方向 |
|---|---|---|
| `handoff.py` | 交接索引派生、H1–H6 校验、对齐矩阵数据 | → models |
| `d11_gateway.py` | D11 tracer bullet：面板值派生、侦察片段映射、提交门禁接线 | → handoff / 既有工具入口 |

## 2. 公开接口

- `derive_panel_flags(registry_text) -> dict[str, str]`：只解析 `面板=` 列。
- `recon_fragments_for_report(fragments, hosts) -> list`：按 host 显式映射，不依赖 `real_only` 过滤。
- `check_h1..check_h6(...) -> GateResult`：六段一致性校验。
- `submission_gate(...) -> GateResult`：组合断图、时间锚、加密判定。
- `ALIGNMENT_CLAIMS`：设计条款 ID → 实现锚点的机读映射。

## 3. seam 与注入

- 复用 `GateResult` / `Verdict`，不新建判定类型。
- 复用 `osai-orchestrator` 的 `Orchestrator` 作为组合入口。
- 命令执行经既有 `CommandRunner` 协议，测试用替身。

## 4. 领域术语（阶段 7）

不引入新术语。复用 `GLOSSARY.md` 既有条目：证据片段、五段式、flag 双通道、战利品、攻击链、编排层、评分器。`check_glossary.py` 为门禁。

## 5. 被否决方案

- 修改 `report_exam.index.build_index` 的 `real_only` 默认值：触碰既有消费者语义，违反零破坏。改用旁路映射。
- 在 `collect_evidence.py` 新增标志：改共享契约需升版本、改消费者登记，成本高且违反本次范围。
- 新建权威交接账本：违反 C1 单一事实源与候选 A 的「派生索引」定义。
