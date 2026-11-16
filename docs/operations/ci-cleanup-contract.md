# CI/CD 标准化清理契约

> **版本** v1.0 · **状态** 已采纳（2026-11-16）· 落地于 `feat/ci-cleanup`
> **依据**：ADR-0003（无依赖 Python 脚本承载 CI 逻辑）、ADR-0006（共享文件隔离）
> **唯一事实源**：`scripts/ci_cleanup.py`（常量 `PROTECTED_TOPLEVEL` / `CACHE_DIR_NAMES` / `DIST_FILE_NAMES`）
> **接线入口**：`.github/actions/ci-cleanup/action.yml`（复用动作），`ci.yml` / `release.yml` / `report-toolchain.yml`

---

## 1. 目标与判定

把「资源清理、临时文件清理、构建产物清理、缓存清理」固化为**安全、幂等、可复用**的流水线步骤，覆盖每个作业**执行前**与**执行后**，以及 `success` / `failure` / `cancelled` 三种结束状态。

验收判定：

| 编号 | 条件 |
|---|---|
| AC-1 | 每个作业均接线 `pre` 与 `post`；`post` 带 `if: always()` |
| AC-2 | 默认 dry-run，显式 `--apply` 才删除；重复执行无副作用（幂等） |
| AC-3 | 不可删除 git 跟踪文件、配置、依赖、`dist` 交付物（除非显式授权） |
| AC-4 | 临时目标必须落在允许的临时根内；越界、符号链接、临时根自身一律跳过 |
| AC-5 | `verify` 阶段只读断言「无残留 + 交付物仍在」，失败即阻断 |
| AC-6 | 可 `workflow_dispatch` 以 dry-run 手动审计清理范围 |

---

## 2. 双层清单：必须保留 vs 可清理

### 2.1 必须保留（永不清理）

`PROTECTED_TOPLEVEL` 顶层目录整体剪枝：`.git`、`.workbuddy`、`evidence`、`loot`、`dist`、`.env`、`.venv` / `venv`、`node_modules`、`site-packages`、`.tox` / `.nox`。

- 源码、配置、依赖、凭据一律不进入候选集。
- `dist` 视为交付物：默认完整保留；仅 `post` + `--clean-dist` 时，按 `DIST_FILE_NAMES`（`redteam-ai300-skills.tgz` 及其 `.sha256`）**逐文件精确**清理，目录内其他文件不动。
- 受 git 跟踪的路径永不删除；缓存型目录内一旦出现被跟踪文件，整目录受保护。

### 2.2 可清理（白名单）

仅以下**未跟踪**路径进入候选集：

- 缓存目录：`__pycache__`、`.pytest_cache`、`.mypy_cache`、`.ruff_cache`、`htmlcov`
- 构建残渣：`build`、`*.egg-info`
- 缓存文件：`*.pyc`、`*.pyo`、`.coverage`、`.coverage.*`、`coverage.xml`
- 显式临时目标：由 workflow 通过 `--temp-target` 传入，且必须落在 `--temp-root` 内

不在白名单内的任意文件（如 `notes.md`、`random.tmp`）一律不动。

### 2.3 三方交叉验证

| 阶段 | 交付物断言 | 清理范围 | 失败时行为 |
|---|---|---|---|
| S3 构建 | 上传前 `verify --keep-only` 断言 `dist/` 两文件存在 | 上传**成功后** `clean-dist` 清本地副本 | 上传失败则不执行 `clean-dist`，唯一副本保留 |
| S5 发布 | Release 创建前 `verify --keep-only` | 创建成功后 `clean-dist` | 同上 |
| T06 工具链 | 无入库交付物 | `runner.temp` 夹具 + `/tmp` 工具链下载与解压目录 | `if: always()` 覆盖全部结局 |

---

## 3. 触发规则与阶段接线

| 触发事件 | 覆盖范围 |
|---|---|
| `pull_request` → main | S1 / S2 + T06 |
| `push` 到任意分支（`branches: ['**']`） | S1 / S2 + T06 |
| `merge_group`（合并队列） | S1 / S2 + T06，预合并态即验证 |
| `push` tag `v*` | S5 |
| `workflow_dispatch`（`dry_run` 布尔输入） | 手动审计，仅报告不删除 |

每个作业步骤序列：`checkout` → `pre` 清理 → 业务步骤 → `post` 清理（`if: always()`）。`dry_run=true` 时清理器只报告范围，`verify` 附带 `--allow-residue` 避免误阻断。

---

## 4. 安全机制

1. **默认拒绝**：无 `--apply` 不删除；白名单外不删除。
2. **realpath 越界检测**：候选路径解析后必须仍落在根路径内。
3. **符号链接不跟随**：符号链接目录/文件仅记为 `skipped`，不解引用、不删目标。
4. **幂等**：候选不存在即 `absent`，二次运行零删除、零报错（见 `test_second_run_is_noop`）。
5. **审计输出**：每次运行输出单行摘要，可选 `--json` 输出结构化报告（含 `removed` / `skipped` / `failed` / `residue` / `verdict`）。

---

## 5. 复验命令

```bash
python -m unittest tests.test_ci_cleanup -q
python scripts/ci_cleanup.py post                      # dry-run 审计
python scripts/ci_cleanup.py post --apply --json
python scripts/ci_cleanup.py verify --keep dist/redteam-ai300-skills.tgz
python scripts/check_token_budget.py --check
```

本地与 CI 使用同一脚本，判定一致（ADR-0003）。
