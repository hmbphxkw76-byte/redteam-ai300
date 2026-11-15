## 变更摘要

`capstone-rehearse`（D11 / P2 / 通用验收）按主线 11 阶段落地：把 §4.5 九阶段流水线走查、§5.4 24h 节奏、缺口分级固化为可机读、可复跑的考前硬门禁。规格 v1/v2 见 #231，父工单 #233，子工单 #234–#239。

```text
cli.py → rehearse(inventory, clock, evidence_source) → RehearsalResult（唯一构造点）
  ├─ S-1 StageInventory（新）  Repo / Memory
  ├─ S-2 Clock（新）           Fixed / System
  └─ EvidenceSource（复用）    → registry.fragment_pieces（既有三件套判据）
  ├─ report.py   覆盖度矩阵 / 24h 时间线 / 缺口清单 / 演练结论
  └─ evidence.py 6 份 collect_evidence.py --step cr-NN --strict
```

零 PyRIT 依赖、纯标准库；演练片段与正式提交隔离（`-real` 过滤 + 演练标注）。

## 纳管信息（新增组件必填，CI 将据此校验）

- **组件类型**：`skill` 实现 + `文档` + `测试`（SKILL.md 已登记于 §4.4）
- **对齐能力域**：`D11` · **优先级**：`P2` · **目标计分单元**：`通用（验收）`
- **端到端演示**：`python -m tools.capstone_rehearse --stdout` → 版本化 JSON；`--emit-evidence evidence/capstone-rehearse-drill` → 6 份 `--strict` 片段；`--out r.json --report r.md` → 四件产出。默认 `ready_for_exam=false` 为如实结论，不假称全覆盖。

## Evidence

| 判据 | 改前 | 改后 |
|---|---|---|
| 覆盖度矩阵 | 无 | 九阶段 9 行，就绪四项合取 + 证据链贯通（§4.5 / AC-01/02） |
| 24h 节奏 | 无 | 四段 + 时间盒，建议/实测分字段，>24h 压缩建议（§5.3/5.4） |
| 缺口清单 | 无 | 阻断性/非阻断二档 + 补强建议（AC-09/10） |
| 演练报告 | 无 | 四件产出 + 明确判定 + VG-1…VG-6 取证方式（质量门） |
| 三件套判据 | 无 | 委托既有 `registry.fragment_pieces`（§6.1 / C1，阶段 10 修正） |
| 证据片段 | 无 | 6 份 `cr-NN --strict`，三件套 + AI 交互日志（AC-21） |
| 测试/覆盖率 | — | 新增 35 用例；全量 652 OK；新包 90.1% / all 91.2%（S2） |
| 门禁 | — | `SUMMARY passed=8 failed=0`；markdownlint 0 issues；C4 六类 PASS（S1） |

- 门禁 2–11、双轴审查见 `docs/operations/capstone-rehearse-*.md`；阶段 10 清零 2 硬违规、阶段 11 清零 1（v1 与 #231 互链，§8.3 显式声明）。
- 一手源：PyPI / GitHub API / OffSec 快照；官方无演练域与节奏表述，分段属仓库判断（§5.4「宜」）。

## Merge Danger

- **单向门**：`ready_for_exam` 默认 `false`（VG-2…VG-6 待取证）；放宽即把「未演练」写成「已通过」，破坏 §4.5 硬门禁。
- **双向门**：30 文件全 `A`、0 `M`/`D`，回滚安全；不改共享文件（ADR-0006）。
- **隔离**：演练片段落 `evidence/`（gitignore、无 `-real`），不混入正式提交；不含真实考试利用。
- **例外**：检出锁因其他 worktree 改动阻断，复判并集为空，经人工确认按 ADR-0006 例外通道推送；CI S1/S2 正常把关。

Closes #234, #235, #236, #237, #238, #239
Refs #231, #233（#233 为 `ready-for-human`，保持 OPEN 待人工最终放行）
