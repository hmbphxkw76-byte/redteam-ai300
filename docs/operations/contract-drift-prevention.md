# 共享工具契约漂移防控方案（Contract Drift Prevention）

> **版本** v1.1 · **状态** 已采纳（2026-11-15）· 落地后登记为 ADR-0007，扩展 ADR-0006 三层隔离
> **针对缺陷**：共享工具契约（`tools/collect_evidence.py`）变更时，跨技能回归仅覆盖「变更时已合入 main 的消费者」，晚于变更合入的 skill（实证：`attack-infra`）无法被覆盖，导致契约漂移。
> **实证证据**：PR #250（F3 契约变更）→ PR #230（attack-infra 后合入，携旧契约断言）→ PR #254（main CI S2 失败后补救）。
> **依据**：[GOVERNANCE.md](../governance/GOVERNANCE.md) §6/§8.2 · [CI-CD.md](../standards/CI-CD.md) S1–S4 · [ADR-0006](../governance/adr/0006-three-layer-isolation.md) · `AGENTS.md` C1（单一事实源）

---

## 1. 问题根因

### 1.1 一句话结论

跨技能回归是**时点快照**而非**契约全量**：它只校验「该 commit 已合入 main 的消费者」，而对「晚于变更合入、但基线落后于变更」的消费者（如 `attack-infra`）既无覆盖、也无提示，漂移只能等合并后由 main CI 事后暴露。

### 1.2 实证时间线（本仓库真实发生）

| 序号 | 事件 | commit / PR | 契约语义 |
|---|---|---|---|
| 1 | F3 契约变更：`shot_cmd`-only 场景截图状态「已提供」→「待补录」 | `e9f8bdd` / PR #250（`e6a9f24`） | `collect_evidence.py` 新增 `shot_status` 三态 |
| 2 | 变更时跨技能回归：全量 628 例 | 仅覆盖当时已合入 main 的消费者 | **不含 attack-infra**（尚未合入） |
| 3 | attack-infra 后合入，携旧契约断言 `\| 截图 \| 是 \| 已提供 \|` | PR #230（`e528801`） | 工作树从变更前基线建，编码旧语义 |
| 4 | main CI S2 失败 → 补救 PR | PR #254（`962b1d6`，`1489503`） | 断言改为 `\| 截图 \| 是 \| 待补录` |

### 1.3 三层根因（对应三条结构性缺口）

- **R1 回归覆盖集是「时点快照」**：PR #250 时的回归对象是 `unittest discover -s tests` 在 `origin/main @ e6a9f24` 的全部用例。attack-infra 的测试当时不在 `main`，故 F3 语义变更对其不可见。契约的「消费者全集」未被显式登记，导致「谁该被回归」无从枚举。
- **R2 后合入技能的工作树基线落后于契约变更**：attack-infra 由 `mainline_worktree.py create` 从**变更前的** `origin/main` 建干净基线（`D:/_attack-infra_wt`），其实现与测试自然编码旧契约。合并后与 F3 新语义冲突，漂移在「合并到 main」之后才由 CI S2 暴露——成本最高、最晚。
- **R3 契约缺「机器可读变更清单」与「落后基线检测」**：契约元素（CLI 标志、`build_fragment`/`report` 键、`build_manifest_record` 字段、`report_exam.index.parse_fragment` 依赖的片段标题、退出码语义）无单一事实源；`checkout_lock.py` 的 `DEFAULT_SHARED_FILES` 硬编码四项（`check_token_budget.py` / `measure_coverage.py` / `ci.yml` / `GLOSSARY.md`），**不含** `collect_evidence.py`，也不检测「工作树基线是否落后于某个契约变更 commit」。

---

## 2. 改进措施

> 每项标注：**触发时机**（何时生效）、**责任方**（谁执行）、**生效范围**（作用对象）。
> M1–M2 为契约治理基础设施，M3 为用户要求②的落地，M2 为用户要求①的落地。

### M1 契约单一事实源（契约清单 + 版本化）【基础设施】

- **内容**：新建 `docs/contracts/collect_evidence.contract.md`，机器可读地登记契约元素：
  - CLI 标志集（`--step/--cmd/--out/--screenshot/--shot-cmd/--shot-kind/--strict/--manifest/--flag-panel/--flag-shot` 等及其语义）；
  - `build_fragment` 参数与 `report` 键（`complete/missing/required_status/optional_status/shot_status/flag_status/hashes` 等）；
  - `build_manifest_record` 字段（`pieces/flag_dual/screenshot_sha256` 等）；
  - 片段各节标题（`report_exam.index.parse_fragment` 依赖，如 `#### 截图（访问证明）`、`#### flag 取证（双通道一致）` 及其 fenced 原值块）；
  - 退出码语义（0/1/2）。
  - 附 `contract_version`（如 `v3`）与 CHANGELOG（逐条记录变更 commit、before→after、兼容性判定）。
- **依据**：对齐 `AGENTS.md` C1——契约只存一份，消费者与报告器只引 `路径#锚点`，不转抄。
- **触发时机**：每次 `collect_evidence.py` 语义改动时同步更新清单与 `contract_version`。
- **责任方**：改动共享工具的会话。
- **生效范围**：全仓库所有消费者、报告器、CI 校验器。

### M2 契约变更 PR 显式列出契约变更清单（用户要求①）【硬门禁】

- **内容**：凡 PR 触及 `tools/collect_evidence.py` 或 `docs/contracts/collect_evidence.contract.md`，PR 正文必须含「契约变更清单」段，至少四项：
  1. 变更元素清单（增 / 删 / 改名 / 语义变，逐条）；
  2. before → after（如 `shot_cmd`-only 截图状态 `已提供` → `待补录`）；
  3. 受影响消费者：**已合入**（可枚举）+ **未合入 backlog**（如 `attack-infra`、`tooling-automate` 等，须逐项点名）；
  4. 兼容性判定（向后兼容 / 破坏性；破坏性须给出迁移断言）。
- **硬门禁**：新校验器（或扩展 `check_token_budget.py`）在 S1 判定「契约 PR 缺清单段」→ 阻断合并。
- **触发时机**：契约 PR `opened`/`synchronize`（CI S1）；并行会话在合并前可据此自查断言。
- **责任方**：契约变更 PR 作者（写清单）+ CI（强制校验）。
- **生效范围**：所有并行会话的合并前自查；任何「未点名受影响消费者」的契约变更均无法进入 main。

### M3 共享检出锁给出契约冲突提示（用户要求②）【硬门禁】

- **内容**：扩展 `scripts/checkout_lock.py`，三处改动：
  1. `DEFAULT_SHARED_FILES` 加入 `tools/collect_evidence.py` 与 `docs/contracts/collect_evidence.contract.md`（保留 `--shared` 可覆盖）；
  2. 新增「基线落后检测」：对每个 worktree 取 `git merge-base <wt HEAD> origin/main`，与契约清单 CHANGELOG 登记的「契约变更 commit 列表」比对；若基线落后于某个契约变更 commit，且该 worktree 消费共享工具（存在 `tools/<skill>/evidence.py`，或 `skills/<skill>/SKILL.md` 含 `collect_evidence.py` 引用），输出明确提示：
     `契约冲突提示：<wt> 基线落后于契约变更 commit <hash>（<变更摘要>，PR #N）。请按该 PR 契约变更清单自查并断言后再推送。`
  3. 修复陈旧 worktree 误报：判定基线改为按**各 worktree 的 `HEAD`**（`merge-base`），不再统一按 `origin/main` 比较（消除工作记忆已记录的误报）。
- **触发时机**：`git push` 前（`pre-push` hook 自动）+ 阶段 11 推送前显式 `--check`。
- **责任方**：落地该技能的并行会话（执行 `--check`）；本方案由工具作者扩展脚本。
- **生效范围**：所有 worktree；落后基线且消费共享工具者被阻断，其余并行任务不受影响。

### M4 契约消费者登记表 + CI 断言【硬门禁】

- **内容**：新建 `docs/contracts/consumers.md`，登记每个消费者：`技能名 → 消费入口文件 → 依赖的契约元素 → 合入状态（已合入 / 未合入 backlog）`。
  - CI S2 加断言：每个「已合入」消费者声明的依赖 ⊆ 当前契约清单；越界（引用不存在的标志/键/标题）即失败。
  - 「未合入」消费者的 PR 首次开启时，强制补登记并校验其依赖对当前契约。
- **触发时机**：CI S2（每次 PR）+ 未合入消费者首次 PR 开启时。
- **责任方**：各技能落地会话（登记）+ CI（断言）。
- **生效范围**：全仓库消费者；「消费者全集」从隐性变为显性、可枚举、可回归。

### M5 契约 PR 强制全量回归 + 未合入消费者预警【硬门禁】

- **内容**：CI 在「PR 触及契约文件」时，除全量 `unittest discover` 外：
  1. 输出「未合入消费者清单」（取自 M4 登记表 backlog 段）；
  2. 要求 PR 正文（M2 清单段）对每个未合入消费者显式声明影响与迁移断言；未声明 → S1 阻断。
- **触发时机**：契约 PR 的 CI S1/S2。
- **责任方**：CI + 契约变更 PR 作者。
- **生效范围**：把「无法被覆盖的消费者」从隐性缺口转为显性、可审计项。

### M6 下游解析契约定点（golden 测试）【回归护栏】

- **内容**：`report_exam.index.parse_fragment` 依赖片段标题与 fenced 原值块结构。新增 golden 片段 + 断言，锁定以下契约：`#### 截图（访问证明）`、`#### flag 取证（双通道一致）`（fenced 原值块）、证据校验表列（`| 截图 | 是 | … |`）。共享工具改动任一节标题即令测试变红。
- **触发时机**：CI S2（每次）。
- **责任方**：`report-exam` 维护者 + 共享工具改动者（改标题须同步 golden）。
- **生效范围**：`collect_evidence.py` ↔ `report_exam` 之间的下游契约，防止静默漂移。

### M7 主流程 / 子 agent 契约指针【提示性】

- **内容**：主线 workflow §5 与 triage brief 模板增加一行「契约指针」：`docs/contracts/collect_evidence.contract.md#<当前版本>` + 最近一次契约变更 PR 号。任何并行会话 / 子 agent 落地技能前先读指针，从当前契约起步。
- **触发时机**：每个主线任务的阶段 1（research）与阶段 5（triage brief）。
- **责任方**：主流程编排层 + triage 会话。
- **生效范围**：所有并行任务起步时的契约基线对齐（提示性，不阻断）。

---

## 3. 分步实施清单

> 优先级：P0（阻塞其他）→ P1（核心防线）→ P2（加固）。依赖列指前序任务编号。

| 步骤 | 内容 | 优先级 | 依赖 | 验收标准 |
|---|---|---|---|---|
| S1 | 建契约单一事实源 `docs/contracts/collect_evidence.contract.md`（元素清单 + `contract_version` + CHANGELOG） | P0 | 无 | 清单覆盖 CLI 标志 / `report` 键 / manifest 字段 / 片段标题 / 退出码；CHANGELOG 回填 F3 变更（`e9f8bdd`）为第一条 |
| S2 | 契约 PR 清单强制校验器（M2）：契约 PR 缺「契约变更清单」段即 S1 阻断 | P0 | S1 | 构造无清单契约 PR → S1 非 0；含清单 → 通过 |
| S3 | 扩展 `checkout_lock.py`：加共享文件、落后基线检测、契约冲突提示、按各 wt `HEAD` 复判（M3） | P1 | S1 | 构造「落后基线 + 消费共享工具」wt → `--check` 非 0 且输出含「契约冲突提示」与对应 PR 号；陈旧 wt 不误报 |
| S4 | 契约消费者登记表 `docs/contracts/consumers.md` + CI S2 断言（M4） | P1 | S1 | 已合入消费者声明依赖 ⊆ 契约清单；声明越界 → S2 失败 |
| S5 | 契约 PR 全量回归 + 未合入消费者预警（M5） | P2 | S4 | 契约 PR 未声明未合入消费者 → S1 阻断；声明后通过 |
| S6 | `report_exam` 片段解析 golden 测试（M6） | P2 | S1 | 改任一片段标题 → golden 变红；恢复 → 变绿 |
| S7 | 主流程 §5 与 triage brief 增加契约指针行（M7） | P2 | S1 | brief 模板含契约指针；新主线任务阶段 5 输出含指针 |

**执行顺序约束**：S1 → {S2, S3, S4} 可并行 → S5（依赖 S4）、S6（依赖 S1）、S7（依赖 S1）。S2/S3 落地后即可回填历史实证（见 §4）。

**并行任务兼容性要求**：新增校验不得误伤当前活跃 worktree（`feat/attack-infra`、`feat/capstone-rehearse`、`feat/attack-supply-chain-tools`、`feat/tooling-automate`、`feat/verify-evidence-*`、`feat/framework-docs-recovery`）。S3 必须按各 wt `HEAD` 复判，避免陈旧 wt 因「相对 origin/main 有改动」被误判为契约冲突。

---

## 4. 落地后验证契约漂移已被拦截

### 4.1 历史实证回放（最关键）

以已发生的 PR #250 → PR #230 → PR #254 序列为判据，在 S2+S3+S4 落地后重放：

| 回放点 | 旧行为（现状） | 期望新行为（拦截点） |
|---|---|---|
| PR #230（attack-infra）合并前 | 无提示，直接合并 → main CI S2 失败 | **S3**：`checkout_lock --check` 在 attack-infra 推送前输出「基线落后于 `e9f8bdd`（F3）」契约冲突提示，阻断推送 |
| PR #230 合并后 | 需补 PR #254 | **S4**：attack-infra 的消费者断言声明旧键/旧值 → S2 失败，PR 无法合并，无需事后补救 |
| 契约 PR #250 开启时 | 未点名未合入消费者 attack-infra | **S2**：PR 缺「契约变更清单」或未声明 attack-infra → S1 阻断 |

判定标准：上述任一「期望新行为」成立即证明漂移被**事前**拦截（拦截点从「main 合并后」前移到「契约 PR 开启时 / 落后基线推送前」）。

### 4.2 复现实验（repro harness）

1. 用 `mainline_worktree.py create <skill> --base <F3 变更前 commit>` 建一个落后基线 worktree；
2. 在其中写一个消费共享工具、断言旧契约语义的测试（模拟 attack-infra）；
3. 依次验证：S3 `--check` 报契约冲突提示；S4 消费者断言失败；S2 契约 PR 清单校验阻断无清单 PR。

### 4.3 反向验证（回归无害）

- 在新增校验下，跑通当前活跃 worktree 各自的 `checkout_lock --check` 与 CI S1/S2，确认无新增误报/误阻断；
- 确认「未改契约、未消费共享工具」的并行任务（如纯文档、纯 skill 分支）完全不受影响；
- `check_token_budget.py --check` 与 `check_glossary.py` 仍全绿（新增文件不破坏既有门禁）。

### 4.4 长期观测指标

- 契约 PR 中「未声明受影响消费者」的数量长期为 0；
- 自落地起，不再出现「后合入技能因契约漂移触发 main CI S2 失败」的补救 PR（此类 PR 计数归零）。

---

## 5. 附则

1. 本方案已采纳，落地见 §6「落地记录」；登记为 **ADR-0007**（扩展 ADR-0006 三层隔离的第③层），决策记录以 Git diff 为准。
2. 与 GOVERNANCE / CI-CD 冲突时，以官方考试事实与「必须」条款为准；偏离须按 GOVERNANCE §8.3 显式声明。
3. 契约清单新增元素须先腾预算、勿抬 `GLOSSARY.md` 上限（沿用既有纪律）；术语以 `GLOSSARY.md` 为唯一基准。

## 6. 落地记录（2026-11-15）

| 步骤 | 交付物 | 状态 |
|---|---|---|
| S1 | `docs/contracts/collect_evidence.contract.md`（契约单一事实源，`contract_version` v3 + CHANGELOG 回填 F3） | ✅ |
| S2+S5 | `scripts/check_contract_manifest.py`（`--check` 清单完整 + `--pr-body` 契约 PR 变更清单门禁） | ✅ |
| S4 | `docs/contracts/consumers.md` + `scripts/check_contract_consumers.py`（消费者依赖断言） | ✅ |
| S3 | `scripts/checkout_lock.py`（共享文件清单加契约文件 + 落后基线契约冲突提示 + 按各 wt `HEAD` 复判） | ✅ |
| S6 | `tests/test_contract_drift.py`（parse_fragment golden + 清单/消费者完整性） | ✅ |
| 接线 | `ci.yml` S1 增 3 步；`check_token_budget.py` CONTRACTS 增 3 锚点 | ✅ |
| S7 | `skill-mainline-workflow.md` §5 契约指针 + `05-triage.md` brief 契约指针 | ✅ |

**验证命令**（本地，与 CI 判定一致）：

```bash
python scripts/check_contract_manifest.py --check
python scripts/check_contract_consumers.py --check
python scripts/checkout_lock.py --check
python scripts/check_token_budget.py --check
python -m unittest discover -s tests -q
python -m py_compile scripts/checkout_lock.py scripts/check_contract_manifest.py scripts/check_contract_consumers.py
```
