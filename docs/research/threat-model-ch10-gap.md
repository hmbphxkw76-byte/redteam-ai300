# Ch10 差距分析 — threat-model 对照 OffSec AI-300《Threat Modeling for AI-Enabled Targets》

> **版本** v1.0 · **状态** 分析交付物（untracked） · **日期** 2026-11-22
> **一手源** `D:\视频\OffSec   AI-300 Advanced AI Red Teaming\Ch10-Threat-Modeling-for-AIEnabled-Targets.html`（§10/§10.1/§10.2/§10.3，Table 1–9、Listing 1–8、Figure 1–8）
> **对照对象** `skills/threat-model/SKILL.md`、`tools/threat_model/`（8 模块）、`threat-model-canonical.md`、`threat-model-design.md`
> 结论附文档锚点（§/L/Table/Listing）或实现锚点（file#symbol）；不改 SKILL.md 与代码。

## 1. 结论摘要

1. **根本错位**：现有 `threat-model` 是围绕 OSAI 考试计分（§2.2/§2.3）与考前 24h 编排（§4.5）的**一次性静态规划器**；Ch10 定义的是随情报演进的**活体方法**（living artifact + 假设登记册 + 跨边界升级路径 + RoE 硬过滤 + 版本化简报）。二者在"资产排序/信任边界/最短路径/攻击图"上同名不同义。
2. **完全缺失的 P0 骨架**：假设登记册+置信度、带验证态的边界分类（含推理强制）、跨区升级路径+Go/No-Go、RoE 硬过滤、版本化简报——五项一项都没有。
3. **同名不同义**：`高价值资产清单`（考试分）≠ `皇冠珠宝`（进攻价值）；`trust_boundaries()`（按 zone 分组）≠ Ch10 边界分类；`shortest_paths()`（套模板）≠ 跨边界路径；`orchestration_order()` ≠ 决策树。
4. **输入侧缺口**：假设/置信度/来源/验证态在 recon 七字段无对应；`classify.enrich` 仅注入 4 类标注。
5. **项目特化（非差距，保留）**：诱饵时间盒、考试计分、§4.5 编排。

## 2. 文档要求分解（Ch10 一手源）

### 2.1 核心流程与方法（M1–M18）
| # | 要求 | 锚点 |
|---|---|---|
| M1 | 活体产物，随情报/假设验证/范围约束持续演进 | §10 L13–17；§10.3 L1103–1112 |
| M2 | observe→hypothesize→test→update→decide→act | §10.3 L1103–1112 |
| M3 | 从碎片重建架构：scoping/OSINT/客户资料→渐进主动侦察 | §10.1 L50–121、L207–243 |
| M4 | 假设登记册六字段（ID/Observation/Hypothesis/Confidence/Source/Status）+ 状态机（UNVALIDATED→VALIDATED/INVALIDATED）+ 反馈环 | §10.1 L122–206，Table 1，Figure 1 |
| M5 | 置信度=来源可靠性而非正确概率；缺证≠漏洞，低置信假设驱动验证任务 | §10.1 L188–200（A-07 Info） |
| M6 | 皇冠珠宝按当前知识进攻价值排序并随情报重排，标注访问状态 | §10.1 L450–513，Table 5 |
| M7 | 组件→MITRE ATLAS 技术 ID + 适用性；`applicable if` 前置未高置信确认前不入执行计划 | §10.1 L514–555，Table 6 |
| M8 | 低垂果实优先：先榨取当前可达情报（检测规则）反哺决策 | §10.1 L556–619，Listing 7 |
| M9 | 信任边界分类（从→到/类型/强制机制/验证状态/进攻含义）；区分**策略强制**与**推理强制**；AI 特有边界（分类信任/RAG 建议/身份塌缩） | §10.2 L704–779，Table 8 |
| M10 | 信任区（trust zone）划分：按已验证情报切分共享权限区；实线=VALIDATED、虚线((?))=UNVALIDATED | §10.2 L780–786，Figure 4 |
| M11 | 跨边界多步升级路径：每条含 Go/No-Go、时间约束、检测风险、前置依赖；计划是决策树非脚本 | §10.2 L787–915，Path 1/2/3 |
| M12 | RoE/范围作**硬过滤器**：禁止路径移出执行计划（仍作风险发现进最终报告），禁止"if client approves"式保留 | §10.1 L286–305；§10.2 L793–796 |
| M13 | Go/No-Go 决策矩阵：信息可用/缺失、验证时间成本、GO/HOLD；时间压力下排序 | §10.2 L869–915，Table 9，Figure 8 |
| M14 | 版本化攻击情报简报：target summary/crown jewels/assumption status/scope constraints/escalation paths/next actions；版本史=决策日志 | §10.2 L924–1020，Listing 8 |
| M15 | 重规划：验证意外→路径废弃→新假设（A-16）→新路径；证伪是约束非消除 | §10.2 L1021–1057 |
| M16 | 检测规则情报化→派生假设；承认规则集不完整（Qdrant 外可能有其他检测） | §10.1 L570–619，A-12…A-15 |
| M17 | 身份塌缩/归属：TB-5 边界身份塌缩致审计归属丢失 | §10.2 L426–438、L750–779 |
| M18 | 最危险路径穿过"从未强制信任的缺口"（未认证 DB、无法区分 agent 的 Vault） | §10.3 L1113–1121 |

### 2.2 输出要求
假设登记册｜带置信度架构图｜皇冠珠宝排序｜ATLAS 映射表｜信任边界表｜信任区图｜升级路径流图+Go/No-Go｜决策矩阵｜版本化简报（决策日志）｜RoE 排除路径转报告风险发现。（§10.1 Table 1/5/6；§10.2 Table 8/9、Figure 2/4/5/6/7/8、Listing 8）

### 2.3 边界条件与注意事项
RoE 硬约束（禁生产库写/投毒仅 staging/无 DoS/无真实 PII/MCP 24h 报告/测试窗口）；in/out of scope；时间盒 10 工作日；置信度=来源可靠性；未验证边界与未确认前置不进执行计划；缺证非漏洞证据；推理边界≠策略边界；目标为 AIVP 非 OSAI 正式环境。（§10.1 L60–100、L286–305；§10.2 L869–915）
注意：证伪比确认更有价值（L652–661）；验证即回写登记册；简报价值在"诚实"非"完整"（L1000–1009）；计划是决策树（L916–923）；"成功的是 Day 3 能正确重规划的团队"（L1055–1057）。

## 3. 结构化对照表

> 列：文档要求 → 现有实现 → 缺失/不足 → 可强化点 → 影响范围 → 优先级（P0 最高）→ 具体改进建议。

### 3.1 方法与流程骨架
| 文档要求（Ch10） | 现有实现 | 缺失/不足 | 可强化点 | 影响范围 | 优先级 | 改进建议 |
|---|---|---|---|---|---|---|
| M1/M2 活体模型+迭代节奏 | `__init__.py#build_threat_model` 一次性构建，无状态 | 无更新/再规划入口，无决策日志 | `revision`+`update(intel)` 增量入口 | `tools/threat_model/*`、`cli.py` | P1 | `ThreatModel` 增 `revision`/`decision_log`；`build_threat_model(...,prior=None,new_intel=None)`；CLI `--prior` |
| M3 碎片渐进重建 | `classify.py#enrich` 合并 recon 七字段+分析师标注（`canonical.md#§4`） | 无"观察来源/假设"层承载推测 | `evidence_step` 升级为来源链；增 `observation` | `recon-ai`、`classify.py`、`model.py` | P1 | `AssetView` 增 `observations:[{source,text,confidence}]`；`enrich` 支持；与 `evidence_step` 互链 |
| M4/M5 假设登记册+置信度+状态机 | 无（`model.py` 无 Assumption；全仓关键词 0 命中） | **完全缺失**六字段/状态机/置信度语义 | LOW/缺证假设标 `verification_task` 非 `attack_plan` | `model.py`、`classify.py`、`render.py`、`report-exam` | **P0** | 新建 `assumptions.py`：`Assumption(id,observation,hypothesis,confidence,source,status)`+`transition()`；render/SKILL.md 增节 |
| M15 证伪生成新假设 | 无；`graph.build_graph` 静态排除诱饵，无路径废弃/重生 | 无比"否→新假设→新路径"闭环 | 与状态机联动：`INVALIDATED` 触发派生假设+路径重算 | `assumptions.py`、`graph.py`、`cli.py` | P1 | `transition(→INVALIDATED)` 返回派生假设；`build_graph` 接受 `invalidated_paths` |

### 3.2 信任建模
| 文档要求（Ch10） | 现有实现 | 缺失/不足 | 可强化点 | 影响范围 | 优先级 | 改进建议 |
|---|---|---|---|---|---|---|
| M9 边界分类+推理强制+验证态 | `boundaries.py#trust_boundaries` 仅按 `trust_zone` 分组 | 语义分叉：无从→到/类型/强制/验证态/进攻含义；无推理边界 | 建 `TrustBoundary`（`enforcement`/`validation_status`/`trust_type`） | `boundaries.py`、`model.py`、`render.py`、`attack-multi-agent` | **P0** | 新建 dataclass；由分类层字段驱动；render 边界节改 5 列；补"推理强制边界"术语 |
| M10 信任区图+验证标注 | `trust_boundaries()` 输出 `{zone:[id]}`，render 2 列；无实线/虚线 | 无验证态可视化，无共享权限区语义 | 增 `zone.validation` + 渲染态 | `boundaries.py`、`render.py` | P1 | 分组值携带 `validation`，render 输出 `zone (VALIDATED)`/`zone (?)` |
| M17 身份塌缩/归属 | 无 | 完全缺失 | `identity_collapse:bool` 标注归属风险 | `model.py`、`boundaries.py` | P2 | `TrustBoundary` 增字段；render 标"归属丢失" |

### 3.3 路径规划与约束
| 文档要求（Ch10） | 现有实现 | 缺失/不足 | 可强化点 | 影响范围 | 优先级 | 改进建议 |
|---|---|---|---|---|---|---|
| M11 跨边界路径+Go/No-Go | `boundaries.py#shortest_paths` 套 `STAGE_TEMPLATE`+`SUBSKILL`；`AttackPath` 仅 stages/耗时/依赖/状态 | 语义分叉：无跨边界步骤、Go/No-Go、前置假设、检测风险 | `AttackPath` 增 `boundary_crossings`/`gates`/`detection_risk` | `boundaries.py`、`model.py`、`render.py`、`attack-*` | **P0** | `shortest_paths()` 接受 boundaries+assumptions；出 Go/No-Go 表；`status` 扩 `GO/HOLD/BLOCKED` |
| M12 RoE 硬过滤 | 无（RoE 命中仅在 `attack-rag`）；`build_graph` 仅排除诱饵 | **完全缺失**；无"执行排除/报告保留"双轨 | `rules_of_engagement` 输入 + `apply_roe()`；排除路径转 `report_findings` | `model.py`、`graph.py`、`cli.py`、`report-exam` | **P0** | 新建 `roe.py#apply_roe()`；CLI 增 `--roe`；`ThreatModel` 增 `report_findings` |
| M13 Go/No-Go 矩阵+时间压力 | 无（`决策矩阵` 命中仅在 `attack_embeddings/decision.py`，无关） | 完全缺失：信息可用/缺失、验证成本、GO/HOLD | 决策矩阵生成，含 `time_cost`/`information_missing` | 新 `decision.py`、`render.py` | P1 | `go_no_go(paths,assumptions,remaining_days)` 出 Table 9 结构；render 增节 |
| M6 皇冠珠宝按进攻价值 | `score.py#score_and_rank`+`SCORE_TABLE` 按考试分 | 语义分叉：得分非进攻价值；无访问状态/置信度 | 与考试分**并存**增 `offensive_value`（不改 §2.2/§2.3 契约） | `score.py`、`model.py`、`render.py` | P1 | `AssetView` 增 `offensive_value`/`access_status`；render 增"皇冠珠宝"节 |
| M7 ATLAS 映射+前置门槛 | `canonical.md#§2` 仅列 ATLAS/OWASP URL；工具无 AML.T 映射 | 缺失：无组件→ATLAS ID，无 `applicable if` 门槛 | 增 `atlas_map` + 前置校验；版本需 WebFetch 核实 | `model.py`、新 `atlas.py`、`canonical.md`、`render.py` | P1 | `map_techniques(assets,assumptions)`；仅前置 `VALIDATED` 标"立即适用"；版本考前复核 |

### 3.4 输出与交付物
| 文档要求（Ch10） | 现有实现 | 缺失/不足 | 可强化点 | 影响范围 | 优先级 | 改进建议 |
|---|---|---|---|---|---|---|
| M14 版本化攻击情报简报+决策日志 | `render.py#render` 四节+质量门，无 brief/版本 | **完全缺失**六段简报与版本史 | 新增渲染节，字段对齐 Listing 8 | `render.py`、`model.py`、`report-exam` | **P0** | 新 `brief.py#render_brief()` 出六段+Version/Day；`ThreatModel` 增 `brief_version`/`engagement_day` |
| M8/M16 检测规则→假设 | 无 | 完全缺失 | `detection_rules` 输入→派生假设 | `assumptions.py`、`classify.py` | P2 | `derive_from_detections()` 生成 A-12 类假设，标 MEDIUM+规则集不完整 |
| M18 信任缺口识别 | 无（`decoy.py` 只做诱饵） | 无"从未强制信任的缺口"识别 | `enforcement=None` 高亮为进攻首选 | `boundaries.py`、`render.py` | P2 | 标 `TRUST_GAP`，render 高亮，路径加权 |
| 输出契约兼容（项目侧） | 四节+`quality_gate()`，兼容 `report-exam`/`verify-evidence`（`canonical.md#§9`） | 扩节后不破坏既有四节与判据 | 新节**增量**追加，不改四节 ID 与 flag 段 | `render.py`、32 测试例、`report-exam` | **P0** | 新节追加四节后；`quality_gate()` 加项保留原四项；回归 `report_exam.index.parse_fragment` |

### 3.5 项目特化（非差距，保留）
诱饵时间盒（OSAI §5.3，Ch10 无）→ `decoy.py#judge_decoy`；考试计分（§2.2/§2.3）→ `SCORE_TABLE/RANK_INDEX`；§4.5 编排 → `graph.py#orchestration_order`。三者保留；M6 进攻价值视角与计分并存，M11 决策树与编排顺序粒度不同。

## 4. 总体差距摘要

| 维度 | 现状 → Ch10 要求 | 等级 |
|---|---|---|
| 生命周期 | 一次性静态 → 活体 + 增量更新 + 决策日志 | 大 |
| 假设管理 | 无 → 六字段登记册 + 状态机 + 置信度 | **缺失** |
| 信任建模 | 按 zone 分组 → 分类边界（推理强制/验证态/身份塌缩）+ 区图 | **缺失（分叉）** |
| 路径规划 | 套 `score_class` 模板 → 跨边界路径 + Go/No-Go + 检测风险 | **缺失（分叉）** |
| 约束处理 | 仅排诱饵 → RoE 硬过滤 + 双轨 | **缺失** |
| 目标排序 | 考试分 → 进攻价值 + 访问状态（并存） | 中 |
| 技术映射 | 仅方法论 URL → 组件→ATLAS ID + 前置门槛 | 中 |
| 交付物 | 四节 md → 六段版本化简报 | **缺失** |
| 闭环 | 无 → 证伪→新假设→重规划 | **缺失** |

**量化**：M1–M18 中 P0 完全缺失 4 项（M4/M9/M12/M14），P0 语义分叉 2 项（M11/M13），P1 缺失/分叉 6 项，P2 2 项。概念重叠约 30%，且多为同名不同义。

## 5. 建议优先处理的 skill 清单

| 序 | skill / 模块 | 优先级 | 处理内容 |
|---|---|---|---|
| 1 | `threat-model`（新 `assumptions.py`+`model.py`/`render.py`/SKILL.md） | **P0** | 假设登记册+状态机+置信度+反馈环；新增渲染节；走 11 阶段主线，新 seam 置最外层 |
| 2 | `threat-model`（`boundaries.py`/`model.py`/`render.py`） | **P0** | 边界实体化+推理边界+验证标注；不破坏现有返回 |
| 3 | `threat-model`（新 `roe.py`+`graph.py`/`cli.py`） | **P0** | RoE 硬过滤+双轨；CLI `--roe`；衔接 `report-exam` |
| 4 | `threat-model`（新 `brief.py`+`render.py`） | **P0** | 六段版本化简报+决策日志；追加节不改四节 ID |
| 5 | `threat-model`（`boundaries.py`+新 `decision.py`） | **P0/P1** | 跨边界路径(Go/No-Go+检测风险)+决策矩阵 |
| 6 | `recon-ai`（`model.py#ASSET_FIELDS`） | P1 | 清单增观察来源链（扩展字段不破坏七字段） |
| 7 | `threat-model`（`score.py`+新 `atlas.py`） | P1 | 皇冠珠宝进攻价值视角+ATLAS 映射及前置 |
| 8 | `threat-model`（`assumptions.py`+`classify.py`） | P2 | 检测规则→假设+身份塌缩/信任缺口 |

> 差距高度集中于单一 skill（8 项中 7 项），`recon-ai` 仅输入侧一处。建议 1→5 合并为一次主线增量落地（新 seam 统一置最外层，依赖无环），避免多次改写 SKILL.md 与渲染契约。

## 6. 追溯索引（结论 ← 文档 / 实现）

| 结论 | 文档依据 | 实现依据 |
|---|---|---|
| 无假设登记册 | §10.1 Table 1/L122–206 | `model.py` 无 Assumption；关键词 0 命中 |
| 边界语义分叉 | §10.2 Table 8/L704–779 | `boundaries.py#trust_boundaries`（按 zone 分组） |
| 路径无 Go/No-Go | §10.2 Table 9/L869–915 | `model.py#AttackPath`（无 gates/detection） |
| 无 RoE 硬过滤 | §10.1 L286–305 | `graph.py#build_graph`（仅排诱饵） |
| 无版本化简报 | §10.2 Listing 8/L924–1020 | `render.py#render`（四节+质量门） |
| 皇冠珠宝分叉 | §10.1 Table 5/L450–513 | `score.py#score_and_rank`（考试分） |
| ATLAS 未落地 | §10.1 Table 6/L514–555 | `canonical.md#§2`（仅 URL） |
| 输出契约约束 | — | `model.py#quality_gate`、32 测试例、`canonical.md#§9` |

## 7. 边界与限制
- 一手源 45MB HTML（内嵌媒体），正文经 stdlib HTMLParser 抽取逐节阅读；Figure 1–8 仅纳入文字说明，未逐像素核验。
- 未改既有文件、未建 worktree、未提交；main 上其他会话文件未触碰。
- 优先级按"覆盖度 × 契约影响"排序；排期叠加 GOVERNANCE §9.2 保分优先与 ADR-0005（C8 不可豁免）。
