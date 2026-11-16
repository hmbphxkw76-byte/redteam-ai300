# tooling-automate — 一手源核实与对象映射（阶段 1 · research）

> 依据 `docs/operations/skill-mainline-workflow.md#31-阶段-1--research调研`；B1–B8 定义见 §2.1，此处不复述（AGENTS C1）。
> 基线：独立 worktree `D:/_tooling-automate_wt` · 分支 `feat/tooling-automate` · `origin/main` = `20ce2eb`。
> 一手源 = 本仓库源码 / 治理文件 / CI 配置 / `docs/research/pyrit-canonical-references.md`（已核实索引，按 C5 不重复检索）。

## 1. 事实基线

| 事实 | 一手源 |
|---|---|
| 本技能零 `pyrit` 依赖，不含攻击逻辑；`pyrit==1.1.0` 仅作全局版本锁定 | `skills/tooling-automate/SKILL.md#L13,L62`；`docs/research/pyrit-canonical-references.md#L9-11` |
| 对象图统一 `pyrit.executor.attack` 下 `*Attack` + `OpenAIChatTarget`；禁用 `pyrit.orchestrator`、`*Orchestrator`、`AzureOpenAIChatTarget` | `docs/research/pyrit-canonical-references.md#L9-11,L25-36` |
| CI 零外部运行时依赖，扩展 = 1 脚本 + 1 CI 步骤；本地与 CI 判定一致 | `docs/governance/adr/0003-ci-cd-github-actions.md#L8,L11-12` |
| C8 不可删减、stdlib-only 密闭 CI | `docs/governance/adr/0005-token-budget-discipline.md#L27-28,L42-44` |
| 三层隔离：分支 worktree / 串行合并 / 共享检出锁 | `docs/governance/adr/0006-three-layer-isolation.md#L28-57` |
| `ci.yml` 触发 `pull_request[main]`、`push['**']`、`merge_group[checks_requested]`；S1 `checks`、S2 `tests`、S3 `build`、S4 `集成合规`；S3/S4 仅 `refs/heads/main` | `.github/workflows/ci.yml#L4-14,L27,L64,L78,L96,L80,L98` |
| S0 提交门禁由 `.githooks/pre-push` 实现；S2 = `discover -q` + `--target all --min 80` | `docs/standards/CI-CD.md#L46`；`.github/workflows/ci.yml#L73-75,L109` |

**指针消歧（已核实）**：`SKILL.md#L7,L13,L39,L61` 的「§3 S2」按上下文指 `docs/standards/CI-CD.md#3-各阶段规范` 的 S2 自动化测试门禁，**不是** `docs/governance/GOVERNANCE.md#L75` 的 §3.1「能力域清单（S2）」。后续规格统一只引前者（C1 单一事实源）。

## 2. SKILL 条款 → 一手源映射

| SKILL 条款 | 一手源事实 | 位置 |
|---|---|---|
| §1.1 批量枚举/证据/校验 | 现有 CI 已把校验脚本化，可直接复用而非重写 | `.github/workflows/ci.yml#L41,L43,L45,L54` |
| §1.2 区分可脚本化 / 人工判读 | flag 双通道与访问证明需同屏截图，属人工判读；`--strict` 只判一致性不判真伪 | `docs/governance/GOVERNANCE.md#L186-188`；`tools/collect_evidence.py#L370-387` |
| §1.3 任务—脚本映射草案 | SKILL 自定产物，无既有源；本阶段 §3 给出初稿 | `skills/tooling-automate/SKILL.md#L23` |
| §2.1 以 `collect_evidence.py` 为证据收口 | CLI 必填 `--step` / `--cmd` / `--out`；`--out -` 输出 stdout；`--append` 追加；`--manifest` 写 JSONL | `tools/collect_evidence.py#L334-359,L418-448` |
| §2.1 三件套 / 五件套 | 三件套 = 确切命令 + 关键输出 + 截图；五件套 = 三件套 + AI 交互日志 + flag 双通道 | `tools/collect_evidence.py#L41,L43,L45,L316-323` |
| §2.1 `--strict` 语义 | 三件套不全或 flag 双通道不一致 → 退出 1；非 strict 缺失仍退出 0 仅告警 | `tools/collect_evidence.py#L370,L380,L387,L450-467` |
| §2.2 复用 `validate_skill.py` / `check_glossary.py` | 前者 `--skills-dir`/`--governance`；后者 `--glossary`/`--scan`；均无 `--check` | `scripts/validate_skill.py#L14,L103-110`；`scripts/check_glossary.py#L9,L73-79` |
| §2.3 markdown/表格结构化 | 落盘片段与 `loot-manage` 索引习惯一致，工具本身即产出 markdown 片段 | `tools/collect_evidence.py#L41-45` |
| §3.1 `<prefix>-01..0N` 命名空间 | `--step` 为必填参数，片段按 step 标识归档 | `tools/collect_evidence.py#L334-359` |
| §3.2 被 attack-* 与 `verify-evidence` 调用 | 固定流水线「必须边打边写」，`--strict` 为强制收口 | `docs/governance/GOVERNANCE.md#L141,L151` |
| §3.3 复用声明 / 新增 seam 理由 | 「零新增 seam」在 `docs/governance/adr/` 检索 0 命中，属 SKILL 自有约束；ADR-0003 的「1 脚本 + 1 CI 步骤」为工程依据 | `skills/tooling-automate/SKILL.md#L13,L25,L35`；`docs/governance/adr/0003-ci-cd-github-actions.md#L11-12` |
| §4.1 不退化 S1/S2 | S1 六项静态校验、S2 标准库 `unittest` + 覆盖率 ≥80% | `docs/standards/CI-CD.md#s1-代码检查static-checks`、`#s2-自动化测试automated-tests` |
| §4.2 与 `verify-evidence` 衔接 | §8.2 八项检查单为全量校验判据 | `docs/governance/GOVERNANCE.md#L223-233` |
| §4.3 自动化覆盖率 | SKILL 自定指标；分母须在 v2 中布尔化 | `skills/tooling-automate/SKILL.md#L41` |
| §质量门 / §校验标准 | 三件套、flag 双通道、copy/paste 复现、术语合规 | `docs/governance/GOVERNANCE.md#L182-191`；`tools/collect_evidence.py#L41` |
| §失败与豁免 | 人工判读标注为手动；新增 seam 须记理由；不含攻击逻辑 | `skills/tooling-automate/SKILL.md#L58-62` |

## 3. 可复用工具接口盘点（任务—脚本映射初稿）

| 任务类别 | 可脚本化 | 复用入口 | 输出 |
|---|---|---|---|
| 批量证据收集 | 是 | `tools/collect_evidence.py --step --cmd --out --strict` | markdown 片段 + manifest JSONL |
| 技能解剖校验 | 是 | `scripts/validate_skill.py` | 退出码 0/1/2 |
| 术语一致性校验 | 是 | `scripts/check_glossary.py` | 退出码 0/1 |
| Token 预算 / 产物上限 | 是 | `scripts/check_token_budget.py --check` / `--artifact KIND PATH` | 退出码 0/1 |
| 覆盖率门禁 | 是 | `scripts/measure_coverage.py --target all --min 80` | 覆盖率数字 + 退出码 |
| CI 门禁编排 | 是（只串联，不重写） | `.github/workflows/ci.yml#L27-109` | CI 结果 |
| flag 双通道值级真伪 | 否（人工判读） | — | 手动标注 |
| 访问证明截图同屏判读 | 否（人工判读） | — | 手动标注 |

**测试夹具约定**：`tests/test_*.py` + `unittest.TestCase` + `unittest.main()`；模块级 `run()` 用 `subprocess.run([sys.executable, SCRIPT], cwd=ROOT, capture_output=True, text=True)`，`tempfile.TemporaryDirectory()` 造临时夹具，仅标准库。见 `tests/test_collect_evidence.py#L24-31,L86-87`、`tests/test_validators.py#L45-52`。

## 4. 攻击路径 / 对象映射

本技能为编排自动化、**不含攻击路径且零 PyRIT 依赖**（`SKILL.md#L62`），故 §3.1 验收③「每条攻击路径有对象映射」以「任务类别 ↔ 复用入口」映射替代（§3 表），并显式声明例外：实现中不得出现 `pyrit.orchestrator`、`*Orchestrator`、`AzureOpenAIChatTarget`（`docs/research/pyrit-canonical-references.md#L11`）。攻击语义由各 attack-* 子技能承担。

## 5. 核验清单

**已核实**：§1 全部版本 / CI / ADR 事实；§2 全部 16 条条款映射；§3 全部 CLI 参数与退出码；三处指针消歧（§3 S2、零新增 seam 归属、GLOSSARY 预算现值 16500 vs ADR-0006 历史值 13000，见 `scripts/check_token_budget.py#L42-46`）。

**待核实（核实闸，逐条命名）**：

| 编号 | 待核实项 | 取证方式 | 关闭阶段 |
|---|---|---|---|
| VG-1 | 「自动化覆盖率」分母的任务全集与判定口径 | v1 长清单 → v2 布尔验收条件固定集合；`check_token_budget.py --check` 侧不参与 | 3 |
| VG-2 | 是否确需新增 seam（默认零新增）及其理由 | 阶段 2 seam 提案与用户核对 + 阶段 6 设计记录；`grep -rn "seam" docs/governance/adr/` 复核 | 2 / 6 |
| VG-3 | runner 被 attack-* 与 `verify-evidence` 直调时的真实可跑性 | 阶段 8 `collect_evidence.py --step --strict` 单步复现 + 阶段 9 unittest 端到端夹具 | 8 / 9 |
| VG-4 | 目标考试环境是否有额外运行时约束 | 沿用 ADR-0003 零外部依赖结论；环境差异以人工判据记录，不新增依赖 | 8 |

**已排除**：重复实现证据收集（破坏 §6 质量基线）；人工判读任务强行自动化（`SKILL.md#L60`）；新增外部运行时依赖（ADR-0003）；全部 PyRIT 旧版/禁用对象名（`pyrit-canonical-references.md#L11,L17,L27,L29,L35`）。

---

## 门禁记录（阶段 1 · research）

| 编号 | 检查项 | 依据 | 实测结果（命令 + 输出摘要） | 判定 | 不符合项 | 修正要求 | 复验 | 结论 |
|---|---|---|---|---|---|---|---|---|
| B7 | 版本与对象图 | §2.1 B7 | `grep -n pyrit requirements.txt` → `pyrit==1.1.0`；本技能零 import；禁用名清单见 §4 | 符合 | — | — | — | PASS |
| B8 | 可追溯性 | §2.1 B8 | §1–§3 每条带 `路径#L行`；VG-1…4 各带取证方式与关闭阶段 | 符合 | — | — | — | PASS |
| 验收① | 结论可定位 | §3.1 | §2 表 16 行全带一手源位置 | 符合 | — | — | — | PASS |
| 验收② | 版本号明确 | §3.1 | §1 锁定 `pyrit==1.1.0` 并声明零依赖 | 符合 | — | — | — | PASS |
| 验收③ | 攻击路径映射 | §3.1 | 零攻击路径已显式例外，改以任务类别映射（§3/§4） | 符合 | 例外已记录 | — | — | PASS |
| 验收④ | 待核实项命名 | §3.1 | VG-1…VG-4 四条，含取证方式与关闭阶段 | 符合 | — | — | — | PASS |
| 验收⑤ | 落盘 `docs/research/` | §3.1 | `docs/research/tooling-automate-canonical.md` | 符合 | — | — | — | PASS |
| G0 | 表字段齐全 | §2.2 | 9 列表头齐全；判定取「符合」，结论取 `PASS` | 符合 | — | — | — | PASS |

**结论：PASS** — 0 不符合项；进入阶段 2（`to-spec` ①）。
