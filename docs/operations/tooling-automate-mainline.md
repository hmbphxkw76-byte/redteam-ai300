# tooling-automate 主线门禁索引

> 依据 `docs/operations/skill-mainline-workflow.md` §2；逐阶段记录见 per-stage 文件（每个 ≤2KB）。B1–B8 定义见 §2.1，此处不重复（C1）。

## 隔离基线（ADR-0006）

- worktree `D:/_tooling-automate_wt` · 分支 `feat/tooling-automate` · 基线 `origin/main` = `20ce2eb`。
- 复用核验：`git status --porcelain` 空、`git rev-list --count origin/main..feat/tooling-automate` = 0、`HEAD` == `origin/main`；等价 `mainline_worktree.py create` 结果。
- 本地主工作树 `main` 落后 `origin/main` 1 提交；全部落地仅在 worktree 内进行，不改共享主工作树。
- 目标 issue 仓库 `hmbphxkw76-byte/redteam-ai300`（`gh repo view` 已确认）。

| 阶段 | 名称 | 结论 | 门禁记录 |
|---|---|---|---|
| 1 | research | PASS（B7/B8，0 不符合项） | `docs/research/tooling-automate-canonical.md` §门禁记录 |
| 2 | to-spec① v1 | PASS（B1/B2/B8，C4 修正后 0 不符合项） | `docs/operations/tooling-automate-gate-stage2.md` |
| 3 | to-spec② v2 | PASS（B1/B2/B6/B7/B8，0 不符合项） | `docs/operations/tooling-automate-gate-stage3.md` |
| 4 | to-tickets | PASS（B2/B8，0 不符合项） | `docs/operations/tooling-automate-gate-stage4.md` |
| 5 | triage | PASS（B8，0 不符合项） | `docs/operations/tooling-automate-gate-stage5.md` |
| 6 | codebase-design | PASS（B2/B7/B8，0 不符合项） | `docs/operations/tooling-automate-gate-stage6.md` |
| 7 | domain-modeling | PASS（B1/B2/B8，0 不符合项） | `docs/operations/tooling-automate-gate-stage7.md` |
| 8 | implement-spec | PASS（B1/B2/B3/B4/B5/B7/B8，0 不符合项） | `docs/operations/tooling-automate-gate-stage8.md` |
| 9 | tdd | PASS（B3/B4/B6/B8，0 不符合项） | `docs/operations/tooling-automate-gate-stage9.md` |

- 阶段 1 交付物：`docs/research/tooling-automate-canonical.md`（16 条条款映射、VG-1…VG-4 核实闸、已排除清单）。
- 阶段 2 交付物：v1 = `docs/specs/tooling-automate-spec-v1.md`（7993B，七节 / 30 US）；规格 issue = #240（`ready-for-agent`）；seam 结论 = 1 处（用户 2026-11-15 确认）。
- 阶段 3 交付物：v2 = `docs/specs/tooling-automate-spec-v2.md`（7793B，20 条布尔 AC / CI 映射 / v1→v2 差异 / VG-1…VG-4 核实闸）；已追加至 issue #240 评论「工程规格定稿 (v2)」，v1 保留全文不动。
- 阶段 4 交付物：父工单 #242 + 子工单 #243(A manifest) #244(B runner) #245(C reuse) #246(D summary) #247(E evidence-contract) #248(F test/coverage)；覆盖矩阵与依赖边见 #242 正文，API 核验阻塞边正确。
- 阶段 5 交付物：7 张工单全标 `ready-for-agent`，每张含 范围/验收/约束/验证 四段 brief；无人工独占项（纯自动化可落地）。
- 阶段 6 交付物：`docs/operations/tooling-automate-design.md`（单包 `tools/tooling_automate/`，5 模块，S-1 唯一 seam，零 pyrit，FakeRunner 假后端策略）。
- 阶段 7 交付物：GLOSSARY 新增 2 术语（任务清单/编排层，16489/16500，未抬上限）+ 术语映射表（gate-stage7）；无新增 ADR。
- 阶段 8 交付物：`tools/tooling_automate/` 7 模块（S-1 唯一 seam、injectable runner、零第三方）+ 6 测试文件（27 例全绿）+ `measure_coverage.py` 注册目标（覆盖 89.6%）。
- 阶段 9 交付物：`test_tooling_tdd_contract.py` 6 例（红→绿→重构留痕，AC-08 补注入点）；全量 650 OK；覆盖 91.8%；AC→测试 20/20。
- 门禁摘要：阶段 1 / 2 / 3 / 4 / 5 / 6 / 7 已按 T5 补登于 issue #240 评论区。
