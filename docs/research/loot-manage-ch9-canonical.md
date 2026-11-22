# loot-manage Ch9 扩展事实索引

> v1.0 · 已核实 · 上游 `skills/loot-manage/SKILL.md` · 课程源 Ch9 L15-28、L53
> 框架组合取矩阵 ⑧（结构化凭据库 + 许可 AI；无攻击框架）。

## 0. 结论
Ch9 五服务凭据狩猎与 K8s 身份链均产出凭据，需即时登记；既有登记簿 8 列已足够，
缺的是「指纹化登记」助手——把 attack-infra ch9 产出的 `前缀/长度/位置` 指纹
写入 `凭据` 行而不落明文。

## 1. 已核实（一手）
| # | 事实 | 来源 |
|---|---|---|
| L-1 | 登记簿 8 列含类型/内容/来源主机/证据片段路径/状态/双通道 | `skills/loot-manage/SKILL.md` 执行体 |
| L-2 | 凭据类型状态集合 {有效,失效}；编号 L-<n> | `tools/loot_manage/registry.py` COLUMNS/TYPES |
| L-3 | 明文凭据禁止入片段；只记指纹 | `docs/research/attack-infra-ch9-canonical.md` P-2 |
| L-4 | 框架组合无攻击框架 | 矩阵 ⑧ |

## 2. 映射
| 步骤 | 成功判据 | 失败分支 |
|---|---|---|
| loot-05 云凭据指纹登记 | 输入含前缀/长度/位置 → 追加凭据行，content 无明文 | 缺位置 → ABSENT |

## 3. 门禁（阶段 1）
| 编号 | 变更项 | 判定 | 复验命令 | 结论 |
|---|---|---|---|---|
| B7 | L-4 零 AI 框架 | 符合 | `grep -nE "pyrit\.orchestrator\|Orchestrator" tools/loot_manage/` → 无 | PASS |
| B8 | L-1..L-4 带来源 | 符合 | `grep -c "registry.py\|SKILL.md\|矩阵" docs/research/loot-manage-ch9-canonical.md` | PASS |
| B9 | 矩阵 ⑧ | 符合 | `sed -n '91,96p' docs/research/osai-skill-framework-matrix.md` | PASS |
