# 设计记录 — threat-model Ch9 C3 身份链资产化加固（阶段 6）

> 判据事实源：`docs/research/threat-model-c3-hardening-canonical.md`；本文件只记模块/接口/依赖方向。

## 1. seam 决策
- 复用既有 `model.AssetView`/`TrustBoundary`/`boundaries.shortest_paths` 为唯一资产/边界/路径实现（C1），不复制判据。
- 保留 `ch9_identity_chain.iam_chain_graph`/`k8s_identity_chain` 公开名与 dict 访问；新增类型化模型与资产化函数。

## 2. 模块与接口

| 模块 | 单一职责 | 公开接口 | 依赖 |
|---|---|---|---|
| `ch9_c3_model` | 类型化身份链结论 | `IdentityChainVerdict`, `asset_id_for`, `CHAIN_KINDS` | 标准库 |
| `ch9_identity_chain` | IAM/K8s 链归一 + 资产/边界/路径投影 | `iam_chain_graph`, `k8s_identity_chain`, `to_assets`, `to_boundaries`, `asset_ids_for`, `shortest_for_chain` | `ch9_c3_model`, `model`, `boundaries` |
| `ch9_c3_downstream` | 下游按 asset_id 引用探针 | `claim_ids`, `compatible_with_iam_ctx` | `ch9_identity_chain` |

## 3. 依赖方向（无环）
```
ch9_c3_downstream → ch9_identity_chain → ch9_c3_model → (标准库)
                                       → model / boundaries（既有，只读复用）
```
`ch9_c3_model` 不 import 本项目模块。

## 4. 测试替身
离线构造角色名/能力 dict；用真实 `boundaries.shortest_paths` 验路径复用；不 mock 既有判据。

## 5. 权衡与否决
- 否决：改 `scripts/tools_manifest.json`/`measure_coverage.py` 注册 target——共享文件其它 worktree staged（ADR-0006）；用独立脚本复用 tracer。
- 否决：改 `decoy.py`/`graph.py`/`boundaries.py`/`model.py`（P-3 零回归）。
- 否决：执行 assume-role/token 提取（P-4）。

## 6. 覆盖率
≥90%；`verify_tm_c3_coverage.py --min 90` 复用 `measure_coverage.measure()`。

## 7. 冲突标注
共享六项（GLOSSARY/check_token_budget/measure_coverage/tools_manifest/ci.yml/collect_evidence 契约）本分支零 delta。
