# attack-supply-chain Ch9 边界事实索引

> v1.0 · 已核实 · 上游 `skills/attack-supply-chain/SKILL.md` · 课程源 Ch9 L54-55（运行时拦截）/ L53（工件凭据）
> 框架组合取矩阵 ⑪（ModelScan + ART + PyRIT 证据）；PyRIT 非主角。

## 0. 结论
Ch9 同时出现两类操作：① Sidecar/init 共享卷拦截推理请求（L54-55）——属运行时基础设施利用，归 attack-infra B2；② MinIO/MLflow 工件凭据外带与模型投毒（L53、既有 Ch8）——属供应链，归本技能。二者须显式划界避免重复实现。

## 1. 已核实
| # | 事实 | 来源 |
|---|---|---|
| S-1 | Sidecar/init 共享卷拦截在 ml-inference namespace、由 inference-sa exec 实现 | Ch9 L54-55；`attack-infra-ch9-canonical.md` C-6 |
| S-2 | MinIO/MLflow/Postgres 凭据在 pipeline-system secrets，用于工件访问与投毒 | Ch9 L53、Listing 53 |
| S-3 | 本技能既有面为模型/数据/依赖投毒（Ch8 G1-G14） | `docs/research/attack-supply-chain-ch8-canonical.md` |
| S-4 | 框架组合 ⑪ | 矩阵 ⑪ |

## 2. 映射
| 观察 | owner | 判据 |
|---|---|---|
| 含 sidecar/init/request-queue/共享卷/exec | attack-infra | S-1 |
| 含 model/artifact/minio/ecr/registry/dataset/投毒 | 本技能 | S-2/S-3 |
| 双向信号 | 本技能优先 + ambiguous 标记 | S-1/S-2 交叉 |

## 3. 门禁（阶段 1）
| 编号 | 变更项 | 判定 | 复验命令 | 结论 |
|---|---|---|---|---|
| B7 | S-4 框架组合 | 符合 | `grep -nE "pyrit\.orchestrator\|Orchestrator" tools/attack_supply_chain/ch9_boundary.py` → 无 | PASS |
| B8 | S-1..S-4 带来源 | 符合 | `grep -c "Ch9\|矩阵" docs/research/attack-supply-chain-ch9-canonical.md` | PASS |
| B9 | 矩阵 ⑪ | 符合 | `sed -n '110,116p' docs/research/osai-skill-framework-matrix.md` | PASS |
