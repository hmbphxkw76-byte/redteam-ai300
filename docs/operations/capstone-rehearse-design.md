# capstone-rehearse 模块与接口设计（codebase-design）

> **阶段**：主线 阶段 6 · **输入**：规格 v2（`docs/specs/capstone-rehearse-spec-v2.md`）、工单 #234–#239、阶段 2 已确认的 seam 提案、调研 §3 九阶段对象映射
> **结论**：新增单包 `tools/capstone_rehearse/`，以 `rehearse(...)` 为唯一深层模块入口；**新 seam 数 = 2，与阶段 2 用户核对结论一致、数量未增加**；第三类依赖复用既有 `EvidenceSource` adapter，不另立判据。

---

## 1. 模块职责与边界（Module / Implementation）

| 层 | 职责 | 明确不做 |
|---|---|---|
| M-1 就绪来源 | 定义九阶段 `Stage`，扫描仓库给出「技能本体 / 实现落点 / 证据契约 / 片段路径」四项判据 | 不解析片段正文、不调用子进程 |
| M-2 节奏 | 按 §5.4 四段与 §5.3 时间盒构造 `TimelineSlot`，区分建议值与实测值，判 >24h | 不写报告、不改时钟 |
| M-3 走查编排 | `rehearse(...)` 聚合矩阵、时间线、缺口清单、`ready_for_exam`、`pending`、`overtime` | 不直接 glob 文件系统、不读环境变量 |
| M-4 报告渲染 | 由 `RehearsalResult` 生成四件产出的 markdown，按路径引用证据片段 | 不重复存储证据本体、不写 `-real` 路径 |
| M-5 输出 | 版本化机读 JSON + 人读摘要 + CLI 退出码 0/1/2 | 不改写任何上游产物 |

**Depth / Leverage / Locality**：调用方只需学一个接口 `rehearse(inventory, clock, evidence_source)`；九阶段判定、24h 边界、缺口分级、演练标注等复杂度全部隐藏在 M-3 内。修改就绪判据只改 M-1，不扩散到报告与 CLI。

## 2. 公开接口（Interface = 签名 + 不变量 + 错误行为）

| 接口 | 职责 | 输入 | 输出 | 错误行为 |
|---|---|---|---|---|
| `SCHEMA_VERSION` | 机读结果版本常量 | — | `"1.0"` | — |
| `Stage` / `CoverageRow` / `TimelineSlot` / `Gap` / `RehearsalResult` | 数据模型（dataclass） | 构造参数 | 不可变值对象 | 字段类型错 → `TypeError` |
| `StageInventory.stages()` | 返回 §4.5 九阶段定义（有序） | 无（或注入清单） | `list[Stage]`，恰 9 项 | 清单缺阶段 → 返回含未就绪项的列表，不抛异常 |
| `StageInventory.evidence_for(stage_id)` | 给出该阶段四项就绪判据与片段路径 | `stage_id` | `StageEvidence`（4 布尔 + 路径） | 路径不存在 → 该项 False，不抛异常 |
| `Clock.durations()` | 给出各阶段耗时（建议/实测） | 无 | `dict[str, float]` | 负值或非法值 → `ValueError`（CLI 转退出码 2） |
| `Clock.now()` | 时间点 | 无 | `datetime` | 注入非法时间 → `ValueError` |
| `rehearse(inventory, clock, evidence_source)` | 唯一走查入口 | 三个 adapter | `RehearsalResult`（schema_version + 矩阵 + 时间线 + 缺口 + 结论 + `pending` + `overtime`） | 任一 adapter 为 None → `ValueError`；不因单个阶段未就绪抛异常 |
| `render_report(result)` | 渲染演练报告 | `RehearsalResult` | markdown 文本（四件产出） | schema 版本不符 → `ValueError` |
| `render_summary(result)` | 人读摘要 | `RehearsalResult` | 文本（阻断缺口数 / 超时 / 核实闸数） | 空结果返回空串 |
| `main(argv)` | CLI | argv（含 `--inventory` / `--out` / `--report` / `--measured`） | 退出码 0=PASS / 1=未过 / 2=用法错误 | 文件缺失或 JSON 非法 → 2 且 stdout 无 `passed` |

**不变量**：① `RehearsalResult` 是下游唯一消费面；② `pending` 非空 → `ready_for_exam=false`；③ 报告路径引用不含 `-real` 段；④ 同输入双跑结果逐字节相等（AC-18）。

## 3. 依赖方向（单向、无环）

```
main → rehearse → { StageInventory(adapter), Clock(adapter), EvidenceSource(既有 adapter) }
                    └→ loot_manage.registry.fragment_pieces（只读判据）
                    └→ report_exam.index.parse_fragment / MemoryEvidenceSource（只读判据）
       └→ render_report / render_summary（只消费 RehearsalResult）
       └→ tools/collect_evidence.py（仅证据片段生产端，走 --step --strict）
```

- 既有模块（`report_exam`、`loot_manage`、`collect_evidence`）**不反向依赖**本包。
- 不修改 `ci.yml` / `check_token_budget.py` / `GLOSSARY.md` 等共享长行（ADR-0006 三层隔离）；CI 若需新增 `py_compile` 步骤，用独立步骤追加。

## 4. seam 清单与注入点（2 新 + 复用 1）

| seam | 位置 | Adapter（生产 / 测试） | 说明 |
|---|---|---|---|
| S-1 `StageInventory` | 走查入口最高层，`rehearse()` 参数 | `RepoStageInventory`（扫仓库） / `MemoryStageInventory`（内存清单夹具） | 新增，阶段 2 已核对 |
| S-2 `Clock` | 走查入口最高层，`rehearse()` 参数 | `SystemClock` / `FixedClock`（固定时间 + 注入耗时） | 新增，阶段 2 已核对 |
| S-3 `EvidenceSource` | 判据层，复用既有协议 | `DirEvidenceSource`（既有）/ `MemoryEvidenceSource`（既有） | **复用**，不新增 seam |

「一个 adapter 是假想 seam，两个才是真 seam」：S-1/S-2 各有生产与测试两个 adapter，seam 成立；S-3 已有两个既有 adapter，直接复用，不新建。

## 5. 对象图构造收敛位置

本技能**无 PyRIT 对象图**。数据对象（`CoverageRow` / `TimelineSlot` / `Gap` / `RehearsalResult`）的**唯一构造点是 `rehearse()`**：CLI 不重建矩阵，报告层不重建时间线，测试不直接改内部状态。该收敛保证 AC-18 确定性与 AC-12「按路径引用、不重复存证据本体」。

## 6. 测试假后端策略

- `MemoryStageInventory`：注入九阶段清单与逐项删除的就绪四要素（AC-02 删除法）。
- `FixedClock`：注入 23h / 24h / 25h 与 29min / 31min 边界值（AC-05…08）。
- `MemoryEvidenceSource`：复用既有 adapter，注入片段以验证证据链贯通（AC-03 替身计数）。
- 不 mock 标准库 `json` / `datetime`；不启动子进程、不联网、不调用 LLM。

## 7. PyRIT 策略（B7）

零 PyRIT 依赖：本包**不 import** `pyrit`，因此不存在「延迟导入」设计；B7 判定形式为「确认为零 PyRIT 依赖 + 不出现旧版对象名」。版本事实与版本归属偏差（G-F）由阶段 1 调研文档 §5 承载，不在本设计内订正共享权威索引。

## 8. 权衡与被否决方案

| 方案 | 结论 | 理由 |
|---|---|---|
| 3 个全新 seam（独立封装片段解析） | 否决 | 与既有 `parse_fragment` 形成两套判据，违反 C1 单一事实源（阶段 2 已否决） |
| 1 个合并 seam（就绪 + 时钟合一） | 否决 | 时间线判据与就绪扫描耦合，24h 边界无法确定性测试（阶段 2 已否决） |
| 在 `rehearse()` 内直接 glob 文件系统 | 否决 | 调用方创建依赖而非接受依赖，测试必须落盘真实目录，Depth 下降 |
| 重写三件套 / 片段解析判据 | 否决 | 复用 `registry.fragment_pieces` 与 `parse_fragment`，避免门禁判据漂移 |
| 报告层与机读结果合并为同一函数 | 否决 | 职责耦合，AC-11 与 AC-19 无法独立验收 |
| 拆成多个顶层包 | 否决 | 接口数增加、Locality 下降；单包 + 内部小模块已足够 |

## 9. ADR 冲突显式标注

- **ADR-0002**（分值驱动优先级）：无冲突；本技能 P2 且为 §4.5 考前硬门禁，两者语义不同（v1 §7）。
- **ADR-0004**（PyRIT 版本锁定）：无冲突；本包零依赖，见 §7。
- **ADR-0005**（Token 预算）：无冲突；产物上限由 AC-24 承接。
- **ADR-0006**（三层隔离）：**显式约束**——不改共享文件，推送前过 `checkout_lock.py --check`；共享索引版本归属偏差 G-F 由独立工单处理。
- 无新增 ADR；术语增补留到阶段 7。
