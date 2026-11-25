## 工程规格定稿 (v2) — recon-ai Ch9 云暴露面（C1）

> 取代 v1（#364 正文保留）；6 US → 7 布尔 AC。

| ID | 布尔验收条件 | 判据 | Ch9 |
|---|---|---|---|
| AC-01 | 实例含 PublicIp 且 SG ingress CIDR=0.0.0.0/0 → EXPOSED_NO_AUTH 并记录端口 | 单测 | L29-30 |
| AC-02 | 仅内网 IP 或仅私网 CIDR → ABSENT | 单测 | — |
| AC-03 | 版本端点返回 version 字符串 → 记录版本 + CVE 查询建议（不含载荷） | 单测 | L32 |
| AC-04 | 无版本数据 → ABSENT，不虚构版本 | 单测 | — |
| AC-05 | 只读判定：模块不发起网络/命令调用 | grep + 依赖注入核对 | R-4 |
| AC-06 | 不新增 step_id；既有 probes/inventory/runner 零判据 diff | git diff | R-4 |
| AC-07 | 每步三件套字段（命令/输出/截图钩子）可生成 | 单测 | §6.1 |

测试决策：只测外部行为；覆盖命中/缺项/边界；覆盖率≥80%。
门禁：unittest + glossary + validate + budget + 双轴 review。
风险闸：R1 — CVE 具体编号不在一手源逐条核实，只给查询建议；不阻断。

### v1→v2 差异
1. US→7 布尔 AC；2. AC-05/06 锁定只读与零 step_id 变更；3. 明确 R1；4. 补三件套 AC-07。
