# CI/CD 流水线设计规范

> **版本** v1.1 · **状态** 生效（2026-11-14 T07/T08 工具链与契约修订）· **性质** 《治理规范》第八章的可执行落地
> **依据** [GOVERNANCE.md](../governance/GOVERNANCE.md) · [GLOSSARY.md](../../GLOSSARY.md) · [ADR-0003](../governance/adr/0003-ci-cd-github-actions.md)

---

## 1. 目的与范围

本规范定义「agent + skill」开发全生命周期的 CI/CD 流水线，将《治理规范》的校验与合规机制（§4.2 技能工程规范、§8.1 技能验收、§8.2 合规检查清单）固化为**自动化、可复现、可审计**的质量门禁。

**适用范围**：本仓库内一切变更——技能（`skills/**`）、智能体代码、文档（`docs/**`、`GLOSSARY.md`）与流水线自身（`.github/**`）。

**核心原则**：
1. **门禁前置**：问题在提交/PR 阶段暴露的成本远低于发布后，故静态检查与测试前置于构建与部署。
2. **校验与治理同源**：每项检查必须对应一条可追溯的治理条款（引用 `条款 X.Y`）。
3. **本地与 CI 一致**：校验脚本本地可运行，CI 判定与本地判定相同（ADR-0003）。
4. **未过即阻断**：任何阶段失败即阻断后续阶段，不带病推进（阶段门禁）。

---

## 2. 流水线总览

| 阶段 | 名称 | 触发条件 | 对应治理条款 | 阻断对象 |
|---|---|---|---|---|
| S0 | 提交门禁 | 本地 commit / push feature | §4.2 | commit / push |
| S1 | 代码检查 | PR 开启/同步、push feature | §4.2、§1.3、§8.2-8 | PR 合并 |
| S2 | 自动化测试 | 依赖 S1 通过 | §8.1 | PR 合并 |
| S3 | 构建 | 合并到 `main` | §6.4（产物） | 发布 |
| S4 | 集成合规 | 合并到 `main`（依赖 S3） | §8.2 全量 | 发布 |
| S5 | 部署/发布 | 打 `v*` tag | §6.4、§9 | 发布 |

```
commit ──S0──▶ PR ──S1──▶ S2 ──▶ merge ──S3──▶ S4 ──▶ tag ──S5──▶ Release
              (门禁)  (检查)  (测试)        (构建) (集成)       (发布)
```

**关键约束**：S0–S2 运行于未合并分支，失败只阻断、不回滚（直接修复重推）；S3–S5 运行于已合并/已发布产物，失败需回滚或撤销。

> **T06 补充**：`.github/workflows/report-toolchain.yml` 为独立工具链冒烟 workflow（不占 S1–S5 阶段号），随 PR/push 触发；固定 pandoc 3.14 / typst 0.15.1 / p7zip-full，真实构建并机读断言 AC-12、PDF 目录条目、无密码、单 PDF 成员、≤100MB。产物仅写 `RUNNER_TEMP`，不上传、不提交。

---

## 3. 各阶段规范

### S0 提交门禁（Commit Gate）

- **触发条件**：每次本地 `git commit`（可选 pre-commit）；每次向远程推送 feature 分支；每次开启/同步 PR。
- **执行步骤**：
  1. 秘密扫描（gitleaks），禁止凭据/密钥入库。
  2. commit message 规范校验（Conventional Commits：`type(scope): subject`）。
  3. 文件大小与二进制检查（拒绝 >1MB 的非必要二进制，参考 §6.4 报告归档上限 100MB）。
  4. 本地记忆：`--local`（`.workbuddy/` 被 gitignore，CI 不可见，按 C7 蒸馏）。
  5. 仓库外产物：`--artifact <KIND> <PATH>`，写 PR 正文 / issue 摘要 / brief 前判 C4 上限。
- **成功标准**：全部通过，允许进入 PR。
- **失败标准**：任一检查非零退出。
- **回滚/修复**：未合并，无回滚；本地修正后 `git commit --amend` 或新增 commit 重推。

### S1 代码检查（Static Checks）

- **触发条件**：PR `opened`/`synchronize`；向任意分支 `push`（`ci.yml` 的 `push.branches: ['**']`，feature 分支同样受门禁约束；S3/S4 仍由 `github.ref == 'refs/heads/main'` 限定）。
- **执行步骤**（对应 `ci.yml` 的 `checks` job）：
  1. Markdown 规范——作用于 `docs/**`、`GLOSSARY.md`、`skills/**`；`globs` 逐行分隔（逗号分隔会假绿）。官方模板按 `.markdownlint-cli2.jsonc` 的 `ignores` 豁免，理由见配置注释（§8.3）。
  2. 技能解剖校验（`scripts/validate_skill.py`）——强制 §4.2 五要素、优先级/能力域/计分单元枚举、目录与 `name` 一致。
  3. 术语一致性（`scripts/check_glossary.py`）——技能不得使用 `GLOSSARY.md` 标注 `_Avoid_` 的废弃术语（§1.3、§8.2-8）。
  4. Token 预算 / 规范契约（`check_token_budget.py --check`）——判 `BUDGETS` 字节上限、冷备清单、重复块，及 `CONTRACTS` 的 14 项锚点（C1–C8、§2.4、ADR-0005、CI 接线、跨 IDE 指针）是否齐全；任一缺失或超限即阻断。依据 `AGENTS.md` C4、主流程 §2.4、ADR-0005。
  5. PR 正文 C4 产物上限（仅 `pull_request` 事件）——把 `github.event.pull_request.body` 落盘后执行 `--artifact pr-body`，超 3KB 阻断。
  6. 共享工具语法编译（`python -m py_compile tools/collect_evidence.py`）——证据收集工具引入后强制语法门禁。
- **成功标准**：六项均 0 错误。
- **失败标准**：任一脚本非零退出，CI 报告精确到文件与缺失字段。
- **回滚/修复**：未合并，无回滚；依检查器输出修正后重推。

### S2 自动化测试（Automated Tests）

- **触发条件**：S1 通过后（`needs: checks`）。
- **执行步骤**：
  1. 运行 `tests/`（标准库 `unittest`，零外部依赖），至少覆盖：校验器自测（用临时夹具构造「合规/不合规」技能，断言校验器正确放行与拦截）；证据收集工具自测（`tests/test_collect_evidence.py`，用假数据断言产出片段含三件套「命令 + 输出 + 截图」，并校验 `--strict` 与废弃术语预警）。
  2. 业务代码引入后，登记其依赖清单与测试框架（如 `requirements.txt` + `pytest`）至本阶段。
- **成功标准**：全部用例通过；存在业务代码时，行覆盖率须 ≥80%（门槛写入 workflow，缺省 80）。
- **失败标准**：任一用例失败。
- **回滚/修复**：未合并，无回滚；修复被测代码或校验器后重推。

### S3 构建（Build）

- **触发条件**：合并到 `main` 后（`push` 到 `main`）。
- **执行步骤**：
  1. 打包技能与治理产物为可分发归档（`dist/redteam-ai300-skills.tgz`）。
  2. 生成归档校验和（`dist/*.sha256`）。
- **成功标准**：产物生成且校验和一致、可解包。
- **失败标准**：构建脚本报错或产物缺失。
- **回滚/修复**：已合并；修复构建脚本走 hotfix 分支；紧急回滚 `git revert <引入问题的 merge>` 后重新构建。

### S4 集成合规（Integration）

- **触发条件**：`main` 分支 S3 通过后（`needs: build`，`if: github.ref == 'refs/heads/main'`）。
- **执行步骤**：全量治理合规套件——
  1. `validate_skill.py` 全量（含「name 是否登记于 §4.4」的登记核对）。
  2. `check_glossary.py` 全量。
  3. 治理文档结构校验（`GOVERNANCE.md` 条款编号唯一、`GLOSSARY.md` 术语定义完整、ADR 编号连续）。
  4. `check_token_budget.py --check` 复核（产物上限 + 14 项规范契约锚点），防止合并后语料或契约回退。
- **成功标准**：全量合规，0 错误。
- **失败标准**：任一检查失败。
- **回滚/修复**：已合并；`git revert` 回滚该 merge；修复后以新 PR 重新进入 S1–S4。

### S5 部署/发布（Release）

- **触发条件**：推送 `v*` tag（语义化版本）。
- **执行步骤**：
  1. 版本标签合法性校验（`vMAJOR.MINOR.PATCH`）。
  2. 运行 S1/S4 校验与测试（发布前最终门禁）。
  3. 打包产物并创建 GitHub Release（`generate_release_notes: true`）。
- **成功标准**：Release 成功发布，产物可下载。
- **失败标准**：校验/测试失败或发布失败。
- **回滚/修复**：发布失败时删除错误 Release 与 tag（属不可逆操作，须二次确认）；修复后重新打新 tag。已发布的正式版本不覆盖，按新版本号递增。

---

## 4. 新增 agent/skill 组件纳管机制

新增任何 agent/skill 组件，**必须**走以下纳管流程，确保每次迭代遵循统一规范：

### 4.1 目录与命名约定
1. 技能置于 `skills/<name>/SKILL.md`，`<name>` 为 kebab-case，须与 `GOVERNANCE.md` §4.4 的 `name` 一致；智能体代码置于 `agents/<name>/`。
2. 技能 front-matter 必须含 §4.2 定义的七字段：`name`、`priority`、`domain`、`scoring_unit`、`trigger`、`input`、`output`。

### 4.2 纳管步骤（逐条强制）
1. **登记**：在 `GOVERNANCE.md` §4.4 技能清单表新增一行（含优先级、对齐能力域、目标计分单元）；若为全新能力域，先在 §3.1 定义能力域。
2. **实现**：按 §4.2 五要素解剖编写 `SKILL.md`，正文必须含「执行体 / 质量门 / 校验标准 / 失败与豁免」四小节。
3. **提 PR**：使用 `.github/PULL_REQUEST_TEMPLATE.md`，强制填写「对齐能力域、优先级、目标计分单元、端到端演示」四项；缺失字段由 CI 阻断。
4. **过门禁**：CI 自动执行 S1（解剖 + 枚举 + 术语）与 S2（测试）；`validate_skill.py` 会核对 `name` 是否已登记于 §4.4。
5. **合并**：合并到 `main` 后自动纳入 S4 全量集成合规。
6. **发布**：纳入 `v*` 打 tag 的产物打包与 Release。

### 4.3 纳管验收标准
- 任一新组件合并前，必须同时满足 S1 与 S2 全绿，且 PR 描述四项字段齐全。
- 未登记于 §4.4 的 `name` 触发 `validate_skill.py` 告警；若 PR 未同步更新 §4.4，评审应拒绝合并。

---

## 5. 回滚与修复总则

1. **未合并阶段（S0–S2）**：不涉及回滚，遵循「修复后重推」。
2. **已合并阶段（S3–S4）**：优先 `git revert` 回滚引入问题的 commit；修复以 hotfix 分支走完整 S1–S4。
3. **已发布阶段（S5）**：不覆盖已发布版本；错误版本撤销 tag/Release（二次确认），正确修复以递增版本号重新发布。
4. **禁止**：直接向 `main` 推送绕过门禁；用 `--no-verify` 跳过钩子；静默偏离（须记录理由，见 §8.3）。

---

## 6. 目录约定

```
.github/
  workflows/ci.yml              # S0–S4：检查、测试、构建、集成
  workflows/release.yml         # S5：发布
  PULL_REQUEST_TEMPLATE.md      # 纳管 PR 模板
scripts/
  validate_skill.py             # 技能解剖与登记校验（S1/S4）
  check_glossary.py             # 术语一致性校验（S1/S4）
  check_token_budget.py         # Token 预算 / 产物上限 / 冷备清单（S1）
tools/
  collect_evidence.py           # 共享证据收集工具（P0，通用，服务 P0 攻击技能）
tests/
  test_validators.py            # 校验器自测（S2，标准库 unittest）
.markdownlint-cli2.jsonc        # Markdown 规范配置
skills/<name>/SKILL.md          # 技能包（纳管对象）
agents/<name>/                  # 智能体代码（纳管对象）
```

---

## 7. 附则

1. 本规范与 `GOVERNANCE.md` 冲突时，以官方考试事实（S1/S2/S3）与《治理规范》「必须」条款为准。
2. 流水线变更走与业务代码相同的 S1–S4 流程；`.github/**` 与 `scripts/**` 的变更亦受门禁约束。
3. 本规范修订须更新版本号，并以 Git diff 为唯一变更记录。
