# tooling-automate 阶段 10 代码评审报告（双轴并列）

基线：`git merge-base origin/main HEAD` = `20ce2eb`；diff 范围 `20ce2eb...HEAD`（9 提交，阶段 1–9）。
两轴并列：Standards（标准符合性）/ Spec（规格符合性），每轴独立结论，发现均带文件位置与「硬违规/判断项」分类。

## §1 Standards 轴（依据 AGENTS.md / GOVERNANCE.md / GLOSSARY.md / CI-CD.md）

| # | 位置 | 发现 | 分类 | 处置 |
|---|---|---|---|---|
| S-1 | `GLOSSARY.md` 第 46 行「诱饵机判定」条目 | 阶段 7 压缩时误删第二个「无」：基线「漏洞缺失（无高价值服务/**无**可达入口）」→ 现「（无高价值服务/可达入口）」，语义反转 | **硬违规** | 已还原「无可达入口」（+3 字节，16492/16500 未超限） |
| S-2 | 9 个提交信息 | Conventional Commits：`feat`/`test`/`docs`/`docs(domain)` 前缀合规 | 判断项 | 无需处置 |
| S-3 | `GLOSSARY.md` 其余压缩行（103 行变更） | 抽查「威胁模型」等条目，仅 S-1 一处语义损毁，余者保留原义 | 判断项 | 已核 S-1 |

**Standards 结论：硬违规 1（已清零），判断项 2（无残留）。**

## §2 Spec 轴（依据 docs/specs/tooling-automate-spec-v2.md，AC-01…AC-20）

| # | 位置 | 发现 | 分类 | 处置 |
|---|---|---|---|---|
| P-1 | `tools/tooling_automate/reuse.py:9` | AC-06：规格与设计列 4 校验器（anatomy/glossary/budget/**coverage**），`VALIDATORS` 仅 3，缺 `coverage` | **硬违规** | 已补 `coverage: [python, scripts/measure_coverage.py, --min, 80]`，测试断言 4 校验器 + `--min` |
| P-2 | `docs/operations/tooling-automate-gate-stage{4,5,6,7}.md` C4 行 | 记录「待测后校验」却标 PASS，与实测不符 | **硬违规** | 已复测并回填真实值（1129/919/1229/1751 字节，均 PASS） |
| P-3 | `summary.py` + `runner.py` | 覆盖口径（分母=scriptable、手动排除）在 `compute_coverage` 与 `run_plan` 两处实现，存在重复 | 判断项 | 保留单一实现于 `summary.py`，`runner.py` 调用之（已一致） |
| P-4 | `tests/test_tooling_reuse.py` | 部分断言用 `assertIn` 子串而非精确 argv，弱断言 | 判断项 | 关键契约（`--strict`/`--min`/步骤透传）已用精确断言；子串断言用于路径可移植性 |
| P-5 | `reuse.py:23` `--no-strict` / `--target` | `--no-strict` 与 `--target` 分支无独立 AC 对位测试 | 判断项 | 补入 coverage 用例覆盖 `coverage` 校验器；`--no-strict` 已有 `test_collect_evidence_no_strict` |
| P-6 | `summary.py` `render_markdown` | AC-02 手动排除仅聚合计数，未逐项输出「为何手动」理由 | 判断项 | 手动任务在表格以 `手动` 标注，满足 AC-02「排除出自动化结果」；逐项理由转跟进 |

**Spec 结论：硬违规 2（已清零），判断项 4（3 项当场处置，P-6 转跟进）。**

## §3 修复后复验

- B3：`py_compile` OK；`unittest discover -s tests` → `Ran 650 tests, OK (skipped=2)`。
- 覆盖：`measure_coverage.py --target tooling-automate --min 80` → 91.8%（≥80）。
- B2：`check_glossary.py` PASS（51 术语）；GLOSSARY 16492/16500。
- B7：`test_no_pyrit_import` PASS（零 PyRIT）。

**总发现 9 条（硬违规 3，判断项 6）；硬违规已全部清零，判断项 1 条（P-6）转跟进。结论：可进入阶段 11。**
