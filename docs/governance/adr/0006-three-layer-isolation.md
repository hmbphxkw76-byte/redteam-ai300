# ADR-0006：三层隔离机制（分支隔离 / 串行合并 / 共享检出锁）

- 状态：已接受
- 日期：2026-11-15
- 决策者：hmbphxkw76-byte

## 背景

本项目为**多 worktree 并行沙箱**：多个主线任务（`/主线 [技能名]`）会同时在不同
worktree 上开发，且它们共同修改一批「共享文件」——`scripts/check_token_budget.py`、
`scripts/measure_coverage.py`、`.github/workflows/ci.yml`、`GLOSSARY.md`。

在 `decoy-detect`（PR #191）落地过程中，暴露出三类结构性风险：

1. **共享工作树污染**：并行任务在同一个工作树里改动，导致 `measure_coverage.py`
   被并发写入了未提交的 `attack_multi_agent_targets`，`--target all` 本地无法运行。
2. **合并顺序冲突**：`check_token_budget.py` 的 `GLOSSARY.md` 预算，一个 PR 设 10200、
   并行技能设 12000，合并时产生内容冲突；且「取 max」仍不够，须按「合并后实际内容
   加余量」重算（最终 13000）。
3. **并发合并无门禁**：main 级无串行/合并队列约束，两个 PR 各自绿、合并后才冲突。

上述问题此前靠**人工纪律**规避，不可被新会话/新成员可靠继承。

## 决策

固化「三层隔离」为**可执行机制**，而非文档约定：

### ① 分支隔离（任务间）

每个主线任务在**独立 worktree + 独立 `feat/*` 分支**上落地，与并行任务物理隔离。

- 实现：`scripts/mainline_worktree.py`
  - `create <skill>` → `git worktree add --detach origin/main` 建干净基线 + `checkout -b feat/<skill>`
  - `list` → 列出全部 worktree / 分支 / HEAD
  - `remove <path> [--force]` → 清理
- 原则：禁止在共享主工作树直接落地主线任务；缺省 worktree 路径 `D:/_<skill>_wt`。

### ② 串行合并（main 级）

main 上的合并与门禁串行化，从机制上消除并发合并冲突。

- 实现：`.github/workflows/ci.yml`
  - `concurrency.group: ci-main-serial-${{ github.ref }}` + `cancel-in-progress: true`
    → 同一 ref 的并发运行互相取消，S3/S4 产物（`dist/`）串行写入。
  - `merge_group: types: [checks_requested]` → 合并队列中的 PR 先按**预合并结果**跑门禁，
    失败不进入 main，避免「各自绿、合并后冲突/超限」。

### ③ 共享检出锁（工作目录级）

提交/推送前检测「同一共享文件被多个 worktree 并发修改」，冲突即阻断。

- 实现：`scripts/checkout_lock.py`
  - 默认共享文件清单（四类）：`check_token_budget.py` / `measure_coverage.py` /
    `ci.yml` / `GLOSSARY.md`
  - 判定：对每个共享文件，比较各 worktree 相对 `origin/main` 的本地改动；同一文件
    被 ≥2 个 worktree 改动即判并发冲突，输出并集提示、返回非 0。
- 配套：`pre-push` hook 在 `git push` 前调用 `checkout_lock.py --check`，非 0 则阻断。

## 后果

### 正面

- 并行任务互相隔离，共享文件冲突从「事后解冲突」前移到「事前阻断」。
- main 合并串行化 + 合并队列，门禁在预合并态验证，不再出现合并后失败。
- 机制可被任意新会话/新成员自动继承，不依赖个人记忆。

### 代价 / 权衡

- `checkout_lock` 是**保守检测**：只要 ≥2 个 worktree 改了同一共享文件即阻断，即使
  改动其实可自动合并。这是刻意的——宁可阻断让人工确认并集，也不靠 main 合并赌运气。
- 共享文件清单目前硬编码为四项；若未来新增共享脚本需扩展，应改为可配置（预留
  `--shared` 参数已支持覆盖）。
- `concurrency.cancel-in-progress` 会取消排队中的同 ref 运行；对 S1/S2（快、幂等）
  无影响，对 S3/S4（写 `dist/`）是必要的串行保护。

## 关联

- ADR-0003（CI-CD GitHub Actions）、ADR-0005（Token 预算纪律）。
- 触发本 ADR 的实证：`docs/operations/decoy-detect-code-review.md`、
  PR #191 合并时的 `check_token_budget.py` / `measure_coverage.py` 冲突。
