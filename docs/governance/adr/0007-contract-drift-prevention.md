# ADR-0007：共享工具契约漂移防控（契约单一事实源 / 变更清单门禁 / 落后基线提示）

- 状态：已接受
- 日期：2026-11-16
- 决策者：hmbphxkw76-byte

## 背景

共享工具 `tools/collect_evidence.py` 的契约被全部 P0/P1 技能消费。跨技能回归的覆盖集是「契约变更时已合入 `main` 的消费者」这一时点快照，对晚于变更合入的技能无覆盖、无提示。

实证链（2026-11-15）：

1. PR #250（`e9f8bdd`）把 F3 截图状态由二值改为三态 `shot_status`（已提供 / 待补录 / 缺失）。
2. PR #230 的 `attack-infra` 晚于变更合入，仍断言旧值「已提供」，合并后导致 `main` CI S2 失败。
3. PR #254（`1489503`）事后补救，把断言改为「待补录」。

根因三层：R1 回归覆盖集是时点快照、消费者全集未登记；R2 后合入技能的工作树基线落后于变更 commit；R3 契约无机器可读变更清单，`checkout_lock.py` 共享文件清单不含共享工具、也不检测基线落后。

## 决策

固化「契约漂移防控」为可执行机制，而非文档约定。措施落点见 `docs/operations/contract-drift-prevention.md`。

### ① 契约单一事实源

`docs/contracts/collect_evidence.contract.md` 唯一登记 CLI 标志、`build_fragment` / `report` 键、清单字段、片段节标题与退出码，附 `contract_version` 与 CHANGELOG（逐条记 commit / PR / 兼容性）。改共享工具语义须同步清单并递增版本。对齐 `AGENTS.md` C1。

### ② 消费者登记表 + 依赖断言

`docs/contracts/consumers.md` 登记每个消费者及其依赖的契约元素；`scripts/check_contract_consumers.py` 断言「全部依赖 ⊆ 契约清单」，漂移即阻断。消费者全集从隐性变显性、可枚举、可回归。

### ③ 契约 PR 变更清单门禁（S2/S5）

`scripts/check_contract_manifest.py` 在 PR 触及契约文件时要求正文含「契约变更清单」段（变更元素 / before→after / 受影响消费者 / 兼容性判定），并点名全部未合入消费者。未声明即阻断。

### ④ 落后基线提示（扩展三层隔离 ③）

`scripts/checkout_lock.py` 共享文件清单加入共享工具与契约清单；取契约 CHANGELOG 的变更 commit，若某 worktree 基线落后于变更 commit 且消费共享工具，输出明确契约冲突提示并阻断。已合并的僵尸 worktree（HEAD 已是 `origin/main` 祖先）不判落后。

### ⑤ 并发判定按各 worktree 自身基线复判

并发共享文件改动改按 `merge-base HEAD origin/main` 比较，而非统一 `origin/main`，消除「陈旧 worktree 因 main 前进而被误判为本地改动」的假阳性。

### ⑥ 下游契约定点

`tests/test_contract_drift.py` 用 golden 片段锁定 `report_exam.index.parse_fragment` 依赖的节标题结构，共享工具改动任一标题即令测试变红。

## 后果

### 正面

- 拦截点从「main 合并后」前移到「契约 PR 开启时 / 落后基线推送前」，消除事后补救 PR。
- 契约与消费者全集机器可读，可被新会话 / 新成员自动继承，不依赖个人记忆。
- 修复三层隔离 ③ 的陈旧 worktree 误报，检出锁判定更精确。

### 代价 / 权衡

- 新增 2 份契约文档 + 2 个校验脚本 + 1 组夹具，契约变更时须多步同步；这是刻意的——用少量同步成本换取跨技能漂移的事前拦截。
- ④ 的检测依赖 `origin/main` 上的契约清单，本 ADR 合入前为引导期 no-op；合入后对既有落后 worktree 生效。
- ⑥ 的 golden 片段在共享工具合法改标题时须同步更新，属预期维护成本。

## 关联

- ADR-0006（三层隔离 ③ 共享检出锁）：本 ADR 扩展其共享文件清单与判定逻辑。
- ADR-0005（Token 预算纪律）：契约文档纳入产物预算与规范契约锚点（CONTRACTS 14→17）。
- 落地实施与验证命令：`docs/operations/contract-drift-prevention.md` §6。
- 触发实证：PR #250 / #230 / #254。
