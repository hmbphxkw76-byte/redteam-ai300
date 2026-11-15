# 阶段 11 门禁记录 — `pr-push-review`

- 交付物：PR 正文 `docs/operations/verify-evidence-pr-body.md`（2953/3000 字节）、双提交（`43c770a` 实现 + 两次 main 合并）、双轴审查报告
- 内部次序：`pre-push-review`（阶段 10 报告 + 修复）→ `pr`（正文四节 + 纳管四项）→ 推送（**阻断**）

| 编号 | 检查项 | 依据 | 实测结果（命令 + 摘要） | 判定 | 不符合项 | 修正要求 | 复验 | 结论 |
|---|---|---|---|---|---|---|---|---|
| B1 | 技能解剖 | §4.2 | `validate_skill.py` → PASS（16 技能） | 符合 | — | — | — | PASS |
| B2 | 术语 | §1.3 | `check_glossary.py` → PASS（50 术语） | 符合 | — | — | — | PASS |
| B3 | 语法与测试 | B3 | `py_compile` 4 文件 OK；`tests.test_verify_evidence + tests.test_report_exam` → `Ran 69 tests, OK` | 符合 | — | — | — | PASS |
| B4 | 证据契约 | §6.1 | S1-only 豁免 + 29 用例 | 符合 | — | — | — | PASS |
| B5 | 证据与 flag | §6.2 | 双通道/访问证明判据 + 用例；无 mock 放行 | 符合 | — | — | — | PASS |
| B6 | CI 门禁 | CI-CD §3 | 覆盖率 92.3% ≥80；预算 PASS；14 锚点齐 | 符合 | — | — | — | PASS |
| B7 | PyRIT | ADR-0004 | 零 `pyrit` 依赖 | 符合 | — | — | — | PASS |
| B8 | 可追溯性 | B8 | PR 正文 `Closes #204-#212`；跟进 #225 | 符合 | — | — | — | PASS |
| 验收① | 双轴发现数与最严重项 | §3.11 | Spec 硬违规 8（访问证明误判）/ Standards 硬违规 5（冲突残留），均已清零 | 符合 | — | — | — | PASS |
| 验收② | 门禁结果行 `passed` | §3.11 | 全绿（见 B1–B6） | 符合 | — | — | — | PASS |
| 验收③ | PR 四节 + 四项纳管字段 | §3.11 | 变更摘要 / Evidence / Merge Danger 齐；组件类型·能力域 D11·P0·通用·端到端演示齐 | 符合 | — | — | — | PASS |
| 验收④ | 推送记录含通道与结果 | §3.11 | `git push origin feat/verify-evidence`（SSH）→ pre-push 钩子阻断；未改试 HTTPS（同锁） | **不符合** | 共享检出锁阻断：`GLOSSARY.md` / `scripts/measure_coverage.py` / `.github/workflows/ci.yml` 被 ≥3 个 worktree 并发改动（`_attack-infra_wt`、`_attack-rag-conform_wt`、`_sc_tools_wt`、主工作树） | 在单一 worktree 串行合入共享文件（取并集）后再推；或等其余任务收口后 rebase 重推 | `python scripts/checkout_lock.py --check` | 仍阻断 |
| 验收⑤ | CI S1–S4 全绿 | §3.11 | 未创建 PR，CI 未触发 | 未判定 | 依赖推送 | 同上 | — | — |
| 验收⑥ | 3 轮收敛 | §3.11 | 推送 2 轮均被锁阻断，未触发「未收敛」清单 | — | — | — | — | — |

**结论：BLOCKED** —— 停在本阶段。技术交付物与本地产物链已全绿；唯一阻塞是**三层隔离的共享检出锁**（协议要求，非代码缺陷）。

## 阻塞解除后的剩余动作（下一步）

1. `git merge origin/main`（若远端再前进）→ `python scripts/checkout_lock.py --check` 归零。
2. `git push origin feat/verify-evidence` → `gh pr create --body-file docs/operations/verify-evidence-pr-body.md --base main`。
3. 跟踪 CI S1–S4 全绿后合并；确认 #204–#212 关联关闭、#225 保留。
