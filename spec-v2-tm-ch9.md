## 工程规格定稿 (v2) — threat-model Ch9 身份链（C3）

> 取代 v1（#367 正文保留）；5 US → 6 布尔 AC。

| ID | 布尔验收条件 | 判据 | Ch9 |
|---|---|---|---|
| AC-01 | 给 N 个 IAM 角色 → 图含 N 节点与 N-1 条 assume-role 边 | 单测 | 图3 |
| AC-02 | 末端策略跨项目 → 图标记 `boundary_crossed=true` | 单测 | M-1 |
| AC-03 | 两身份分别具 secrets.read 与 pods.create → 可达路径存在 | 单测 | Table 2 |
| AC-04 | 缺任一能力 → 路径不可达并记录 gap | 单测 | M-2 |
| AC-05 | 零网络零框架；既有 threat-model 图/诱饵判据零 diff | grep + git diff | M-4 |
| AC-06 | 输出含 Ch9 锚点（图3/Table 2），可追溯 | 单测断言 | M-1/M-2 |

测试决策：只测外部行为；覆盖完整链/断链/互补/缺口四路径；覆盖率≥80%。
门禁：unittest + glossary + validate + budget + 双轴 review。
风险闸：R1 — 真实环境的角色名/权限从上游 attack-infra 观测注入，本模块不虚构；不阻断。

### v1→v2 差异
1. US→6 布尔 AC；2. AC-05 锁定既有图语义零 diff；3. AC-06 追溯锚点；4. 明确 R1。
