# threat-model Ch10 对齐设计记录（阶段 6 · codebase-design）

> 版本 v1 · 日期 2026-11-22 · 上游：规格 v2（issue #324 AC-01..18）、工单 #325..#334、事实源 `docs/research/threat-model-ch10-canonical.md`、既有设计 `docs/operations/threat-model-design.md`（继承不重复）。
> 目标：把 A1–A8 的规划能力实现为可测试、可注入、单向依赖的模块；新 seam 置最外层，领域逻辑保持纯函数。

## 1. 设计目标与不变量
- **不变量（用户确认提示词第四节）**：既有四节与 `quality_gate()` 四项语义不变；新节增量追加；flag 双通道与证据片段原值块保留；classify/时钟 seam 保留；依赖单向；零第三方依赖；无 PyRIT；项目特化三项（诱饵/计分/编排）保留。
- **目标**：13 个公开入口覆盖 AC-01..18；每个外部依赖可注入；测试替身可替换时钟与规则源。

## 2. 模块职责与公开接口
| 模块 | 单一职责 | 公开接口 | 覆盖 AC |
|---|---|---|---|
| `model`（改造） | 领域类型与契约唯一定义（不 import 本项目模块） | 新增 `Assumption` / `TrustBoundary` / `DecisionGate` / `ATLASMap` dataclass；`AssetView` 增 `observations` / `offensive_value` / `access_status`；`AttackPath` 增 `boundary_crossings` / `gates` / `detection_risk`；`ThreatModel` 增 `revision` / `decision_log` / `report_findings` / `brief_version` / `engagement_day`。`quality_gate()` 追加新项但保留原四项 | 01/04/08/11/12/16 |
| `assumptions`（新） | 假设六字段 + 置信度语义 + 状态机 + 证伪派生 | `to_register(observations, classification) -> list[Assumption]`；`transition(a, target) -> (Assumption, list[Assumption])`；`bucket(confidence, source) -> 'attack_plan'|'verification_task'`；`derive_from_detections(rules) -> list[Assumption]` | 01/02/03/14 |
| `boundaries`（改造） | 信任边界实体化 + 三态 + 信任区标注 + 缺口标记 | `trust_boundaries(assets, boundaries=None) -> dict`；`shortest_paths(assets, top_n=3, boundaries=None, assumptions=None) -> list[AttackPath]`（status 改 GO/HOLD/BLOCKED） | 04/05/15 |
| `roe`（新） | RoE 硬过滤 + 双轨输出 | `apply_roe(model, roe) -> (model, findings)`；`is_prohibited(path, roe) -> bool` | 06 |
| `decision`（新） | Go/No-Go 门评估 + 决策矩阵 | `evaluate_gates(paths, assumptions) -> list[AttackPath]`；`go_no_go(paths, assumptions, remaining_days) -> dict` | 08/09 |
| `atlas`（新） | 组件→ATLAS 七 ID 映射 + 前置门槛 | `map_techniques(assets, assumptions) -> list[ATLASMap]`（前置 VALIDATED 才"立即适用"，否则 applicable if） | 13 |
| `brief`（新） | 六段版本化攻击情报简报渲染 | `render_brief(tm) -> str`（六段标题 + Classification/Day/Version + 决策日志） | 07 |
| `render`（改造） | 既有四节 + 新增增量节 | `render(tm)` 追加：假设登记册 / 信任边界五列 / 皇冠珠宝 / 升级路径与决策矩阵 / 简报引用；既有四节 ID 与表头不变 | 01/04/12/07 |
| `classify`（改造） | 覆盖层合并（既有 seam） | `enrich(inventory, classification)` 增传 observations / detection_rules / trust_boundaries 字段；recon 七字段只读 | 11/14 |
| `score`（保留） | 考试计分排序 | `score_and_rank` / `high_value_only` 语义不变 | 12（并存不替换） |
| `graph`（改造） | 优先级图 + 编排顺序 | `build_graph` 接受被 RoE 排除的路径集；`orchestration_order` 不变（项目特化） | 06/18 |
| `cli`（改造，唯一 I/O） | 输入→build→render→门禁 | 增 `--roe <json>` / `--prior <md>`；退出码 0=过门禁，1=未过/输入错，2=用法错 | 06/10/16 |
| `__init__`（改造） | 单一公开入口 | `build_threat_model(inventory, classification, now=None, roe=None, prior=None, new_intel=None) -> ThreatModel`；构造序 `enrich → assumptions → score → boundaries → decoy → decision → roe → graph → atlas → (increment) → brief → render-ready` | 全部 |

## 3. 依赖方向（单向无环）

```
cli ─┬─> classify ──────┐
     ├─> assumptions ───┤
     ├─> score ─────────┤
     ├─> boundaries ────┤
     ├─> decoy ─────────┼──> model
     ├─> decision ──────┤
     ├─> roe ───────────┤
     ├─> atlas ─────────┤
     ├─> brief ─────────┤
     ├─> graph ─────────┤
     └─> render ────────┘
```

- 领域模块只 import `model`；`model` 不 import 本项目任何模块。
- `cli` 唯一文件 I/O；`assumptions` / `roe` / `decision` / `atlas` / `brief` 纯函数（时钟经 `now=` 注入，规则经参数注入）。

## 4. seam 清单（新增 2 + 复用 3，均置最外层）
| seam | 位置 | 作用 | 测试替身 | 状态 |
|---|---|---|---|---|
| 只读输入契约 | `cli` 读 recon 七字段 | 与 recon 解耦 | Fake inventory dict | 复用（既有） |
| 分类覆盖层 | `classify.enrich` | 人工标注假设/观察/RoE/边界/检测规则 | Fake classification dict | 复用（既有，字段扩展） |
| 时钟 | `decoy.judge_decoy(now=)` | 诱饵时间盒确定性判定 | Fake clock | 复用（既有） |
| **规则注入** | `build_threat_model(roe=...)` / `--roe` | RoE 与 new_intel 从最外层入口进入，领域纯函数不读文件 | Fake roe dict | **新增 S-4** |
| **历史注入** | `build_threat_model(prior=..., new_intel=...)` / `--prior` | 上一版模型进入增量重建 | Fake prior dict | **新增 S-5** |

**为何新增 2 seam**：RoE 与历史均为外部输入，若由领域模块自读文件会破坏"cli 唯一 I/O"与可测性；置于最高层构造函数符合用户确认提示词"新 seam 统一置最外层、依赖无环"。与 v1 ID-5 / v2 AC-10 一致。

## 5. 对象图构造（收敛点）
单一入口 `build_threat_model` 顺序：`enrich → to_register(assumptions) → score_and_rank → trust_boundaries → judge_decoy → evaluate_gates → apply_roe → build_graph → map_techniques → (prior/new_intel increment) → (render / render_brief 由 cli 分流)`。
- `apply_roe` 在 `evaluate_gates` 之后：先确定路径门状态，再硬过滤，被禁路径转 `report_findings`（双轨）。
- `map_techniques` 在假设 VALIDATED 判定之后：保证 applicable if 前置门槛可读。

## 6. 关键契约与兼容性
- **输入**：recon 七字段（只读）+ 分类层 `{asset_id:{score_class,attack_surface,trust_zone,reachable,...,observations}}` + 可选 `roe` / `prior` / `new_intel`。
- **输出**：既有四节 markdown（表头/ID 不变）+ 新增节 + 独立 `render_brief` 简报；`quality_gate()` 既有四项语义不变，新增项追加。
- **不可判定**：分类缺失记「不可判定」；假设来源缺失记 UNVALIDATED + 缺证标记；不臆测（沿用既有三值习惯）。
- **证据契约**：`render` 不得改动 flag 段原值块结构；回归 `report_exam.index.parse_fragment`。
- **术语**：信任区（trust zone）≠ 信任边界（trust boundary）；新增"推理强制边界/假设登记册/皇冠珠宝/攻击情报简报"走阶段 7 入 GLOSSARY。

## 7. 权衡与被否决方案
| 决策 | 采纳 | 否决 | 理由 |
|---|---|---|---|
| 新能力落点 | 增量新模块 + 既有模块最小改造 | 全部塞进 `model.py` 单文件 | 单职责 + 可测；避免 model 膨胀破坏"不 import 本项目模块"不变量 |
| RoE 过滤时机 | 门评估后、图构建前 | 渲染后过滤 | 双轨输出需在图构建期分离 plan/findings |
| ATLAS 映射 | 纯函数 + 七 ID 常量表 | 运行时 WebFetch | 规划阶段无网络；版本核实走阶段 1/8 取证闸（research 已记录） |
| 增量重建 | prior/new_intel 注入 + revision 递增 | 全量重跑覆盖 | 保留决策日志与已验证假设（AC-10） |
| 攻击框架 | 不引入 | PyRIT 承载 | 矩阵 ⑬；规划技能层级错配 |

## 8. 阶段 6 门禁记录（G0 · B2/B7/B8）
| 基线 | 判定 | 证据摘要 |
|---|---|---|
| B2 术语 | 符合 | 设计区分信任区/信任边界；新增术语列于 §6 待入 GLOSSARY |
| B7 PyRIT | 符合（不适用） | 设计无对象图、无旧版编排器名；矩阵 ⑬ 无专用框架 |
| B8 可追溯 | 符合 | 每模块接口标 AC 编号；seam 与 v1 ID-5/v2 AC 对应；否决方案附理由 |

**结论**：PASS。不符合项 0。
