## 工程规格定稿 (v2) — foothold-traditional Ch9 入口扩展

> 取代 v1（issue #355 正文保留）；差异：User Stories → 8 条布尔 AC + 门禁映射 + 核实闸。

| ID | 布尔验收条件 | 检查命令/判据 | Ch9 |
|---|---|---|---|
| AC-01 | SSRF 响应含 3 个 AWS 凭据键名时，产出 3 条指纹且 outcome=EXPOSED_NO_AUTH | 单测断言 | L1 |
| AC-02 | 响应无凭据键名时 outcome=ABSENT(reason=none_found) | 单测 | — |
| AC-03 | 任一凭据明文不出现在 verdict.output | 单测断言 | P-2 |
| AC-04 | 凭据验证端点返回身份 JSON 时 outcome=EXPLOITED | 单测 | L1 GetCallerIdentity |
| AC-05 | sudo -l 输出含 `(root) NOPASSWD:` 包装脚本时，outcome=EXPOSED_NO_AUTH 且记录脚本路径 | 单测 | L56-57 |
| AC-06 | sudo -l 无 NOPASSWD 条目时 ABSENT | 单测 | — |
| AC-07 | 每步证据三件套齐全（命令/输出/截图钩子） | 证据契约测试 | §6.1 |
| AC-08 | 五值结论 reason 属既有枚举集合 | 单测 | AC-19 类同 |

测试决策：只测外部行为；FakeCommand 离线；覆盖成功/缺项/拒绝三路径；覆盖率≥80%。
门禁映射：AC-01..06,08 单测(S2)；AC-07 证据契约(S2)；全量 unittest + glossary + validate + budget。
风险闸：R1 — SSRF 载荷生成不属本技能（由 recon/attack-infra 提供），只在有响应文本时判定。
核实闸不阻断。

### v1→v2 差异
1. 6 条 User Stories 收敛为 8 条布尔 AC；2. 补门禁映射；3. 明确 R1 核实闸；4. AC-08 对齐五值 reason 枚举。
