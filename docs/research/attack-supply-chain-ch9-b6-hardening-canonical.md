# attack-supply-chain Ch9 B6 边界加固事实索引

> **版本** v1.0 · **状态** 已核实 · **性质** 本轮加固单一可信源
> **取证日期** 2026-11-22 · **上游轻量版** `docs/research/attack-supply-chain-ch9-canonical.md`（S-1..S-4，保留不推翻）
> **框架组合（矩阵 ⑪）** ModelScan + IBM ART + PyRIT(证据) + 自定义；PyRIT 非攻击主角。

## 0. 结论
1. B6 的职责边界不是新增攻击能力，而是**路由判据**：把 Ch9 观察归类为「运行时 Sidecar 拦截（转 attack-infra B2）」或「工件投毒（本技能既有 Ch8 G1-G14）」，避免两技能重复实现同一手法。
2. 轻量版（PR #363）的 `ch9_boundary.classify` 仅返回裸 dict、无类型、无转交目标、无证据留痕；本轮升级为类型化 `BoundaryVerdict` + 显式转交规则 + `collect_evidence.py --strict` 证据契约，覆盖 ≥90%。
3. 不改动既有投毒判据：本轮只新增边界路由模块与 SKILL.md 段，Ch8 各模块零 diff。

## 1. 已核实清单（一手源逐条 / C1 指针）

| # | 事实 | 来源 | 课程锚点 |
|---|---|---|---|
| B6-1 | Sidecar/init 共享卷拦截推理请求与请求篡改属运行时基础设施利用，由 attack-infra B2 实现：`tools/attack_infra/ch9_container.py#writable_shared_volume`（ch9-ctr-01）与 `#intercept_verdict`（ch9-ctr-02） | 本仓 `tools/attack_infra/ch9_container.py:27,54`（一手实现）；上游 S-1 | L54-55 |
| B6-2 | MinIO/MLflow/Postgres 工件凭据外带与模型投毒属供应链，由本技能既有 `ch8_poison` / `mcp_backdoor` 等承担，本轮不新增 | 本仓 `docs/research/attack-supply-chain-ch8-canonical.md`；上游 S-2/S-3 | L53 |
| B6-3 | 边界歧义（同时含运行时与工件信号）须标 `ambiguous` 供人工复核，不得静默归一方 | 上游 S-1/S-2 交叉；安全判定原则 | — |
| B6-4 | 证据三件套（命令/输出/截图钩子）+ `--strict` 退出码契约为 C8 不可豁免 | `docs/contracts/collect_evidence.contract.md:29,34`；`AGENTS.md#C8` | — |
| B6-5 | 框架组合 ⑪ PyRIT 仅证据，边界路由为零框架纯判定 | `docs/research/osai-skill-framework-matrix.md` ⑪ | — |

## 2. 映射（要求↔事实↔判据）

| 观察 | owner | 转交目标 | 判据 |
|---|---|---|---|
| 仅 sidecar/init/request-queue/共享卷/exec | attack-infra | `attack-infra#ch9-ctr-01/02`（B6-1） | runtime_signals |
| 仅 model/artifact/minio/ecr/registry/dataset/投毒 | attack-supply-chain | 本技能 Ch8 既有模块（B6-2） | artifact_signals |
| 双向信号 | 本技能优先 + `ambiguous` | 人工复核（B6-3） | 双集合非空 |
| 无信号 | 空 owner | 不转交 | no_signal |

## 3. 判据前提与陷阱
- **P-1 类型化**：`BoundaryVerdict`（不可变 dataclass）含 owner/reason/confidence/transfer_to；reason 取固定枚举，杜绝裸 dict 漂移。
- **P-2 显式转交**：`transfer_to` 必须是 literal 路径#锚点（B6-1/B6-2），为空即无转交。
- **P-3 证据不可豁免**：每次边界判定经 `collect_evidence.py --strict` 落盘三件套（B6-4）。
- **P-4 零回归**：既有投毒判据（Ch8 G1-G14）与 trad/attack-infra 判据零 diff；不执行任何攻击载荷。

## 4. 待核实 / 已排除
- **R-1**：信号词表为教学级启发式，`ambiguous` 必须人工复核，不作自动提权依据；不阻断。
- **D-1**：不新增攻击手法、不实现 Sidecar 拦截本体（属 attack-infra）、不改动 Ch8 模块、不引入新框架。

## 5. 门禁记录（阶段 1）

| 编号 | 本阶段变更项 | 判定 | 复验命令 | 结论 |
|---|---|---|---|---|
| B7 | B6-5 零新增框架 | 符合 | `grep -rnE "pyrit\.orchestrator|Orchestrator" tools/attack_supply_chain/ch9_boundary*.py` → 无 | PASS |
| B8 | B6-1..B6-5 带来源 | 符合 | `grep -c "本仓\|docs/\|矩阵\|AGENTS" docs/research/attack-supply-chain-ch9-b6-hardening-canonical.md` | PASS |
| B9 | 框架组合 ⑪ | 符合 | `sed -n '109,113p' docs/research/osai-skill-framework-matrix.md` | PASS |

**阶段结论**：`PASS`。复验：`python scripts/check_glossary.py && python scripts/validate_skill.py`。
