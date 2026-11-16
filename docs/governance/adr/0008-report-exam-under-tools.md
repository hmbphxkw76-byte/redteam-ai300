# ADR-0008：report-exam 组装器迁入 `tools/report_exam`

- 状态：已接受
- 日期：2026-11-16
- 决策者：hmbphxkw76-byte

## 背景

`report_exam` 原为仓库根目录的顶层包，与「根目录只放仓库级文件、可执行工具统一在 `tools/`」的既有布局不一致；重名风险与阅读成本随技能数量增长而上升。该包本属报告组装工具链，调用方仅 `tests/`、`scripts/measure_coverage.py`、`tools/capstone_rehearse/` 与两条 CI 工作流。

## 决策

1. 包迁至 `tools/report_exam/`，唯一调用形态为 `python -m tools.report_exam <index|build>`；根目录不再保留同名包。
2. `package.py` 的 `ROOT` 改为自文件位置回退 3 级（仓库根），确保 `report/`、`evidence/`、`tools/verify_evidence.py` 定位不变。
3. CI 语法编译与报告工具链冒烟改为 `tools/report_exam/*.py` / `python -m tools.report_exam build`；覆盖率与测试导入同步为 `tools.report_exam.*`。
4. 历史记录（日期化实现/验证/评审/审计记录与冻结规格）保留原文路径，作为当时状态快照；「当前仓库现状」类文档（canonical 事实库、契约登记、设计文档）同步新路径。

## 后果

- 旧命令 `python -m report_exam` 不再可用；仓库内当前消费方已全部迁移，CI 不再引用旧形态。
- 报告产物命名、`.7z`/PDF 打包、`verify-evidence` 委托与退出码语义不变；迁移后 `index`/`build` 冒烟与既有门禁结论一致。
- 新增技能或脚本引用组装器时以 `tools.report_exam` 为唯一入口，避免再引入根级包。
