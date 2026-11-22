## 工程规格定稿 (v2) — threat-model Ch9 C3 身份链资产化加固

> 本文为 issue #400 规格 v1 的工程定稿（v2），v1 全文保留；差异见文末。

### 验收条件（布尔化）

| ID | 布尔验收条件 | 检查命令/判据 | C3 |
|---|---|---|---|
| AC-01 | IAM 链 A→B→C → 每角色一 `asset_id`（`iam-<role>` 稳定），depends_on 前序角色 | 单测 | L5-14/图3 |
| AC-02 | 同一角色输入两次 → 相同 asset_id（稳定可引用，无随机） | 单测 | P-2 |
| AC-03 | K8s 双 SA 能力互补 → 可达路径；缺 secrets 读或缺 pods 写 → gap 明确 | 单测 | L47-52/T2 |
| AC-04 | 每 AssumeRole 边 → TrustBoundary 实体（trust_type=role_assumption，is_gap 按 enforcement）；SA 互补 → identity_collapse 边界 | 单测 | M5-5 |
| AC-05 | `asset_ids_for` 返回下游可按 ID 引用的资产 ID 列表（attack-infra/foothold 可消费） | 单测 | M5-6 |
| AC-06 | `shortest_for_chain` 复用既有 `boundaries.shortest_paths`，不改其签名/语义；路径 status 按 depends_on 可达性 | 单测 | P-3 |
| AC-07 | `IdentityChainVerdict` frozen + dict shim；轻量版 6 例零回归 | 单测 | P-1 |
| AC-08 | 不执行 assume-role/token/云/K8s API；模块无网络调用 | 源码 grep + 单测 | P-4 |
| AC-09 | `decoy.py`/`graph.py`/`boundaries.py`/`model.py` 零 diff；诱饵判定与优先级图语义不变 | git diff + 单测 | P-3 |
| AC-10 | 新增模块行覆盖率 ≥90% | `python scripts/verify_tm_c3_coverage.py --min 90` | 本轮门槛 |
| AC-11 | SKILL.md Ch9 段引用逐条字面存在；全量 unittest + 门禁全 PASS | `verify_tm_c3_skill_refs.py` + 实跑 | 收口 |

### 测试决策
- 只断言外部行为：资产 ID、边界实体、路径复用、下游引用、dict shim；离线无网络。
- 覆盖率 tracer 复用共享脚本（C1），≥90%。

### 门禁映射
AC-01..09 → 单测(S2)；AC-10 → 覆盖率脚本；AC-11 → 引用核验 + 全量门禁。

### 风险闸
- R-1：角色 ARN/SA 名为演练输入，本模块不虚构；不阻断。
- P-3：不改诱饵/优先级语义；不阻断。

### v1→v2 差异
1. 10 条 US 收敛为 11 条布尔 AC；2. AC-02 明确 asset_id 稳定性；3. AC-04/06 明确边界实体与路径复用既有判据；4. AC-09 锁定既有模块零 diff；5. AC-10 门槛 80%→≥90%；6. AC-11 明确引用核对。
