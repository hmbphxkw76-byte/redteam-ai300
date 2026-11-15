# attack-supply-chain 模块与接口设计（阶段6 codebase-design）

> 输入：spec v2 #161（`docs/specs/attack-supply-chain-spec-v2.md`）、工单 #173-176、`tools/collect_evidence.py` 边界。
> 目标：确定深层模块边界与 seam，使实现可测试、可注入、可导航。依赖方向单向，外部库经 seam 注入。

## 1. 模块图（`tools/attack_supply_chain/`）
| 模块 | 职责 | 公开接口（关键） | 依赖 |
|---|---|---|---|
| `workflow.py` | 编排 sc-01~sc-08 顺序，逐段调用 seam 并触发证据落盘 | `run(step, ctx) -> StepResult` | 下列各 seam 模块 |
| `recon_input.py` | **S5** 消费 recon-ai 资产清单 JSON | `load_assets(path) -> SupplySurface` | 仅标准库 |
| `poison_engine.py` | **S2** 适配 IBM ART 投毒类 | `poison_dataset(...)`、`poison_model(...)` | 惰性 import `art` |
| `model_scan.py` | **S3** 封装 ModelScan CLI/JSON | `scan(path) -> ScanResult(findings, severity_max, exit_code)` | 惰性 import `modelscan`/`subprocess` |
| `injector.py` | **S4** 依赖/ETL/构建注入 | `inject_dependency(...)`、`inject_pipeline(...)`、`inject_build(...)` | 仅标准库 |
| `evidence.py` | **S1** 证据契约薄封装（转发 `collect_evidence.py`）+ PyRIT 证据 | `emit(step, pieces) -> path` | `tools/collect_evidence.py`；惰性 `pyrit` |
| `__init__.py` | 包入口 | — | — |

## 2. seam 与注入点（S1–S5 定案）
- **S1 证据**：`evidence.emit()` 转发 `tools/collect_evidence.py --step --strict`；PyRIT 仅用 `SQLiteMemory`/`PrettyAttackResultMemoryPrinter`，构造于 `evidence.py` 内，**惰性导入**，测试可替换为内存假实现。
- **S2 投毒引擎**：`poison_engine` 定义 `PoisonBackend` 协议（`poison_dataset`/`poison_model`）；默认实现包装 ART 类（`PoisoningAttackBackdoor`/`FeatureCollisionAttack`/`GradientMatching`）；注入点 `backend` 参数供测试替身。
- **S3 扫描**：`model_scan.scan()` 默认调用 `modelscan -r json`；`runner` 注入点允许测试注入假 runner 返回预置 JSON+退出码。
- **S4 注入器**：`injector` 三方法返回 `InjectionConfig(config, expected_effect)`；`writer` 注入点供测试替换落盘。
- **S5 recon 输入**：`recon_input.load_assets()` 纯解析，无副作用。

## 3. 依赖方向与对象图
- 方向：`workflow → {recon_input, poison_engine, model_scan, injector, evidence}`；各 seam 不反向依赖 `workflow`（单向）。
- 外部重依赖（`art`、`modelscan`、`pyrit`）**全部惰性导入**，导入失败给出明确错误；测试无需安装即可跑替身。
- 对象图：ModelScan（子进程/库）+ ART（投毒 estimator）+ PyRIT `SQLiteMemory`（证据）。**禁止** `pyrit.orchestrator`/`*Orchestrator`/`AzureOpenAIChatTarget`。
- 无硬编码凭据；端点/路径经 `ctx` 传入。

## 4. 权衡与被否决方案
- 否决：把投毒逻辑直接写在 `workflow`（不可测、耦合外部库）→ 改为 S2 seam。
- 否决：`evidence.py` 自带截图捕获（越界，`collect_evidence` 已定义边界）→ 仅转发。
- 采纳：最少 seam（S1 复用 + S2/S3/S4 新增 + S5 复用），新增 seam 均有测试替身价值。

## 5. 可测试性
- 每个 seam 提供注入点（backend/runner/writer），单元测试注入假后端，断言外部行为（证据件套、扫描判定、注入配置），不断言实现细节。

## 6. 术语映射（SKILL ↔ 框架对象 ↔ 代码标识符）
| SKILL 概念 | 框架/对象 | 代码标识符 |
|---|---|---|
| 发现供应链面 | recon-ai 资产清单 | `recon_input.load_assets → SupplySurface` |
| 数据集投毒 | ART `PoisoningAttackBackdoor`/`FeatureCollisionAttack` | `poison_engine.poison_dataset` |
| 模型/适配器投毒 | ART 投毒 + ModelScan | `poison_engine.poison_model` + `model_scan.scan` |
| 数据管道投毒 | 自定义注入 | `injector.inject_pipeline` |
| 依赖投毒 | 自定义注入 | `injector.inject_dependency` |
| 构建触发 | 自定义注入 | `injector.inject_build` |
| 下游行为取证 | PyRIT `SQLiteMemory` | `evidence.emit` |
| flag 取证 | PyRIT `SQLiteMemory` | `evidence.emit` |

