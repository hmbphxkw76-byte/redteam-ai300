# PyRIT 持续升级 Runbook

> **适用** 从当前目标版本升级到任意新稳定版（1.2.x / 1.3.x+）。
> **单一事实源** `tools/pyrit_compat/data/versions/<version>.json`。核心模块、技能正文、证据契约不随版本改动。
> **原则** 先一手源取证 → 再登记事实 → 最后验证；未核实项标 `UNVERIFIED` 并阻断验收，禁止笼统宣称兼容。

## 0. 前置条件

- 隔离 worktree：`D:/_pyrit-compat_wt`（分支 `feat/pyrit-compat`）；未获明确指令不提交、不推送。
- 两个解释器：WorkBuddy 内置 Python 跑零依赖框架测试；本机 `C:/Users/liude/AppData/Local/Programs/Python/Python313/python.exe` 已装 `pyrit==1.2.1`，仅用于运行时探针。
- 遵守 `AGENTS.md` C1–C8；不改 `skills/*/SKILL.md`、证据三/五件套、flag 双通道。

## 1. 检测新版本

```bash
python -m tools.pyrit_compat.checker detect --data-dir tools/pyrit_compat/data --minimum <上一稳定版本>
python -m tools.pyrit_compat.checker detect --minimum <上一稳定版本>   # 实时 PyPI，需联网
```

记录版本号、上传 UTC、wheel SHA-256；rc/dev 版本自动忽略。

## 2. 一手源取证（每次必做）

1. PyPI JSON API：`https://pypi.org/pypi/pyrit/json` → 版本、日期、哈希。
2. GitHub release：`https://github.com/microsoft/PyRIT/releases/tag/v<新版本>` → 破坏性变更、弃用、移除、行为变化原文。
3. GitHub tag 源码：`v<新版本>` 的 `pyrit/**` → 逐符号 `inspect.signature` 等价的参数名与默认值。
4. 每条结论写 URL 与核实日期；文档站缺失时以 tag 源码为准，并在研究文档标注。

## 3. 新增版本事实文件（唯一需要新增的"代码"）

复制 `data/versions/<上一版本>.json` 为 `data/versions/<新版本>.json`，修改：

- `version`、`release.version`、`release.upload_utc`、`release.hashes`、`release.release_notes_url`、`verified_at`。
- `changes`：仅本版本引入的变更；每条含 `id/category/status/symbol/version_from/version_to/detail/source_url/verified_at/verification/adaptation/adaptation_note`。无变更写 `[]`。
- `signatures`：沿用上一版本快照，只覆盖有实际签名变化的符号；值为 `{kind, params, defaults}`。
- `adapters`：新增规则只对新增/变化符号登记；空数组表示继承既有规则。

适配器规则动作（`actions[].kind`）：
`reject`（整个符号不可用）、`reject_param`（参数移除/改名）、`require_param`（必填）、
`require_min_version`（新增参数的最低版本）、`rewrite_param`（默认值显式改写，必发 warn）。
未登记符号在 `adapt_kwargs` 中显式报错，不静默放行。

## 4. 静态验证

```bash
python -m tools.pyrit_compat.checker selftest
python -m tools.pyrit_compat.checker map --root . --out docs/operations/pyrit-compat-call-sites.json
python -m tools.pyrit_compat.checker check --root . --target <新版本>
python -m tools.pyrit_compat.checker lock --version <新版本>   # 安装时即时生成哈希锁
```

判据：调用点 100% 分类；`error=0`；`verdict=PASS`；新增变更均有适配器或明确的「非影响」登记。

## 5. 运行时验证（本机已安装目标版本时）

```bash
"C:/Users/liude/AppData/Local/Programs/Python/Python313/python.exe" -m tools.pyrit_compat.runtime_probe \
  --version <新版本> --report docs/operations/pyrit-compat-runtime-verification.json
```

判据：`installed_version == 目标版本`；全部签名检查 `PASS`；确定性 `SubStringScorer` 命中。
未安装或沙箱阻断时标 `UNVERIFIED` 并说明理由，不得写成 PASS。

## 6. 回归与门禁

```bash
python -m unittest discover -s tests -t . -q
python scripts/measure_coverage.py --target pyrit-compat --min 80
python scripts/validate_skill.py
python scripts/check_glossary.py
python scripts/check_token_budget.py --check
python scripts/check_tools_compile.py
python scripts/check_contract_manifest.py --check
python scripts/check_contract_consumers.py --check
python scripts/check_evidence_contract.py
python scripts/checkout_lock.py --check
npx markdownlint-cli2 "docs/operations/pyrit-upgrade-runbook.md" "docs/operations/pyrit-compat-framework-design.md"
```

## 7. 回滚

删除 `data/versions/<新版本>.json`、`requirements.txt` 恢复上一版本、`checker check --target <上一版本>` 重跑至 PASS；
运行时报告保留并标注 `ROLLED_BACK`，不删除历史证据。

## 8. 文件变更边界

- **只改**：`data/versions/<新版本>.json`、`requirements.txt`、`docs/research/*`、`docs/operations/*`、必要的调用点测试。
- **永不改**（除非一手源证明且走完整主线）：`tools/pyrit_compat/{version,model,alert,versions,manifest,mapper,compat,checker,runtime_probe}.py` 的核心逻辑、`skills/*/SKILL.md`、证据片段与 flag 双通道契约。
- CI 门禁为独立步骤，已固化，无需随版本改动。

## 9. 交付清单

一手源清单 + 新版本事实文件 + 静态检查报告 + 运行时报告 + 全量门禁摘要 + 更新后的对齐矩阵；
明确列出「哪些结论来自运行时实测、哪些仅来自一手源、哪些 UNVERIFIED」。
