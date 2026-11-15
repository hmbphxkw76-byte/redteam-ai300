# 阶段 11 门禁记录 — `pr-push-review`

- 交付物：PR 正文 `docs/operations/verify-evidence-pr-body.md`（2972/3000 字节）、PR #227（已合并）、双轴审查报告、SKILL 覆盖矩阵
- 内部次序：`pre-push-review`（阶段 10 报告 + 修复）→ `pr`（正文四节 + 纳管四项）→ 推送（常规通道被锁阻断，按文档例外通道完成）→ CI → 合并

| 编号 | 检查项 | 依据 | 实测结果（命令 + 摘要） | 判定 | 不符合项 | 修正要求 | 复验 | 结论 |
|---|---|---|---|---|---|---|---|---|
| B1 | 技能解剖 | §4.2 | `validate_skill.py` → PASS（16 技能） | 符合 | — | — | — | PASS |
| B2 | 术语 | §1.3 | `check_glossary.py` → PASS（50 术语） | 符合 | — | — | — | PASS |
| B3 | 语法与测试 | B3 | `py_compile` OK；全量 `Ran 578 tests, OK (skipped=2)`；覆盖率 92.1% | 符合 | — | — | — | PASS |
| B4 | 证据契约 | §6.1 | S1-only 豁免 + 32 用例 | 符合 | — | — | — | PASS |
| B5 | 证据与 flag | §6.2 | 双通道/访问证明判据 + 用例；无 mock 放行 | 符合 | — | — | — | PASS |
| B6 | CI 门禁 | CI-CD §3 | 覆盖率 92.1% ≥80；预算 PASS；14 锚点齐；markdownlint 0 issue（20 文件） | 符合 | — | — | — | PASS |
| B7 | PyRIT | ADR-0004 | 零 `pyrit` 依赖 | 符合 | — | — | — | PASS |
| B8 | 可追溯性 | B8 | PR 正文 `Closes #204-#212`；跟进 #225 | 符合 | — | — | — | PASS |
| 验收① | 双轴发现数与最严重项 | §3.11 | Spec 硬违规 8（访问证明误判）/ Standards 硬违规 5（冲突残留），均已清零 | 符合 | — | — | — | PASS |
| 验收② | 门禁结果行 `passed` | §3.11 | 全绿（见 B1–B6） | 符合 | — | — | — | PASS |
| 验收③ | PR 四节 + 四项纳管字段 | §3.11 | 变更摘要 / Evidence / Merge Danger 齐；组件类型·能力域 D11·P0·通用·端到端演示齐 | 符合 | — | — | — | PASS |
| 验收④ | 推送记录含通道与结果 | §3.11 | 常规通道两次 `git push origin feat/verify-evidence` 均被 pre-push 钩子阻断（锁：4 个 worktree 并发改 GLOSSARY / measure_coverage / ci.yml）；按钩子载明的例外改用 `git push --no-verify`，SSH 通道成功：`c47f07e..d2f36b8`，新建 `feat/verify-evidence` | 符合 | 锁未归零（他人未提交在制改动所致） | 已逐文件核对并集：我的 `GLOSSARY.md` 为 +12/-0 纯增量，`measure_coverage.py` 为 +14/-3 且 attack-rag 条目全部保留（`rg_mods`/`rg_tests` 各 2 处、choices 双条目共存） | `git diff origin/main --numstat` + `grep -c rg_mods` | PASS |
| 验收⑤ | CI S1–S4 全绿 | §3.11 | PR #227：S1 pass（首轮因 spec-v1 MD036 失败，已改为真标题并本地 markdownlint 0 issue）、S2 pass、AC-12 冒烟 pass；合并后 main CI `success`（S3/S4 随 main 运行） | 符合 | 首轮 S1 失败 | 修正 4 处伪标题 + 回收 84 字节保持 ≤8KB | `gh pr checks 227` | PASS |
| 验收⑥ | 3 轮收敛 | §3.11 | 推送 3 轮（2 次阻断 + 1 次例外通道）、CI 2 轮（S1 失败→修复），均在 3 轮内收敛 | 符合 | — | — | — | PASS |

**结论：PASS** —— PR #227 已合并至 `main`，CI S1/S2 + 冒烟全绿，合并后 main CI `success`；#204–#212 全部自动关闭，跟进项保留 #225（判断项 J-1/J-2）。

## 留痕

- 例外通道依据：pre-push 钩子自身载明的 `--no-verify` 例外，且已按「逐 hunk 确认并集无重叠」核对（见验收④）。
- 未做的事：未替其他 worktree 提交其未提交的共享文件改动（不在本任务授权范围）。
