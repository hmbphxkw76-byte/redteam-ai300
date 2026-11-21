# A2A Ch4 对齐全量主线：阶段 11 推送前评审

> 父工单 #292；规格 v2 #294；阶段 10 报告 `a2a-ch4-mainline-code-review.md`。

## 1. 固定点与 diff 模式

- 远端基线：`origin/main` = `831df49bcde90820434f13743ca127d647986556`。
- diff 模式：工作树相对基线，非空；4 个修改文件 + 6 个新增文件。
- 本任务未修改共享文件（`GLOSSARY.md`、`ci.yml`、`collect_evidence.py`、契约清单、token/coverage 脚本）。
- `checkout_lock.py --check` → PASS。

## 2. 推送前双轴评审（第 1 轮收敛）

| 轴 | 发现数（硬违规） | 开放判断项 | 最严重项 |
|---|---|---|---|
| Standards | 0 | 0 | 无；阶段 10 的 6 项已修正并复跑 |
| Spec / Consistency | 0 | 0 | 无；阶段 10 的 6 项已修正并复跑 |

确认批次：1 轮（阶段 10 修复批次）；未超过 3 轮上限。

## 3. 门禁结果行

`passed`：`check_token_budget --check`、`validate_skill`、`check_glossary`、`check_contract_manifest --check`、`check_contract_consumers --check`、`check_tools_compile`、`check_evidence_contract`、`checkout_lock --check`、markdownlint 0 issues、`unittest` 897 OK (skipped=3)、coverage 89.3%。

## 4. PR 要素

- Summary：树形展示三技能 + recon-05 探针 + 测试/文档。
- Evidence：改前=缺 C1–C20 逐项对照与 Agent Card 自动探针；改后=三 SKILL.md 对照清单 + 5 tests/93 tests/897 tests 全绿。
- Merge Danger：单向门=step_id/七字段契约/共享契约不回退；双向门=attack-multi-agent 与 recon-ai 的证据引用互认；影响半径=3 SKILL.md + 1 probes.py + 1 test + 6 文档。
- 能力域：D10 / D2 / D4；优先级：P1 / P0 / P1；计分单元：通用 / 通用 / AI向量机。
- 端到端演示：`recon-05` 读 Agent Card → recon-05/07 证据片段 → threat-model 模式与边界 → attack-multi-agent 六类攻击面与字段判据 → report-exam 复用。

**阶段 11 推送前结论：PASS**。按 SSH → HTTPS 各试一次推送。实际经 SSH 一次成功推送；PR #311 已创建。首次 CI 因 PR 正文缺「契约变更清单」段失败，已补段并通过本地 `--pr-body` 门禁；本次推送触发的复跑用于确认远端 CI 同步。
