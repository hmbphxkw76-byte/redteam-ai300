## Problem Statement

既有 B6 轻量版（PR #363）的 `ch9_boundary.classify` 仅返回裸 dict（`owner/reason/confidence`），既无类型化结论也无显式转交目标与证据留痕；编排层与评审者无法据此确定「运行时 Sidecar 拦截转给 attack-infra B2 的具体哪个步骤」、无法机器复核边界判定，覆盖率也未达本轮 ≥90% 要求。

## Solution

将边界判定升级为不可变 `BoundaryVerdict`（owner/reason/confidence/transfer_to/summary + 证据字段），`transfer_to` 以字面 `路径#锚点` 指向 attack-infra `ch9_container.py#writable_shared_volume`/`#intercept_verdict` 或本技能 Ch8 模块；每次判定经 `collect_evidence.py --strict` 落盘三件套。只做路由，不实现任何攻击、不改既有投毒判据。

## User Stories

1. 作为编排者，我想把 Ch9 观察自动归类为运行时拦截或产物投毒，以便不重复实现。
2. 我想判定结果含明确的转交目标（路径#锚点），以便直接移交 attack-infra B2。
3. 我想双向信号标 `ambiguous`，以便人工复核而非静默归类。
4. 作为评审者，我想每次边界判定有 `collect_evidence.py --strict` 三件套证据，以便复核。
5. 作为质量负责人，我想新增模块覆盖率 ≥90%，以便满足本轮门槛。
6. 作为维护者，我想既有 Ch8 投毒判据零 diff，以便零回归。
7. 作为评审者，我想 SKILL.md 引用的每个工具/模块/函数字面存在，以便端到端演示可复核。
8. 作为演练者，我想结论类型是固定的五值语义之一（此处为路由判定，owner 取三值），以便不漂移。

## Implementation Decisions

- 新增 `BoundaryVerdict` frozen dataclass；reason 取固定枚举；`transfer_to` 为字面路径指针（C1）。
- 保留 `classify()` 公开函数名与 dict 兼容访问（`__getitem__`/`.get`），使轻量版测试零回归。
- 新增 `ch9_boundary_evidence.py#emit_strict_evidence`：复用 `collect_evidence.py` CLI，组装 `--strict` 参数经注入命令执行器调用。
- 新增 `ch9_boundary_runner.py#run_boundary`：判定 + 证据附着。
- 信号词表由轻量版常量提升为带权重的有序元组，歧义判定显式化；不引入任何框架。

## Testing Decisions

- 好测试只断言外部行为：`BoundaryVerdict` 字段与证据 argv 列表，不测私有辅助。
- 覆盖 runtime/artifact/ambiguous/no_signal 四路径 + 证据 strict 成功/失败 + dict shim。
- 覆盖率用 `scripts/verify_asc_b6_coverage.py` 复用 `measure_coverage.measure()`，目标 ≥90%。

## Out of Scope

- 不实现 Sidecar 运行时拦截本体（属 attack-infra B2）。
- 不改动 Ch8 G1-G14 投毒判据、既有 trad/attack-infra 判据。
- 不新增攻击载荷、不引入 PyRIT 或任何 AI 框架作攻击用途。

## Further Notes

- 事实见 `docs/research/attack-supply-chain-ch9-b6-hardening-canonical.md`（B6-1..B6-5、P-1..P-4、R-1、D-1）。
- 上游轻量版事实 `attack-supply-chain-ch9-canonical.md` 保留，本轮只升级实现质量与转交规则。
