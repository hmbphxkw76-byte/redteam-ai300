# threat-model Ch9 C3 身份链加固事实索引

> **版本** v1.0 · **状态** 已核实 · **性质** 本轮加固单一可信源
> **取证日期** 2026-11-22 · **上游轻量版** `docs/research/threat-model-ch9-canonical.md`（M-1..M-4，保留）

## 0. 结论
1. C3 把两类身份链纳入既有信任边界与最短攻击路径图：IAM 角色链（Listing 5-14、图 3）与 K8s SA 身份链（Listing 47-52、Table 2）。
2. 轻量版（PR #369）仅返裸 dict 图与可达性，无 `asset_id` 资产、无信任边界实体、无可供下游按 ID 引用的最短路径；本轮升级为类型化 `IdentityChainVerdict` + 资产/边界/路径模型，供 attack-infra/foothold-traditional 按 `asset_id` 引用。
3. 既有诱饵判定（`decoy.py`）与优先级图语义（`graph.py`/`boundaries.py`/`shortest_paths`）零改动：本轮只在既有图输入侧追加身份链资产。

## 1. 已核实清单

| # | 事实 | 来源 |
|---|---|---|
| M5-1 | IAM 角色链：用角色 A 凭据 assume 角色 B；会话上限 1 小时，transitive session tags 沿链传递 | <https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_terms-and-concepts.html>（一手，取证 2026-11-22） |
| M5-2 | IAM role 无长期凭据，assume 时给临时凭据；信任策略+权限策略双侧授权 | 同 M5-1（一手） |
| M5-3 | K8s SA 为 Pod 内进程身份；token 自动挂载于 `/var/run/secrets/kubernetes.io/serviceaccount/token`；可 `automountServiceAccountToken: false` 退出；TokenRequest 有界寿命 | <https://kubernetes.io/docs/tasks/configure-pod-container/configure-service-account/>（一手，取证 2026-11-22） |
| M5-4 | 双 SA 能力互补（secrets 读 + pods 写）→ 凭证外带+提权路径（Table 2） | 课程 Listing 47-52 / Table 2；上游 M-3 |
| M5-5 | 既有信任边界实体 `TrustBoundary`（含 `identity_collapse`/`is_gap`）；最短路径 `shortest_paths(assets,...)` 按 `asset_id`/`depends_on`/`score_class` 计算 | 本仓 `tools/threat_model/boundaries.py:12,43`（一手） |
| M5-6 | 资产 ID 稳定唯一；下游 `attack_infra/ch9_iam.py` 消费 `ctx.iam_chain`、`foothold-traditional` 消费资产 ID 定位主机 | 本仓 `tools/attack_infra/ch9_iam.py:179`；`model.py:150`（一手） |
| M5-7 | 框架组合 ① 零攻击框架参与纯分析 | `docs/research/osai-skill-framework-matrix.md` ① |

## 2. 身份链 → 资产/边界/路径映射

| 链 | 资产（asset_id） | 信任边界 | 最短路径 |
|---|---|---|---|
| IAM A→B→C（L5-14/图3） | `iam-<role>` 每角色一资产，depends_on 前序角色 | 每 `sts:AssumeRole` 一条 TrustBoundary（trust_type=role_assumption） | 沿 depends_on 链，status 由可达性定 |
| K8s SA A+B（L47-52/T2） | `k8s-sa-<name>` 每 SA 一资产 | secrets.read→pods.create 互补为 identity_collapse 边界 | 可达时 path=["secrets.read","credentials.exfil","pods.create"] |

## 3. 判据前提与陷阱
- **P-1 类型化**：`IdentityChainVerdict` frozen dataclass + dict shim；不改既有图语义。
- **P-2 资产 ID 稳定**：基于角色/SA 名规范化生成，可被下游按 ID 引用；不生成随机 ID。
- **P-3 零回归**：`decoy.py`/`graph.py`/`boundaries.py` 的判定与优先级语义零 diff；身份链资产作为**新增输入**追加。
- **P-4 只读**：不执行 assume-role/token 提取；只归一上游观测。

## 4. 待核实 / 已排除
- **R-1**：角色链具体 ARN 与 SA 名为演练输入，本模块不虚构；不阻断。
- **D-1**：不执行云/K8s API、不改诱饵/优先级语义、不引入 AI 框架。

## 5. 门禁记录（阶段 1）

| 编号 | 本阶段变更项 | 判定 | 复验命令 | 结论 |
|---|---|---|---|---|
| B7 | M5-7 零攻击框架 | 符合 | `grep -rnE "pyrit\.orchestrator|Orchestrator|AzureOpenAIChatTarget" tools/threat_model/ch9_c3*.py` → 无 | PASS |
| B8 | M5-1..M5-7 带来源 | 符合 | `grep -c "https://\|本仓\|课程\|矩阵" docs/research/threat-model-c3-hardening-canonical.md` | PASS |
| B9 | 框架组合 ① | 符合 | `sed -n '55,59p' docs/research/osai-skill-framework-matrix.md` | PASS |

**阶段结论**：`PASS`。复验：`python scripts/check_glossary.py && python scripts/validate_skill.py`。
