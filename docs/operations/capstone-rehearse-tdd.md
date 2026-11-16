# capstone-rehearse TDD 记录（红 → 绿 → 重构）

> 依据规格 v2 §1（25 条 AC）与主线 §3.9；测试只经公开接口断言外部行为。
> 用例集：`tests/test_capstone_rehearse.py`（30 例）、`tests/test_capstone_rehearse_evidence_contract.py`（4 例）、`tests/test_capstone_rehearse_coverage.py`（1 例）。

## 1. 红（真实失败输出留痕）

命令：`python -m unittest tests.test_capstone_rehearse -v`

```text
Ran 25 tests in 1.317s
FAILED (failures=1)
FAIL: test_ac17_all_six_gates_listed_with_evidence_methods
AssertionError: 'VG-1' not found in '# capstone-rehearse 演练报告 ...'
- 待取证核实闸：VG-2、VG-3、VG-4、VG-5、VG-6
```

判据：v2 AC-17 要求「VG-1…VG-6 逐条列出且各带取证方式；VG-1 已关闭」，阶段 8 实现仅输出 `pending` 列表，缺 VG-1 与取证方式，属**规格偏差**而非测试误报。

## 2. 回退阶段 8（主线 §3 第 4 条）

按规范退回第 8 阶段修正并重跑门禁：新增 `model.GATE_DETAILS`（六闸单一事实源，含取证方式）、`RehearsalResult.to_dict()["gates"]`、`report` §4 核实闸清单（状态由 `pending` 动态判定，VG-1 恒为「已关闭」）。复跑记录见 `docs/operations/capstone-rehearse-gate-stage8-recheck.md`（PASS），随后回到本阶段。

## 3. 绿

命令：`python -m unittest tests.test_capstone_rehearse`
输出：`Ran 25 tests in 1.658s / OK`。

## 4. 重构

- 4 处 `open(...).read()` 改为 `with open(...)`，消除 `ResourceWarning`。
- `isinstance(..., StageEvidence)` 改为断言 `ready` 布尔与 `missing()` 元组：覆盖率工具 `measure()` 会 reload 业务模块，类对象重建使类型断言假失败；改后只测外部行为（同时更贴合 v2 §2）。
- 补 5 个 CLI 分支用例（`--out/--report`、`--step`、非法 `--evidence-dir`、`--emit-evidence`、真实仓库 adapter）以提高覆盖率。
- 复跑：`python -m unittest tests.test_capstone_rehearse tests.test_capstone_rehearse_evidence_contract tests.test_capstone_rehearse_coverage` → `Ran 35 tests in 18.490s / OK`。

## 5. 覆盖率（AC-22 / CI S2）

复用 `scripts/measure_coverage.py#measure(modules, test_names)`，不改共享脚本、不改 `ci.yml`（ADR-0006 去冲突约定）。覆盖率测试自身不在 `test_names` 内，避免递归重入。

| 模块 | 可执行行 | 命中 | 覆盖率 |
|---|---|---|---|
| `model.py` | 81 | 80 | 98.8% |
| `inventory.py` | 48 | 44 | 91.7% |
| `clock.py` | 43 | 37 | 86.0% |
| `walk.py` | 78 | 76 | 97.4% |
| `report.py` | 66 | 62 | 93.9% |
| `evidence.py` | 52 | 50 | 96.2% |
| `cli.py` | 98 | 71 | 72.4% |
| **合计** | **466** | **420** | **90.1%** |

`cli.py` 72.4% 是唯一低值（未覆盖：`--measured` 有效输入、`--evidence-dir` 有效目录、`--closed-gates` 解析分支），属非阻断改进项，不影响总体 ≥80% 门槛。

## 6. 门禁数据

- 全量：`python -m unittest discover -s tests` → `Ran 652 tests in 129.003s / OK (skipped=2)`。
- 本地与 CI 一致：CI S2 同样执行 `unittest discover -s tests`；新包覆盖率由 `tests/test_capstone_rehearse_coverage.py` 在 S2 内自测，无需改 CI 接线。
- 红/绿/重构三轮命令与输出摘要完整留痕于本文件，不复制到 issue（T5）。
