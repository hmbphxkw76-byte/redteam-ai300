# report-exam — 工程规格 v2（历史留痕回填）

> 回溯整理：依据 `skills/report-exam/SKILL.md` 与既有实现、测试归纳；**不代表原流程按序执行**。
> 整理日期：2026-11-27　状态：定稿（v2）

## 1. v1 → v2 差异清单

- 把 v1 的 15 条用户故事收敛为 AC-01…AC-15 布尔验收条件，每条附检查方式与真实测试模块。
- 新增测试决策：只测外部行为，证据源以假后端注入，CI 不打真实目标。
- 新增门禁映射：每条 AC 指向 CI S1/S2 或 `verify-evidence` 八项检查。
- 新增证据与可观测性：片段、步骤标识、AI 日志、双版事实与覆盖率口径。
- 新增风险与待验证：历史留痕与当前复跑差异、真实证据缺口、T11–T20 人工边界。
- v1 七节不改，冲突时以 v1 的行为定义为准；v2 取代 v1 为定稿。

## 2. 布尔验收条件（AC-01…AC-15）

| AC | 验收条件（必须 / 不得 / 至少） | 测试模块 |
|---|---|---|
| AC-01 | 主机键集合必须等于计分目标全集，且无重复主机小节 | `tests.report_exam.test_report_exam.IndexTests` |
| AC-02 | 缺片段的计分目标必须记「未达成」，不得出现伪造命令或输出 | `tests.report_exam.test_report_exam.SectionTests` |
| AC-03 | 报告必须含 Introduction/Objective/Requirements、Executive Summary、Attack Walkthrough、Appendix 六锚点 | `tests.report_exam.test_report_exam.SkeletonTests` |
| AC-04 | 目录必须含 `Offsec AI Red Teamer Report`，版权声明必须逐字 | `tests.report_exam.test_report_exam.SkeletonTests` |
| AC-05 | 每主机小节必须含五段式标记，包括枚举、利用、提权、Proof 与证据归属 | `tests.report_exam.test_report_exam.SectionTests` |
| AC-06 | 源片段的确切命令与关键输出必须在报告中逐字出现 | `tests.report_exam.test_report_exam.SectionTests` |
| AC-07 | 含 AI 交互日志的片段必须全量复制进 Appendix D | `tests.report_exam.test_report_exam.AppendixTests` |
| AC-08 | 证据充分性检查 `vrf-04` 必须为真，双通道缺失不得判通过 | `tests.report_exam.test_report_exam.VerifyTests` |
| AC-09 | 域控 `proof.txt` 提交记录必须恰好一次，重复提交必须阻断 | `tests.report_exam.test_report_exam.VerifyTests` |
| AC-10 | EN 与 ZH 两版从正文抽取的事实块必须逐字一致 | `tests.report_exam.test_report_exam.BilingualTests` |
| AC-11 | 超过阈值的长 PoC 必须分流 Appendix A，正文保留指引 | `tests.report_exam.test_report_exam.AppendixTests` |
| AC-12 | 必须产出官方命名 PDF 与无密码 `.7z`，体积不超过 100MB | `tests.report_exam.test_report_exam.PackagingTests` |
| AC-13 | 组装完成必须通过 `verify-evidence` 八项检查，全绿才可标记可提交 | `tests.report_exam.test_report_exam.VerifyTests` |
| AC-14 | 2 台诱饵机必须记为「确认不可利用」，不得计入计分主机 | `tests.report_exam.test_report_exam.SkeletonTests` |
| AC-15 | 每段引用必须标注来源证据片段路径，可回溯至原子单元 | `tests.report_exam.test_report_exam.SectionTests` |

## 3. 测试决策

- 只测外部行为：给定证据源，断言报告结构、逐字性与校验结论，不断言内部实现细节。
- 假后端注入：以内存证据源与合成片段驱动，覆盖合规、缺失、重复 `proof.txt`、缺章节四类夹具。
- 真实 seam 不进 CI：证据源为唯一注入点，CI 不访问真实演练目标，渲染依赖以注入执行器模拟。
- 证据契约另测：`tests.report_exam.test_report_exam_evidence_contract` 断言 rpt-01…05 步骤声明与官方标题逐字。
- 预检与回填单测：`tests.report_exam.test_preflight` 与 `tests.report_exam.test_backfill` 覆盖占位扫描、命名体积与去占位幂等。

## 4. 门禁映射

| CI 阶段 | 检查 | 覆盖 AC |
|---|---|---|
| S1 | `python -m py_compile tools/report_exam/*.py` | AC-01…15 语法 |
| S1 | `python scripts/validate_skill.py` | B1 解剖结构 |
| S1 | `python scripts/check_glossary.py` | 术语与禁用词 |
| S2 | `python -m unittest discover -s tests/report_exam -t . -q` | AC-01…15 行为 |
| S2 | `python scripts/measure_coverage.py --target report-exam` | 覆盖率 ≥80% |
| S3/S4 | `verify-evidence` 八项检查 | AC-08、AC-09、AC-12、AC-13 |

## 5. 证据与可观测性

- 证据片段：`collect_evidence.py` 产出的原子 markdown，`tools/report_exam/index.py:parse_fragment` 解析，flag 段保留 fenced 原值块。
- 步骤标识：rpt-01…rpt-05 与技能声明一致，由 `EVIDENCE_STEPS` 常量公开比对。
- AI 日志：正文与附录 D 双处保留，附录为全量副本。
- 双版事实：`extract_facts` 从渲染正文抽取并逐字比对，非共享隐藏块。
- 覆盖率：当前复跑 `--target report-exam` 为 491/506 = 97.0%；manifest 口径 45 例 / 2 模块，全目录 `discover` 实跑 54 例通过。

## 6. 风险与待验证

- VG-1：24h 窗口、≤100MB 与评分细则属 S3 事实，待官方 Exam Guide 复核后回填，不臆造数值。
- VG-2：loot 登记簿实际列定义须在实战生成后对齐索引构建。
- VG-3：pandoc 与 7z 环境依赖，缺工具时显式失败并转核实闸。
- VG-4：`proof.txt` 单次在真实取分后由 `verify-evidence` 闭环校验。
- 真实证据缺口：现有 `-real` 片段 flag 双通道均为「未提供」，报告如实记「未达成」，不虚构。
- T11–T20 人工考试边界：真实 OSID、flag 双通道、控制面板值与正式 24h 窗口属人工动作，T19 提交不可逆，不可自动化；演练态 `submission-ready` 仅为工具链验收，非提交许可。
