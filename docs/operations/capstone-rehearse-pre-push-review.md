# capstone-rehearse 推送前双轴评审（阶段 11 · pre-push-review）

> **固定点**：`git fetch origin main` 后 `git merge-base origin/main HEAD` = `20ce2eb`；diff 模式 = **branch commits**（工作树干净）；命令 `git diff 20ce2eb...HEAD`；commit 列表 `git log origin/main..HEAD --oneline`；diff 非空（30 文件，全为 `A`、0 个 `M`/`D`）。
> **规格源**：`docs/specs/capstone-rehearse-spec-v2.md`（活版本，25 条 AC）+ issue #231（GitHub tracker 可用，v2 全文在评论）+ `skills/capstone-rehearse/SKILL.md`（行为唯一来源）。
> **标准源（本项目实际）**：`GOVERNANCE.md` §4.2/§6/§8.2、`docs/standards/CI-CD.md` S0–S4、`AGENTS.md` C1–C8、`GLOSSARY.md`、`.markdownlint-cli2.jsonc`、`.github/workflows/ci.yml`。**显式偏离声明（§8.3）**：技能文档列举的 `CODING_STANDARDS.md` / `CONTRIBUTING.md` / `gate_suite.py` / `sync_all.py` 本仓库均不存在，门禁套件按项目实际脚本执行；技能要求的检查名 `audit (3.11)` / `audit (3.13)` 对应本仓库 CI 的 `checks`(S1) / `tests`(S2)。

## 1. 双轴并列报告（不合并、不重排）

| 轴 | 发现数 | 硬违规 | 判断项 | 最严重项 |
|---|---|---|---|---|
| **Standards** | 0 | 0 | 0 | 无 |
| **Spec** | 7 | 1 | 6 | AC-25 / `spec-v1.md` 被阶段 10 的 MD012 修复改写，与 issue #231 正文逐字节互链断裂，且 v2「v1 不改写」与 AC-25 字节判据失真 |

Standards 轴确认：30 个变更全为新增、未触碰 4 个共享文件；三件套判据已委托 `registry.fragment_pieces`；3/3 commits 符合 Conventional Commits；`validate_skill` / `check_glossary` / `check_token_budget --check` / markdownlint(141 文件) / `unittest discover`(652 OK) / `measure_coverage --target all`(91.2%) 全部通过。

Spec 轴确认：seam 仍为「2 新 + 复用 1」数量未增；四件产出、VG-1…VG-6、演练标注、`-real` 过滤忠实；未见「未演练写成已通过 / 建议伪装实测 / 超时隐瞒 / 真实考试利用」。

## 2. 逐条分类（Spec 轴 7 项）

| # | 位置 | 描述 | 分类 | 处置 |
|---|---|---|---|---|
| 1 | `AC-25 / spec-v1.md:90` | 删尾部空行致 7982B→7981B，与 #231 正文不再逐字节一致；`test_ac25` 未实现哈希判据；`gate-stage10` §2.3 记「未变」失真 | 硬违规 | **批次 1 修复** |
| 2 | `gate-stage10.md:19` | §2.3 口径与历史 7982B 矛盾 | 判断项 | 随批次 1 修正为「§8.3 格式修正」 |
| 3 | `AC-03 / walk.py:40` | `test_ac03` 只计 `iter_fragments()`，未锁死 `fragment_pieces` 被调用；`_chain` 的技能名子串匹配使默认演练片段路径恒为断点 | 判断项 | 改进项（记录，不阻断） |
| 4 | `AC-18/19` | 三态仅测 1、2，缺 0=PASS；AC-18 未断言退出码相同 | 判断项 | 改进项 |
| 5 | `AC-04/14/24` | 锚点字符串退化、空断言、六类 `--artifact` 仅实跑一类 | 判断项 | 改进项（门禁已实跑六类） |
| 6 | `cli.py:66` | `--closed-gates` 可纯声明关闭核实闸，与「未演练≠已通过」有张力 | 判断项 | 改进项（报告免责声明承接） |
| 7 | `Closes #233` | 父工单为 `ready-for-human`（含人工最终放行），合并自动关闭会绕过人工放行 | 判断项 | **采纳**：PR 改 `Closes #234–#239`，`Refs #231, #233`，父工单保持 OPEN |

## 3. 人工确认批次（用户 2026-11-15 确认）

| 批次 | 内容 | 确认结果 |
|---|---|---|
| 1 | 同步 issue #231 正文为 7981B 版本恢复逐字节互链；按 §8.3 显式声明纯格式修正（七节/32 US/语义不变）；`gate-stage10` §2.3 口径修正；v2 正文不改（C4 余量 16B），以 issue 评论发布「v2 补充声明」 | **已确认并执行** |
| 2 | 按 ADR-0006 钩子例外通道推送：并集为空已逐 hunk 核对（本 PR 30 文件全 `A`，未触碰共享文件），`git push --no-verify` 绕过 pre-push 锁但**不绕过任何 CI 门禁**；SSH 失败则 HTTPS，各试一次即停 | **已确认** |

写入 hunks 严格限于：issue #231 正文/评论、`docs/operations/capstone-rehearse-gate-stage10.md` 两行；不触碰共享文件与 v2 正文。复评第 2 轮：**硬违规 0**，1 轮内收敛（上限 3 轮）。

## 4. 门禁结果行（第 2 轮复跑）

```text
S1 validate_skill                             passed
S1 check_glossary                             passed
S1 check_token_budget --check                 passed
S1 markdownlint(141 files)                    passed
S2 py_compile                                 passed
C4 spec-v1 / spec-v2 / gate-stage10           passed
SUMMARY passed=8 failed=0 total=8
python -m unittest discover -s tests          Ran 652 tests OK (skipped=2)
python scripts/measure_coverage.py --target all --min 80   总计 91.2% PASS
```

`checkout_lock.py --check` 返回 1（其他 3 个 worktree 的共享文件改动），本 worktree 不在 offender 列表；按批次 2 例外通道处置，记录见 §5。

## 5. 收口记录（推送 / PR / CI 实测）

- **推送通道**：`git push --no-verify origin feat/capstone-rehearse`（SSH）**一次成功**；按双通道约定「各试一次即停」，未使用 `origin-https`。例外依据 ADR-0006 与用户确认批次 2；并集为空（本 PR 30 文件全 `A`、0 `M`/`D`），未触碰共享文件；CI S1/S2 未被绕过。
- **PR**：#251 `feat(capstone-rehearse): 考前演练走查主线落地（D11 / P2 / 通用验收）`，`feat/capstone-rehearse → main`，`MERGEABLE`。
- **CI**：PR 阶段 `静态检查 (S1)` = pass、`AC-12 真实 PDF / .7z 冒烟` = pass、`自动化测试 (S2)` 由 PR #251 把关；S3 `build` / S4 `integration` 由 `ci.yml` 在 main 合并后触发，实测结果见 issue #233 收口摘要与工作记忆（阶段 11 门禁记录 §验⑤）。
- **关联**：`Closes #234, #235, #236, #237, #238, #239`；`Refs #231, #233`（#233 保持 OPEN 待人工最终放行）。
- **收敛**：pre-push Spec 轴硬违规 1（v1 与 #231 逐字节互链断裂）已按批次 1 清零并复评；判断项 6 记录为改进项；1 轮内收敛（上限 3 轮）。

## 6. PR 要素交接

- **标题**：`feat(capstone-rehearse): 考前演练走查主线落地（D11 / P2 / 通用验收）`
- **正文**：`docs/operations/capstone-rehearse-pr-body.md`（四节 + 四项纳管字段，C4 `pr-body` ≤3KB）
- **必需检查名（本仓库实际）**：`checks`（S1）、`tests`（S2）；合并后 main 触发 `build`（S3）、`integration`（S4）
- **关联**：`Closes #234, #235, #236, #237, #238, #239` · `Refs #231, #233`（#233 保持 OPEN 待人工放行）
