# threat-model 设计记录（模块与接口 / seam）

> 版本 v1 · 阶段 6（codebase-design）交付物 · 对齐规格 #159 v2 §D seam 收敛。
> 技能：`skills/threat-model/SKILL.md`（D10/P1）。事实源：`docs/research/threat-model-canonical.md`。输入契约：`tools/recon_ai/model.py`（`ASSET_FIELDS` 七字段，只读复用）。
> 框架组合：矩阵 ⑬（方法论+文档+许可 AI），**无 PyRIT 对象图**（规划技能，不含攻击利用）。

## 1. 设计目标

把「分类资产清单 → 高价值资产清单 / 信任边界+最短路径 / 诱饵判定 / 优先级攻击图」这一纯规划流程实现为**可测试、可注入、单向依赖**的 Python 模块集合，作为 `tools/threat_model/` 落点。接口少、实现深；外部依赖（recon 清单、分析师分类、时钟）经参数注入。

## 2. 模块职责与公开接口

| 模块 | 单一职责 | 公开接口 |
|---|---|---|
| `model` | 领域类型与契约的唯一定义处（不 import 本项目任何模块） | `ScoreClass`／`AssetView`／`PathStep`／`AttackPath`／`DecoyVerdict`／`ThreatModel`／`SCORE_TABLE`／`SURFACE_DOMAINS` |
| `classify` | 合并 recon 七字段清单 + 分析师分类层 → 富化资产视图 | `enrich(inventory: dict, classification: dict) -> list[AssetView]` |
| `score` | 按 §2.2/§2.3 计分排序 + 攻击面归属 | `score_and_rank(assets) -> list[AssetView]` |
| `boundaries` | 信任边界归类 + top-N 最短攻击路径 | `trust_boundaries(assets) -> dict`／`shortest_paths(assets, top_n=3) -> list[AttackPath]` |
| `decoy` | 三维度诱饵判定 + ≤30min 时间盒（时钟注入） | `judge_decoy(asset, elapsed_minutes, now) -> DecoyVerdict` |
| `graph` | 优先级攻击图（诱饵排除）+ §4.5 编排顺序 | `build_graph(assets, paths) -> dict`／`orchestration_order(graph) -> list[str]` |
| `render` | 渲染 markdown 四节 + 质量门四项 | `render(tm: ThreatModel) -> str` |
| `cli` | 命令行入口：读两输入 → build → render；退出码语义 | `main(argv) -> int` |

## 3. 依赖方向（单向，无环）

```
cli ─┬─> classify ─┐
     ├─> score ────┤
     ├─> boundaries┤──> model
     ├─> decoy ────┤
     ├─> graph ────┤
     └─> render ───┘
```

- 所有领域模块只 import `model`；`model` 不 import 任何本项目模块。
- `cli` 是唯一做文件 I/O 的模块；领域模块纯函数，便于确定性单测。
- 无环；新增 seam 数量：2（`classify` 覆盖层、`clock` 注入），均置于最高层。

## 4. seam 清单与注入点

| seam | 位置 | 作用 | 测试替身 |
|---|---|---|---|
| 输入契约（复用） | `cli` 读 recon 七字段清单 | 与 `recon-ai` 解耦，按 `ASSET_FIELDS` 消费 | Fake inventory dict |
| 分类覆盖层 | `classify.enrich` | 分析师补 `score_class/attack_surface/trust_zone/reachable`（recon 不含） | Fake classification dict |
| 时钟 | `decoy.judge_decoy(..., now=)` | 诱饵时间盒时间戳/耗时判定，可注入固定时钟 | Fake clock |

**为何新增 2 seam**：recon 清单缺计分分类与可达性（研究文档 §4），必须由分类覆盖层补齐；诱饵时间盒需确定性时间判定，故注入时钟。两 seam 均置于最外层，不侵入领域逻辑。

## 5. 对象图构造（收敛点）

- 单一公开入口：`build_threat_model(inventory: dict, classification: dict, now=None) -> str`（`cli` 组装并调用各模块，返回 markdown）。
- 构造顺序：`enrich → score_and_rank → answer decoy → shortest_paths → build_graph → render`。
- 本技能**无 PyRIT 对象图**（矩阵 ⑬）；B7 以「不出现旧版对象名」为判据。

## 6. 关键契约

- **输入**：recon 七字段清单（`ASSET_FIELDS`）+ 分类层 `{asset_id: {score_class, attack_surface, trust_zone, reachable, …}}`。
- **输出**：markdown 四节（高价值资产清单 / 信任边界+最短路径 / 诱饵判定清单 / 优先级攻击图）+ 质量门四项自检；每条含 `asset_id` 与 `evidence_step` 锚点，供下游按资产ID复用。
- **不可判定**：分类缺失时资产记「不可判定」（沿用 recon 三值习惯：存在/不存在/不可判定），不臆测。

## 7. 权衡与被否决方案

| 决策 | 采纳 | 否决替代 | 理由 |
|---|---|---|---|
| 分类来源 | 分析师分类层（独立输入） | 工具自动指纹推断计分类型 | 计分类型是考试语义判断，recon 信号不足以推断，自动推断会臆测（违反「不虚构可达性」） |
| 路径计算 | 基于信任域/可达性的结构化推导 | 真实网络图最短路（Dijkstra on live topology） | 规划阶段无实时拓扑，且 SKILL 仅要求规划产出；结构化推导可复现、可审计 |
| 诱饵时间盒 | 注入时钟 + 显式 elapsed 判定 | 依赖 wall-clock | 可确定性单测（TD4 要求超时用例） |
| 攻击框架 | 不引入（矩阵 ⑬） | 复用 PyRIT 承载 | 威胁建模是分析活动，框架是被建模对象；引入 PyRIT 属层级错配 |

## 8. 与 ADR / 术语的一致

- 无 ADR 冲突；「无 PyRIT」是矩阵 ⑬ 的显式范围决定，非偏离「必须」条款。
- 新增术语（威胁模型/信任边界/最短攻击路径/优先级攻击图/计分分类）在阶段 7 入 `GLOSSARY.md`。
