## 工程规格定稿 (v2) — attack-supply-chain Ch9 边界（B6）

> 取代 v1（#361 正文保留）；4 US → 5 布尔 AC。

| ID | 布尔验收条件 | 判据 | Ch9 |
|---|---|---|---|
| AC-01 | 仅运行时信号（sidecar/共享卷/exec）→ owner=attack-infra | 单测 | L54-55 |
| AC-02 | 仅工件信号（model/artifact/minio/registry）→ owner=attack-supply-chain | 单测 | L53 |
| AC-03 | 双向信号 → owner=本技能且 confidence=ambiguous | 单测 | S-1/S-2 |
| AC-04 | 无信号 → owner 为空、reason=no_signal | 单测 | — |
| AC-05 | 零网络、零框架、零投毒载荷改动；既有 Ch8 模块零 diff | grep + git diff | S-4 |

测试决策：只测 classify 外部行为；四路径全绿；覆盖率≥80%。
门禁：unittest + glossary + validate + budget + 双轴 review。
风险闸：R1 — 信号词表为教学级启发式，人工复核 ambiguous；不阻断。

### v1→v2 差异
1. US→5 布尔 AC；2. 补门禁映射；3. AC-05 锁定既有模块零 diff；4. 明确 R1。
