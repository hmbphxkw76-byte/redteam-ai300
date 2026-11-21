# A2A Ch4 对齐全量主线：阶段 10 双轴代码审查

> 对应父工单 #292、规格 v2 #294。固定基线：`git merge-base origin/main HEAD` = `831df49`；diff 非空（4 modified + 5 new files）。两轴并行审查、不合并、不重排。

## 1. Standards 轴

| 项 | 结果 |
|---|---|
| 硬违规 | 0 |
| 判断项 | 6 |
| 最严重项 | `judge_agent` 的 Agent Card 判据优先于既有 request_id 判据，与设计记录声明的优先级不一致 |

| 位置 | 分类 | 处置 |
|---|---|---|
| `tools/recon_ai/probes.py` card 分支位置 | 判断项 | 已重排：先判 `/agents`、`/health`、request_id 信号，再判 Agent Card；与设计 §3.1 一致 |
| `tests/recon_ai/test_recon_ai_a2a.py` 缺共存用例 | 判断项 | 已补 `test_request_id_signal_precedes_card`；现 5 tests OK |
| `docs/operations/a2a-ch4-mainline-tdd.md` 证据契约测试数 27 | 判断项 | 已改为 3（该模块实际 3 tests） |
| `attack-multi-agent` 与 `recon-ai` 重复 Agent Card/OpenAPI 命令 | 判断项 | attack-multi-agent 改为按资产 ID / `loot/recon-05-agent-sys.md` 引用，命令定义只在 recon-ai |
| 实现记录字节数混用 CRLF 原始值与 checker 口径 | 判断项 | 改为 LF 归一化口径 5916/11957/11743，并注明原始值另计 |
| 设计记录 `_agent_card` 返回类型写为 `dict | None` | 判断项 | 改为 `(dict, ProbeResult)` 或 `(None, None)` |

**Standards 结论：0 硬违规，6 判断项全部修正。**

## 2. Spec / Consistency 轴

| 项 | 结果 |
|---|---|
| 硬违规 | 0 |
| 判断项 | 6 |
| 最严重项 | recon-05 的 Agent Card jq 未含 `protocolVersion`/`securitySchemes`、OpenAPI 未含 `$ref`、注册端点未含注销端点，C7–C10 覆盖弱于规格 |

| 位置 / AC | 分类 | 处置 |
|---|---|---|
| AC-RC-2 / C7–C10 | 判断项 | recon-ai SKILL.md 补入 `protocolVersion`/`securitySchemes`/`$ref`/`/agents/deregister`；合法 workflow 基线明确交叉引用 a2a-01 |
| AC-TM-1 / C3 | 判断项 | threat-model 补入“智能体间未验证输出/工具/系统”三层信任边界，并在质量门同步 |
| VG-V3 | 判断项 | 实现记录新增 Listing 13/16/22/28/47/55 → 原始字段判据的人工核实清单 |
| V4 | 判断项 | recon-ai 功能边界新增 garak 偏离条目，指向设计记录 |
| AC-ALL-1 字节口径 | 判断项 | 已统一为 checker 口径 |
| 阶段 9 checkout_lock 记录 | 判断项 | 复跑 PASS，TDD 记录更新为“外部并发已消解” |

**Spec 结论：0 硬违规，6 判断项全部修正。**

## 3. 复跑结果（修正后）

| 检查 | 结果 |
|---|---|
| `python scripts/check_token_budget.py --check` | PASS |
| `python scripts/validate_skill.py` | PASS（16 技能） |
| `python scripts/check_glossary.py` | PASS（57 个废弃术语） |
| contract manifest / consumers / tools_compile / evidence_contract | PASS |
| `python scripts/checkout_lock.py --check` | PASS |
| `npx markdownlint-cli2 "skills/**/*.md" "docs/**/*.md" "GLOSSARY.md"` | 0 issues（186 文件） |
| `python -m unittest discover -s tests -t . -q` | Ran 897 tests，OK (skipped=3) |
| `python scripts/measure_coverage.py --target all --min 80` | 9811/10986 = 89.3% |
| recon-05 证据契约 | 5 tests OK；既有 recon group 93 tests OK |
| attack-multi-agent 证据契约 | 3 tests OK；8 步契约未变 |

## 4. 阶段 10 G0（B1–B9 全项）

B1 技能解剖 PASS；B2 术语一致 PASS；B3 语法/测试 PASS；B4 证据契约 PASS；B5 证据与 flag 双通道语义保留 PASS；B6 CI 门禁 PASS；B7 PyRIT 版本与对象图 PASS；B8 可追溯 PASS；B9 框架选型合规（含 V4 显式偏离）PASS。

**阶段 10 G0：PASS**。进入阶段 11 `pr-push-review`。
