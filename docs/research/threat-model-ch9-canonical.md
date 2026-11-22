# threat-model Ch9 身份链信任建模事实索引

> v1.0 · 已核实 · 上游 `skills/threat-model/SKILL.md` · 课程源 Ch9 图3、Table 2
> 框架组合取矩阵 ⑬（方法论 MITRE ATLAS/OWASP + 文档；框架是被建模对象）。

## 0. 结论
Ch9 两类身份链是既有 threat-model「信任边界与最短路径」需要纳入的新型边界：IAM assume-role 链（图3）与 K8s 双身份能力互补链（Table 2）。二者均可归一为「节点=身份、边=可扮演/可读凭据/可建负载」的有向图，供最短路径排序。

## 1. 已核实
| # | 事实 | 来源 |
|---|---|---|
| M-1 | IAM assume-role 链：DataScientistRole→MLOpsRole→SageMakerExecutionRole，末端托管策略打破项目边界 | Ch9 图3、L215-698 |
| M-2 | K8s 双身份：inference-sa(读 secrets) + argo-workflow-controller(建 pods)，单独不足、组合可接管 | Ch9 Table 2、L2274-2279 |
| M-3 | 既有 threat-model 输出含信任边界 + 最短攻击路径 + 优先级攻击图 | `skills/threat-model/SKILL.md` §2 |
| M-4 | 框架组合 ⑬（方法论，无专用框架） | 矩阵 ⑬ |

## 2. 映射
| 能力 | 成功判据 | 失败分支 |
|---|---|---|
| iam-chain-graph | 给角色链 → 输出节点/边/末端跨边界标记 | 链空 → 空图 |
| k8s-identity-chain | 两身份能力互补 → 标记路径可达、缺口 | 不互补 → 记录缺口 |

## 3. 门禁（阶段 1）
| 编号 | 变更项 | 判定 | 复验命令 | 结论 |
|---|---|---|---|---|
| B7 | M-4 方法论 | 符合 | `grep -nE "pyrit\.orchestrator\|Orchestrator" tools/threat_model/ch9_identity_chain.py` → 无 | PASS |
| B8 | M-1..M-4 带来源 | 符合 | `grep -c "Ch9\|矩阵" docs/research/threat-model-ch9-canonical.md` | PASS |
| B9 | 矩阵 ⑬ | 符合 | `sed -n '121,125p' docs/research/osai-skill-framework-matrix.md` | PASS |
