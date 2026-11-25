## 工程规格定稿 (v2) — attack-supply-chain Ch9 B6 边界加固

> 本文为 issue #378 规格 v1 的工程定稿（v2），v1 全文保留；差异见文末。

### 验收条件（布尔化）

| ID | 布尔验收条件 | 检查命令/判据 | Ch9 |
|---|---|---|---|
| AC-01 | 仅运行时信号（sidecar/init/共享卷/exec）→ `owner=attack-infra` 且 `transfer_to` 含 `tools/attack_infra/ch9_container.py#writable_shared_volume` | 单测断言 | L54-55 |
| AC-02 | 仅工件信号（model/artifact/minio/registry/投毒）→ `owner=attack-supply-chain` 且 `transfer_to` 指向本技能 Ch8 模块 | 单测 | L53 |
| AC-03 | 双向信号 → owner=本技能且 `confidence=ambiguous`，reason 含两类信号标记 | 单测 | B6-3 |
| AC-04 | 无信号 → owner 空、reason=no_signal、transfer_to 空 | 单测 | — |
| AC-05 | `BoundaryVerdict` 为 frozen dataclass；reason 属固定枚举；非法 reason 构造抛 ValueError | 单测 | P-1 |
| AC-06 | 每次判定生成 `collect_evidence.py --step <id> --cmd --output --shot-cmd --strict` argv；strict 非零 → `evidence_ok=False` | 单测 + argv 断言 | B6-4 |
| AC-07 | `--strict` 参数不可省略；argv 无 shell=True；命令可直接 copy/paste | 源码 grep + argv 断言 | C8 |
| AC-08 | dict 兼容访问 `v["owner"]`/`v.get("transfer_to")` 有效，轻量版测试零回归 | 单测 | AC-12 关联 |
| AC-09 | 新增模块行覆盖率 ≥90% | `python scripts/verify_asc_b6_coverage.py --min 90` | 本轮门槛 |
| AC-10 | SKILL.md Ch9 段引用的模块/函数/路径字面存在 | `python scripts/verify_asc_b6_skill_refs.py` | 收口要求 |
| AC-11 | Ch8 既有投毒模块零 diff；既有 attack-infra/ trad 判据零 diff | git diff 核对 | P-4 |
| AC-12 | 全量 unittest 零回归；check_glossary / validate_skill / check_token_budget 全 PASS | 实跑 | — |

### 测试决策
- 只断言外部行为；FakeCommand 离线；覆盖 4 类路由 + 证据 2 路径 + frozen/兼容 shim。
- 覆盖率 tracer 复用 `scripts/measure_coverage.py#measure`（C1），不改共享 manifest。

### 门禁映射
AC-01..08 → 单测(S2)；AC-09 → 覆盖率脚本；AC-10 → 引用核验；AC-11/12 → diff + 全量门禁。

### 风险闸
- R-1：信号词表为教学级启发式，`ambiguous` 须人工复核，不作自动提权依据；不阻断。
- P-4：不实现 Sidecar 拦截本体、不改投毒判据；不阻断。

### v1→v2 差异
1. 8 条 US 收敛为 12 条布尔 AC；2. 补门禁映射与复现命令；3. AC-05 明确 frozen dataclass + reason 枚举；4. AC-08 明确 dict 兼容零回归；5. AC-09 门槛由 CI 80% 抬至 ≥90%；6. AC-10 明确 SKILL.md 引用逐条核对。
