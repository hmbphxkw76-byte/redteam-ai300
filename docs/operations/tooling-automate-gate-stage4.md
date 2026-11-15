# 阶段 4 门禁记录 — `to-tickets`（垂直切片拆解）

- 交付物：父工单 #242 + 子工单 #243(A) #244(B) #245(C) #246(D) #247(E) #248(F)
- 变更项：v2 的 20 条 AC 拆成 6 子工单 + 覆盖矩阵 + 依赖边

| 编号 | 检查项 | 依据 | 实测结果 | 判定 | 结论 |
|---|---|---|---|---|---|
| B2 | 术语一致 | §1.3 | 各工单用规范术语；`check_glossary` 仓库级 PASS | 符合 | PASS |
| B8 | 可追溯 | B8 | #242↔#240 互链；#243…248 `Part of #242` | 符合 | PASS |
| 验收① | 切片完整 | §3.2 | A manifest/B runner/C reuse/D summary + E evidence + F test | 符合 | PASS |
| 验收② | 依赖边 | §3.2 | E blocked-by 245；F blocked-by 243,244,245,246（API 核验 1/4） | 符合 | PASS |
| 验收③ | 验证命令 | §3.2 | 每张工单含 `unittest`/`grep` 验证命令覆盖其 AC | 符合 | PASS |
| 验收④ | 覆盖矩阵 | §3.2 | #242 正文 AC→工单矩阵 20 条全覆盖 | 符合 | PASS |
| C4 | 产物体积 | C4 | `--artifact gate-record` 1129/2000 | 符合 | PASS |

**结论：PASS**（不符合项 0），进入阶段 5（`triage`）。
