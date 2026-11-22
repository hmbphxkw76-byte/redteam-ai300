## Problem Statement

既有 C3 轻量版（PR #369）只把 IAM 角色链与 K8s SA 能力互补归一为裸 dict 图与可达性，缺稳定 `asset_id` 资产、缺信任边界实体、缺可被下游按资产 ID 引用的最短路径；attack-infra/foothold-traditional 无法据其定位角色链资产，编排层也无法把身份链并入既有优先级图。

## Solution

在 `ch9_identity_chain.py` 之上新增类型化模型：定义 `IdentityChainVerdict`（frozen + dict shim），提供 `to_assets`（角色/SA → 稳定 asset_id 资产，depends_on 前序）、`to_boundaries`（AssumeRole / SA 互补 → TrustBoundary 实体）、`to_shortest_paths`（复用既有 `boundaries.shortest_paths`），并暴露 `asset_ids_for` 供下游按 ID 引用。既有诱饵判定与优先级图语义零改动。

## User Stories

1. 作为分析师，我想把 IAM 角色链 A→B→C 建模为带稳定 ID 的资产与边，以便引用（L5-14/图3）。
2. 我想把 K8s SA 双身份能力互补建模为可达路径与缺口（L47-52/T2）。
3. 我想每次 AssumeRole 生成信任边界实体（含 identity_collapse 标记），以便并入信任边界图。
4. 作为下游 attack-infra，我想按 asset_id 取身份链资产，以便定位 IAM 角色（ch9_iam）。
5. 作为下游 foothold-traditional，我想按 asset_id 定位主机/SA，以便衔接立足点。
6. 作为编排者，我想身份链资产并入既有 shortest_paths 且不改优先级图语义，以便零迁移。
7. 作为评审者，我想诱饵判定零回归，以便不误判资产价值。
8. 作为质量负责人，我想覆盖率 ≥90%，以便满足本轮门槛。
9. 作为评审者，我想 SKILL.md 引用逐条字面存在，以便端到端复核。
10. 作为维护者，我想轻量版 dict 访问零回归，以便不破坏既有调用方。

## Implementation Decisions

- 新增 `ch9_c3_model.py`：`IdentityChainVerdict` frozen dataclass + dict shim；asset/边界/路径为追加产物。
- 重写 `ch9_identity_chain.py`：保留 `iam_chain_graph`/`k8s_identity_chain` 公开名与 dict 访问，新增 `to_assets`/`to_boundaries`/`asset_ids_for`/`shortest_for_chain`。
- 资产 ID 规范化：`iam-<role>` / `k8s-sa-<name>`，只含安全字符，稳定可引用（P-2）。
- 复用既有 `boundaries.shortest_paths` 与 `model.TrustBoundary`/`AssetView`，不复制判据（C1）。
- 独立覆盖脚本 `verify_tm_c3_coverage.py` 复用 `measure_coverage.measure()`，零共享文件改动。

## Testing Decisions

- 只断言外部行为：资产 ID 稳定/引用、边界实体、路径复用、诱饵/优先级图零回归、dict shim。
- 覆盖 IAM 链/K8s 可达/缺口/边界/引用/下游可消费；离线。
- 覆盖率 tracer 复用共享脚本，≥90%。

## Out of Scope

- 不执行 assume-role/token 提取、不调用云/K8s API。
- 不改 `decoy.py`/`graph.py`/`boundaries.py`/`model.py` 既有判据与优先级语义。
- 不引入 PyRIT 或任何 AI 框架（矩阵 ①）。

## Further Notes

- 事实见 `docs/research/threat-model-c3-hardening-canonical.md`（M5-1..M5-7、P-1..P-4）。
- 上游轻量版事实 `threat-model-ch9-canonical.md` 保留，本轮只升级模型与下游可引用性。
