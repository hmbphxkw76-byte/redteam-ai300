# tooling-automate 设计记录（阶段 6 codebase-design）

> 输入：v1 §4（seam 1 处）、v2 §4（收敛决策）、triage 子工单 #243…#248。
> 约束：零第三方依赖、零新增 seam（仅 S-1）、复用既有共享工具、不含攻击逻辑、不调用 PyRIT。

## 1. 模块树（单包路径，对齐 `tools/loot_manage/`）

```
tools/tooling_automate/
  __init__.py     # 导出 run_plan / main
  __main__.py     # python -m tools.tooling_automate
  cli.py          # argparse: --manifest / --out / --dry-run（进入 S-1）
  manifest.py     # 清单解析层（切片 A #243）
  runner.py       # S-1 统一入口 + 编排执行（切片 B #244）
  reuse.py        # 复用串联既有工具（切片 C #245）
  summary.py      # 结构化汇总输出（切片 D #246）
```

`py_compile` 与 CI S2 按该包路径接线；不为分层新增子包目录。

## 2. 公开接口（签名级）

### manifest.py（切片 A）
- `class Task`：`category, target, step, inputs:dict, outputs, trigger, classification`
- `load_manifest(path: Path) -> Manifest`
- `Manifest.tasks: list[Task]`
- `classify_manual(task) -> bool`（classification == "manual"，不伪造判定）
- `parse_step(step) -> (prefix, index)`：`regex ^[\w-]+-\d+$`，匹配 `<prefix>-01..0N`（AC-07/AC-12）
- `ManifestError` / `UsageError`（非法输入或 step 标识冲突 → 退出码 2，AC-14）

> 实际执行命令放在 `inputs.cmd`（保留 7 个顶层字段不变，命令作为 inputs 子键）。

### runner.py（切片 B · S-1）
- `class CommandRunner(Protocol): def run(self, argv: list[str]) -> RunOutcome`
- `class SubprocessRunner: def run(self, argv) -> RunOutcome`（subprocess, check=False）
- `@dataclass RunOutcome: returncode: int; stdout: str; stderr: str`
- `@dataclass StepResult: task; argv; outcome; strict_ok: bool`
- `@dataclass PlanResult: results: list[StepResult]; coverage: float; manual: list[Task]; exit_code: int`
- `def run_plan(manifest, runner: CommandRunner = SubprocessRunner(), strict: bool = True, dry_run: bool = False) -> PlanResult`
  - 按 step index 排序后顺序执行，无漏步（AC-04）
  - 退出码三值：0 全通过 / 1 门禁失败 / 2 用法错误（AC-13），**不依赖文本输出**
  - 只读：从不自写证据、不改登记簿/报告（AC-17）
- `def main(argv=None) -> int`（CLI 入口，返回退出码）

### reuse.py（切片 C）
- `def build_collect_evidence_argv(task, strict=True) -> list[str]`
  → `['python','tools/collect_evidence.py','--step',step,'--cmd',inputs.cmd,'--out',outputs.evidence,'--strict'|…]`
- `def build_validator_argv(kind, target) -> list[str]`：映射 `validate_skill/check_glossary/check_token_budget/measure_coverage` 既有 CLI
- 编排层**只构造 argv 并经注入 runner 调用**，无等价实现（AC-06；替身断言被调用）

### summary.py（切片 D）
- `def compute_coverage(manifest, executed) -> float`：分母=可脚本化全集，手动单列不计入（AC-03）
- `def render_markdown(result, out_path) -> None`：markdown 表格含路径指针，可被 `verify-evidence` 直调消费（AC-09）；每件含复用声明或新增 seam 理由（AC-10）；含覆盖率与剩余手动清单（AC-11）

## 3. 依赖方向

```
cli → runner(S-1) → manifest(解析) + reuse(构造 argv) + summary(渲染)
reuse → (经注入 runner 调 collect_evidence.py / 各校验脚本)
```

- 无模块 import 其他模块的校验实现；所有判定走外部 CLI，单一事实源。
- runner 不反向依赖 summary/reuse 的具体实现，仅通过注入 runner 解耦。

## 4. seam 清单（仅 1 处，与阶段 2/3 一致）

| seam | 位置 | 形状 | 注入点 |
|---|---|---|---|
| S-1 | `runner.run_plan(manifest, runner=SubprocessRunner())` | CLI 与库调用共用同一公开入口；`CommandRunner` 协议可替换 | `runner` 参数 |

- 既有接缝复用：collect_evidence `--step/--strict` 命令行边界、各校验脚本退出码边界，不另立判据。
- 测试替身：`FakeRunner(records=[])` 记录 argv，断言调用序列（AC-06/AC-08）。

## 5. PyRIT 与测试假后端

- **零 PyRIT 依赖**：`tools/tooling_automate/**` 无 `import pyrit`（B7 判定形式为无 import）。
- **无惰性导入需求**：本技能不装配 PyRIT 对象图，故无 lazy import。
- **假后端策略**：外部命令（collect_evidence / 各校验脚本）经注入 `FakeRunner` 替换，CI 与单测不依赖真实演练目标（`192.168.40.189`）；另留真实脚本串联用例（`tests/test_tooling_runner.py` 中 `test_real_chain`）证明可跑性（VG-3）。

## 6. CI 接线

- S1：`python -m py_compile tools/tooling_automate/*.py`
- S2：`python -m unittest discover -s tests`（覆盖 A/B/C/D/E/F）
- S2：`scripts/measure_coverage.py` 注册目标 `tools/tooling_automate`（门限 80，AC-20）
- S1：`validate_skill.py` / `check_glossary.py` / `check_token_budget.py --check`
