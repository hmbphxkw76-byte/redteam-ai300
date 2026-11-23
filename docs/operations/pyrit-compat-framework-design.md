# PyRIT 版本追踪与平滑升级框架设计

> **版本** v1.0 · **日期** 2026-11-24 · **性质** 基础设施设计（不改任何 `SKILL.md`）
> **事实源** `docs/research/pyrit-version-tracking-1.2.x.md`（一手源 URL 与核实日期）、`requirements.txt`、`tools/pyrit_compat/data/`
> **约定** 遵循 `AGENTS.md` C1–C8；ADR-0004 仍是 1.1.0 基线记录，升级到 1.2.1 后须由治理流程决定是否重开 ADR。

## 1. 实现范围

### 1.1 范围内（IN）

1. 全仓 `tools/`、`scripts/` 中 20 个 PyRIT import 点的发现、分类与映射。
2. 1.1.0 / 1.2.0 / 1.2.1 的版本检测、变更记录、签名快照、兼容适配、版本锁定、升级检查、回归测试与告警。
3. 既有调用点中三处预存漂移的修复：`attack-multi-agent` 初始化/目标/攻击构造、`attack-rag` 消息模型；`attack-ai-agent` 版本字符串单一来源化。
4. CI 独立门禁步骤与可复跑 CLI。

### 1.2 范围外（OUT）

1. `skills/*/SKILL.md` 正文、证据三/五件套、flag 双通道、`report-exam` 解析契约——本框架不改变这些契约，只复用其检查命令。
2. 目标环境 `http://192.168.40.189`（OWASP AIVP）业务攻击逻辑与真实凭据。
3. CoPyRIT GUI/backend 部署、Gandalf 等已移除target 的迁移实现（无仓库调用点）。
4. 1.3.x 及未来版本的实际适配代码；框架提供扩展点，事实与适配器须随新版本一手源补录。

## 2. 关键模块

| 模块 | 职责 | 公开接口 | 依赖 |
|---|---|---|---|
| `version.py` | 版本解析、区间判定、单一版本常量 | `Version`、`in_range`、`TARGET_VERSION`、`SUPPORTED_VERSIONS` | 标准库 |
| `versions.py` | PyPI JSON 实时检测 / 离线夹具检测 | `PypiReleaseSource`、`FixtureReleaseSource`、`latest` | `version.py` |
| `model.py` | 变更记录、调用点、告警数据类 | `ChangeRecord`、`CallSite`、`Alert` + 枚举常量 | 标准库 |
| `manifest.py` | 加载并校验变更清单，按版本筛选 | `load`、`for_version`、`unverified` | `model.py`、`version.py` |
| `mapper.py` | AST import 扫描、变更映射、覆盖率、旧 API/评分钩子检测 | `scan`、`classify`、`coverage`、`legacy_alerts`、`hook_alerts` | `ast`、`tokenize` |
| `compat.py` | 显式适配与显式失败；签名快照比对 | `resolve_import`、`adapt_kwargs`、`require_runtime_version`、`signature_alerts` | `alert.py`、`version.py` |
| `alert.py` | JSONL + GitHub Actions 注解 | `emit`、`count_errors` | 标准库 |
| `checker.py` | CLI：`detect` / `map` / `check` / `selftest` | `main(argv)` | 上述全部 |
| `data/versions/<version>.json` | 单一事实源：发布事实 + 变更记录 + 签名快照 + 适配器规则，每版本一文件 | JSON schema 1.0 | — |
| `runtime_probe.py` | 运行时实测（仅本机安装 pyrit 时使用）：签名内省 + 确定性评分器 | JSON 报告 | `manifest`、`inspect` |
| `checker lock` | 从版本事实文件即时生成 pip 哈希锁，不落重复副本 | CLI | `manifest` |

**数据流**：`versions.detect`（实时 PyPI 或版本事实）→ `manifest.load_bundle` 聚合 → `mapper.scan/classify` → `compat`（注册表规则 + 签名比对）→ `alert.emit` → `checker` 退出码（0 PASS / 2 BLOCKED / 3 源不可达）。新增版本只需新增 `data/versions/<version>.json`，核心模块零改动。

**设计约束**：
- 框架顶层与所有技能模块顶层均不 `import pyrit`，保持延迟导入契约与 ADR-0003 零依赖 CI。
- 兼容层不做静默回退：未知参数形态抛 `CompatibilityError`；任何改写必发 `warn`；未映射调用点计为 BLOCKED。
- `require_runtime_version(..., allow_offline_stub=True)` 仅允许「已注入桩、无发行版元数据」的离线测试模式，并返回 info 告警，不伪造版本已验证。

## 3. 迁移内容

| # | 变更/问题 | 迁移动作 | 影响文件 | 验证方式 |
|---|---|---|---|---|
| M1 | 1.2.0 新增 `HTTPTarget.trace_config` | 版本文件登记；规则对 <1.2.0 显式拒绝 | `data/versions/1.1.0.json#adapters`、`1.2.0.json#CHG-001` | `signature_alerts` 产生 `PARAM_ADDED` warn |
| M2 | `params_type` 默认值变化 | 注册表规则显式改写并告警 | `data/versions/1.2.0.json#ADP-PARAM-TYPE` | `test_adapt_kwargs` |
| M3 | 评分钩子更名 | 无子类需改；AST 钩子扫描阻断未来回归 | `mapper.hook_alerts` | `test_no_legacy_or_hook_drift` |
| M4 | 已移除 Gandalf / Python 3.10 | 登记为无调用点 / 环境约束 | `CHG-005`、`CHG-006` | 清单校验 + 本地 Python 3.13.14 |
| M5 | 1.2.1 packaging-only | 明确复用 1.2.0 适配集 | `CHG-011` | 发布页一手源 |
| M6 | `pyrit.common.initialize_pyrit_async` 预存错误 | 改走 `pyrit.setup`；适配层拒绝旧路径 | `pyrit_attack.py`、`compat.py` | `test_resolve_import_rejects_legacy` |
| M7 | `PromptRequestResponse/Piece` 预存错误 | 改为 `MessagePiece` + `send_prompt_async(message=...)` | `attack_rag/backends.py` | `test_attack_rag` 124 例 |
| M8 | `HTTPTarget(http_target=...)` / `PromptSendingAttack(attack_target=..., memory=..., scorer=...)` 预存错误 | 改为 `http_request=` / `objective_target=` + executor + 独立评分 | `pyrit_attack.py` | `test_attack_multi_agent` 55 例 |
| M9 | 版本字符串散落 | 统一引用 `TARGET_VERSION`，`requirements.txt` 固定 1.2.1 | 9 个运行文件 + 3 个测试 | 全量测试 + `grep` |
| M10 | 持续检测与 CI 告警 | 新增独立 CI 步骤与 `detect`/`check` CLI | `.github/workflows/ci.yml` | `checker check` PASS |

## 4. 验证标准

1. **事实完整**：15 条变更均有 `https://` 一手源与核实日期；`unverified(records, "1.2.1") == []`。
2. **映射覆盖**：AST 调用点分类覆盖 100%（当前 20/20，未分类 0）；旧 API/评分钩子告警为 0。
3. **版本矩阵**：1.1.0 / 1.2.0 / 1.2.1 签名快照逐符号比对；`PARAM_REMOVED` 为 0，新增/默认变更均有对应适配。
4. **升级检查**：`python -m tools.pyrit_compat.checker check --root . --target 1.2.1` 退出码 0、`verdict=PASS`；故障注入三类（版本漂移、API 缺失、行为偏离）均非零退出并可读告警。
5. **回归**：`python -m unittest discover -s tests -t . -q` 全绿；新包覆盖率 ≥80%；C1–C8 相关门禁全过。
6. **契约不破坏**：`validate_skill.py`、`check_glossary.py`、`check_token_budget.py --check`、`check_tools_compile.py`、`check_contract_manifest.py`、`check_contract_consumers.py`、`check_evidence_contract.py`、`checkout_lock.py --check` 全过。
7. **运行时实测**：本机 Python 3.13 已装 `pyrit==1.2.1`，`runtime_probe` 14/14 签名 PASS、确定性评分器命中；1.1.0/1.2.0 仍仅源码核实，边界写入 `docs/research/pyrit-version-tracking-1.2.x.md` §6。
8. **可持续升级**：新增 `data/versions/1.3.0.json` 与一条适配器规则后，`check --target 1.3.0` 即得正确判定，核心模块零改动（`test_new_version_requires_only_a_fact_file`）。

## 5. 可复跑命令

```bash
python -m tools.pyrit_compat.checker selftest
python -m tools.pyrit_compat.checker detect --data-dir tools/pyrit_compat/data --minimum 1.2.0
python -m tools.pyrit_compat.checker map --root . --out docs/operations/pyrit-compat-call-sites.json
python -m tools.pyrit_compat.checker check --root . --target 1.2.1
python -m tools.pyrit_compat.checker lock --version 1.2.1
"C:/Users/liude/AppData/Local/Programs/Python/Python313/python.exe" -m tools.pyrit_compat.runtime_probe --version 1.2.1 --report docs/operations/pyrit-compat-runtime-verification.json
python -m unittest discover -s tests/pyrit_compat -t . -q
python scripts/measure_coverage.py --target pyrit-compat --min 80
```
