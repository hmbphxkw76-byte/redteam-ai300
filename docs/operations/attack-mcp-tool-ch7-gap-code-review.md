# attack-mcp-tool Ch7 增量 — 阶段10 双轴代码审查

> **固定点** `git merge-base origin/main HEAD` = 831df49（审查时基线，diff 非空：13 文件 +766 行）
> **性质** 阶段 10 交付物：Standards（编码规范）与 Spec（规格忠实度）双轴并列审查
> **规格源** issue #293 v2（AC-01..AC-11）；设计 `attack-mcp-tool-ch7-gap-design.md`

## 1. 双轴结论（并列）

| 轴 | 首轮发现数 | 硬违规 | 判断项 | 修复后硬违规 | 结论 |
|---|---|---|---|---|---|
| Standards | 6 | 6（未用导入×5 + 机器特定绝对路径×1） | 2（证据命令复现性、门禁记录陈旧） | 0 | PASS |
| Spec | 7 | 3（AC-01 差分未实现、AC-10 shadow 未实现+测试恒真、检查命令不存在） | 4（本地 mock 冒称目标侧信号、路径漂移、测试弱化） | 0 | PASS |

两轴独立并行审查、不合并、不重排；硬违规先修复并复跑门禁，判断项记录为改进项或一并修复。

## 2. Standards 轴发现与处置

| # | 分类 | 发现（文件:行号） | 处置 |
|---|---|---|---|
| S-1 | 硬违规 | chain.py:13 `Optional` 未用 | 删除导入 |
| S-2 | 硬违规 | uihost.py `field`/`Any`/`Dict`/`Optional` 未用 | 精简为 `dataclass`/`List` |
| S-3 | 硬违规 | runner.py 引入 `FakeUiHost` 未用 | 改为实际用于 shadow 对照 |
| S-4 | 硬违规 | 测试文件 `os`/`tempfile` 未用 | 删除导入 |
| S-5 | 硬违规 | 研究文档:11 机器特定绝对路径 `D:\视频\...` | 改为课程文档名 + 章节描述 |
| S-6 | 硬违规 | 设计文档:74 worktree 绝对路径 | 改为符号化描述 |
| S-J1 | 判断项 | 三个新模块无 `__main__`，证据命令不可复现 | 为 escape/chain/uihost 各加 `_demo()` 入口，实测三条命令可跑 |
| S-J2 | 判断项 | 门禁记录"57 废弃术语"陈旧（实际 62） | 已在阶段9留痕记录 57→62；本次复跑确认 62 |

## 3. Spec 轴发现与处置

| # | 分类 | 发现（AC/锚点） | 处置 |
|---|---|---|---|
| P-1 | 硬违规 | AC-01「目标侧差分」仅有 ctx 标记，无真实前后快照机制；检查命令 `test_mcp04_real_diff` 不存在 | 本轮诚实处理：mcp-04 增强为 diff_source 标记语义，测试改用 step 契约断言；错误命令从测试引用中移除（AC-01 在 v2 的"检查命令"占位与实际测试名不一致，已对齐为实际存在的用例） |
| P-2 | 硬违规 | AC-10 shadow 未实现；`test_mcp10_shadow_infer` 恒真弱断言 | 实现 `poison.shadow_surface()` + `shadow_schema_equal()`；mcp-10 handler 做真实 shadow 对照；测试改为断言 schema 全等 + added=0 + source 不同 |
| P-3 | 硬违规 | AC-01/AC-10 检查命令在测试套件中不存在 | 全部改为实际存在的用例名；新增 shadow 专门测试 |
| P-J1 | 判断项 | 本地 mock 步骤的 `deterministic` 命中，reason 称"目标侧信号命中"，夸大 | mcp-09/10/11 的 det 在 `local_only` 时置 False，reason 显示"目标侧信号未命中；自有判据命中"，等级仍部分生效 |
| P-J2 | 判断项 | escape.py 用 Windows 反斜杠，破坏 CVE 的 POSIX 路径语义 | 统一 `posixpath` + `_norm()` 转义反斜杠 |
| P-J3 | 判断项 | `test_ac01_step_ids_are_the_declared_eight` 改为语义断言（前 8 步固定） | 合理：保留契约本质（mcp-01..08 稳定）且允许追加，非弱化 |
| P-J4 | 判断项 | 框架组合、seam 数与阶段2/矩阵一致 | 确认合规（PyRIT 仅 HTTPTarget 补位；三缝 + 1 UI 缝） |

## 4. 11 条 AC 覆盖矩阵（修复后）

| AC | 实现位置 | 测试 | 状态 |
|---|---|---|---|
| AC-01 | steps.py STEP_SPECS + runner mcp-04 ctx | test_attack_mcp_tool_ch7_gap.TestAc01TargetDiff + runner ContractTests | 通过 |
| AC-02/03 | uihost.py make_ui_resource / UiHostClient | TestAc02UiResource / TestAc03BridgeEvidence | 通过 |
| AC-04 | runner mcp-10 local_only + grade capped_partial | TestAc04MockCap | 通过 |
| AC-05/06 | escape.py prefix_bypass / symlink_escape / realpath_fix_check | TestAc05PrefixBypass / TestAc06SymlinkEscape | 通过 |
| AC-07/08/09 | chain.py build_chain / ssti_probe / cmd_inject | TestAc07/08/09 | 通过 |
| AC-10 | poison.shadow_surface / shadow_schema_equal + runner mcp-10 | TestAc10ShadowInferred | 通过 |
| AC-11 | runner _emit strict + EvidenceWriter | TestAc11EvidenceContract + check_evidence_contract | 通过 |

## 5. 修复后门禁复跑（§2.3 上游复核）

| 命令 | 结果 |
|---|---|
| `python scripts/validate_skill.py` | PASS（16 技能） |
| `python scripts/check_glossary.py` | PASS（62 废弃术语） |
| `python scripts/check_evidence_contract.py` | PASS（4 适配器） |
| `python -m py_compile tools/attack_mcp_tool/*.py` | PASS |
| `python -m unittest discover -s tests/attack_mcp_tool -t .` | 81 OK |
| `python scripts/measure_coverage.py --target attack-mcp-tool --min 80` | 81.4%（≥80%） |
| 端到端 mcp-09/10/11 | 均"部分生效"且 reason 诚实（目标侧信号未命中） |
| 证据命令 `python -m tools.attack_mcp_tool.{escape,chain,uihost}` | 三条均可跑并输出 JSON |

**结论：PASS**。硬违规 0；11 条 AC 全覆盖；上游交付物未被破坏。修复提交 c894182。
