# PyRIT 1.2.x 对齐验证矩阵

> 变更项来源 `tools/pyrit_compat/data/versions/<version>.json#changes`；映射结果 `pyrit-compat-call-sites.json`；检查结果 `pyrit-compat-check-report.json`；告警 `pyrit-compat-check-alerts.jsonl`。
> 判定只取 `PASS` / `BLOCKED`；任一行为 `BLOCKED` 即整轮不通过。

| 变更 ID | 类别/状态 | 一手源 | 映射调用点 | 适配实现 | 测试 | 证据 | 判定 |
|---|---|---|---|---|---|---|---|
| CHG-001 | 参数/新增 | v1.2.0 tag 源码 `http_target.py` | `backends.py:245`、`pyrit_attack.py:36` | `compat.adapt_kwargs` 拒绝 <1.2.0 使用 `trace_config` | `test_adapt_kwargs` | `check-alerts.jsonl` PARAM_ADDED | PASS |
| CHG-002 | 参数/更新 | v1.2.0 tag 源码 `prompt_sending.py` | `backends.py:315`、`pyrit_attack.py:35` | `adapt_kwargs` 显式改写 `params_type` 并告警 | `test_adapt_kwargs`、`test_signature_alerts` | `check-alerts.jsonl` DEFAULT_CHANGED | PASS |
| CHG-003 | 行为/更新 | v1.2.0 发布页 | 0（显式非影响） | `1.2.0.json#CHG-003` 标注 scenario API ≠ `initialize_pyrit_async` | `test_version_filter` | 研究文档 §4 | PASS |
| CHG-004 | 函数/更新 | PR #3312 | 0（无自定义子类） | `mapper.hook_alerts` AST 阻断旧钩子 | `test_no_legacy_or_hook_drift` | `check-report.json` error=0 | PASS |
| CHG-005 | API/移除 | PR #3467 | 0 | `lexer` 旧名告警 + 清单登记 | `test_no_legacy_or_hook_drift` | `check-report.json` error=0 | PASS |
| CHG-006 | 行为/移除 | v1.2.0 发布页 | 0（环境约束） | 锁文件注明 Python `>=3.11,<3.15`；本机 3.13.14 | 命令 `python -V` | 研究文档 §2/§6 | PASS |
| CHG-007 | 行为/更新 | PR #2953 | 0 | 记录为非影响（无 CoPyRIT 集成） | `test_version_filter` | 研究文档 §5 | PASS |
| CHG-008 | 参数/更新 | v1.2.0 发布页 | 0 | 记录为非影响 | `test_version_filter` | 研究文档 §2 | PASS |
| CHG-009 | 行为/更新 | PR #2829 | 0 | 记录为部署约束 | `test_version_filter` | 研究文档 §2 | PASS |
| CHG-010 | 行为/更新 | v1.2.0 发布页 | 0 | `warn` 级备份提示 | `test_signature_alerts` 无 error | `check-report.json` warn=3 | PASS |
| CHG-011 | 行为/更新 | v1.2.1 发布页 | 0 | 复用 1.2.0 适配集 | `test_version_filter` | 研究文档 §3 | PASS |
| CHG-012 | API/移除（预存） | v1.2.1 `pyrit/common/__init__.py` | `pyrit_attack.py` 已修复 | `resolve_import` 显式拒绝 `pyrit.common` | `test_resolve_import_rejects_legacy` | `check-report.json` error=0 | PASS |
| CHG-013 | API/移除（预存） | v1.2.1 `pyrit/models/__init__.py` | `attack_rag/backends.py:110` 已修复 | `Message`/`MessagePiece` + `send_prompt_async` | `test_attack_rag`（124 例） | 研究文档 §4/§5 | PASS |
| CHG-014 | 参数/移除（预存） | v1.2.1 `http_target.py` | `pyrit_attack.py:36` 已修复 | `http_request=` + `adapt_kwargs` 守卫 | `test_attack_multi_agent`（55 例） | `call-sites.json` | PASS |
| CHG-015 | 参数/移除（预存） | v1.2.1 `prompt_sending.py` | `pyrit_attack.py:35` 已修复 | `objective_target=` + executor + 独立评分 | `test_attack_multi_agent`（55 例） | `call-sites.json` | PASS |

**运行时实测（2026-11-24）**：本机 Python 3.13 装 `pyrit==1.2.1`，`runtime_probe` 版本匹配、14/14 签名 PASS、确定性 `SubStringScorer` 命中 `true`；证据 `pyrit-compat-runtime-verification.json`。

**汇总**：15/15 PASS；检查器 `error=0`、`verdict=PASS`；新版本可扩展性测试 PASS（仅新增事实文件 + 规则）。调用点分类与 warn 计数以实跑为准（2026-11-28 复跑 `python -m tools.pyrit_compat.checker check --root . --target 1.2.1`：sites=34、warn=4），本表不转抄动态计数（C1）。

**未达标项（如实登记）**：1.1.0 与 1.2.0 未在本机安装，其结论仅来自官方 tag 源码，不冒充运行时实测；`XPIATestWorkflow` 端到端对象图仍保留 `signature_unverified` 闸门。见研究文档 §6。
