# capstone-rehearse 实现清单与规格对应矩阵（阶段 8）

> **依据**：规格 v2（issue #231 评论 / `docs/specs/capstone-rehearse-spec-v2.md`）、设计 `docs/operations/capstone-rehearse-design.md`、工单 #234–#239。
> **性质**：最小实现切片（接口完整、可编译、可验证）；完整 AC 用例集与红—绿—重构收敛在阶段 9。

## 1. 变更清单（与工单一一对应）

| 工单 | 新增文件 | 职责 |
|---|---|---|
| #234 | `tools/capstone_rehearse/model.py`、`inventory.py`、`walk.py` | 数据模型、S-1 就绪来源 adapter、九阶段矩阵与唯一走查入口 |
| #235 | `clock.py`（+ `walk._timeline`） | S-2 时钟、§5.4 四段、§5.3 时间盒、>24h 压缩建议 |
| #236 | `model.Gap` + `walk.rehearse` 缺口段 | 阻断性/非阻断二档、补强建议、核实闸 |
| #237 | `report.py` | 四件产出的演练报告、按路径引用、演练标注与来源锚点 |
| #238 | `cli.py`、`__init__.py`、`__main__.py` | 机读 JSON、CLI 三态、公开导出 |
| #239 | `evidence.py`、`tests/test_capstone_rehearse_evidence_contract.py` | 委托共享收集器的证据片段与三件套契约测试 |
| 共性 | `docs/operations/capstone-rehearse-implementation.md` | 本对应矩阵与变更清单 |

`SKILL.md` 保持为行为唯一来源，未改写；未修改任何共享文件（`GLOSSARY.md` / `ci.yml` / 校验脚本），符合 ADR-0006。

## 2. AC → 实现位置矩阵（25/25）

| AC | 实现位置 | AC | 实现位置 |
|---|---|---|---|
| AC-01 | `inventory.stages_from_specs` + `walk.rehearse` 矩阵 9 行 | AC-14 | `cli.main` 只读构造 `DirEvidenceSource`，不改 `verify-evidence` |
| AC-02 | `model.StageEvidence.ready` / `missing`；`MemoryStageInventory` 注入 | AC-15 | 门禁实跑 `check_glossary.py` |
| AC-03 | `walk._chain` 委托 `registry.fragment_pieces(Fragment.raw)`，不另立判据 | AC-16 | `walk.rehearse` 的 `ready` 合取；实现无真实利用动作 |
| AC-04 | `evidence.EvidenceWriter` + `report.SOURCES` + 片段路径引用 | AC-17 | `model.GATE_DETAILS` + `report` §4 核实闸清单 + `walk.pending` |
| AC-05 | `clock.SEGMENTS` + `walk._timeline`（start/end/duration/key_node 递增） | AC-18 | `model.RehearsalResult.to_dict`（sort_keys）+ `FixedClock` 固定时间 |
| AC-06 | `clock.DECOY_TIMEBOX` + `_timeline` 独立时间盒行 | AC-19 | `cli.main` 退出码 0/1/2 + `render_summary` |
| AC-07 | `_timeline` `overtime` / `compression`；`report` §2 | AC-20 | `report.SOURCES` 四条一手来源锚点 |
| AC-08 | `TimelineSlot.estimate/measured`；`report` 显示「未实测」 | AC-21 | `evidence.EvidenceWriter` `--strict` + `--ai-log` + flag 保持 N/A |
| AC-09 | `walk.rehearse` 缺口段 + `Gap.suggestion` | AC-22 | 阶段 9 全量 unittest 与覆盖率（本阶段 `py_compile` 通过） |
| AC-10 | `model.BLOCKING/NON_BLOCKING` + `RehearsalResult.blocking/non_blocking` | AC-23 | 全包零 `import pyrit`（源码扫描见门禁记录） |
| AC-11 | `report.render_report` 四节 + `ready_for_exam` 布尔 | AC-24 | 门禁实跑 `--artifact` 六类 |
| AC-12 | `report.render_report` 只写片段路径，不写片段正文 | AC-25 | 门禁复核 v1 字节数与 32 条 US 未变 |
| AC-13 | `report.DISCLAIMER` + 路径过滤 `-real` 段 | — | — |

## 3. 每步证据片段（B4 / copy/paste 可复现）

统一命令模板（由 `--emit-evidence` 实际执行并捕获真实 stdout 作为「关键输出」）：

```bash
python -m tools.capstone_rehearse --stdout --step cr-NN
python tools/collect_evidence.py --step cr-NN --strict --cmd <上述命令> --out evidence/capstone-rehearse-drill/cr-NN.md
```

| 片段 | 走查步骤 | 三件套 | AI 交互日志 | flag |
|---|---|---|---|---|
| `evidence/capstone-rehearse-drill/cr-01.md` | 九阶段覆盖度矩阵 | 齐全 | 有 | 未提供（N/A） |
| `cr-02.md` | 24h 节奏时间线 | 齐全 | 有 | 未提供 |
| `cr-03.md` | 缺口清单与分级 | 齐全 | 有 | 未提供 |
| `cr-04.md` | 证据链贯通核对 | 齐全 | 有 | 未提供 |
| `cr-05.md` | 演练报告四件产出 | 齐全 | 有 | 未提供 |
| `cr-06.md` | 机读结果与退出码 | 齐全 | 有 | 未提供 |

截图以 `--shot-cmd` 记录捕获钩子（Edge `--headless=new`），不自行捕获、不伪造；`evidence/` 属运行时目录、不入版本库（`.gitignore`），片段可按上述命令复现。演练片段路径不含 `-real` 段，与正式提交隔离（`report_exam/index.py#L13`）。

## 4. 对象图与依赖

零 PyRIT 对象；`rehearse()` 是 `CoverageRow` / `TimelineSlot` / `Gap` / `RehearsalResult` 的唯一构造点。依赖方向、seam 与注入点见设计文档 §3–§5，不在本文件复述（C1）。

## 5. 无硬编码凭据

全包不读 `.env`、不含 API key / token / 口令字面量；演练目标仅以 `--target drill-target` 占位，真实端点凭据属 #233 的 `ready-for-human` 人工项（VG-2 取证）。
