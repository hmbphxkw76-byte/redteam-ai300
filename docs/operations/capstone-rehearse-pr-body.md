## 变更摘要

`capstone-rehearse`（D11 / P2 / 通用验收）按主线 11 阶段落地：把 `GOVERNANCE.md` §4.5 的九阶段流水线走查、§5.4 24h 节奏、缺口分级固化为**可机读、可复跑、可交接**的考前硬门禁。规格 v1/v2 见 issue #231，父工单 #233，子工单 #234–#239。

```text
tools/capstone_rehearse/cli.py
  └─ rehearse(inventory, clock, evidence_source) → RehearsalResult（唯一构造点）
       ├─ S-1 StageInventory（新）  RepoStageInventory / MemoryStageInventory
       ├─ S-2 Clock（新）           FixedClock / SystemClock
       └─ EvidenceSource（复用）     DirEvidenceSource / MemoryEvidenceSource
                                      └─ registry.fragment_pieces（既有三件套判据）
  ├─ report.py      → 覆盖度矩阵 / 24h 时间线 / 缺口清单 / 演练结论
  └─ evidence.py    → collect_evidence.py --step cr-NN --strict（6 份）
```

本技能零 PyRIT 依赖、纯标准库；演练片段与正式提交隔离（`-real` 过滤 + 演练标注）。

## 纳管信息（新增组件必填，CI 将据此校验）

- **组件类型**：`skill` 实现 + `文档` + `测试`（未新增 SKILL.md，已登记于 §4.4）
- **对齐能力域**（D1–D11）：`D11` · **优先级**：`P2` · **目标计分单元**：`通用（验收）`
- **端到端演示**：`python -m tools.capstone_rehearse --stdout` → 版本化 JSON；`python -m tools.capstone_rehearse --emit-evidence evidence/capstone-rehearse-drill` → 6 份 `--strict` 三件套片段；`python -m tools.capstone_rehearse --out r.json --report r.md` → 四件产出报告。默认 `ready_for_exam=false` 为如实结论（演练取证未完成），不假称全覆盖。

## Evidence

| 判据 | 改前 | 改后 | 依据 |
|---|---|---|---|
| 覆盖度矩阵 | 无 | §4.5 九阶段 9 行，就绪四项合取 + 证据链贯通 | §4.5 / AC-01/02 |
| 24h 节奏 | 无 | 四段 + 诱饵机时间盒，建议/实测分字段，>24h 压缩建议 | §5.3/§5.4 / AC-05…08 |
| 缺口清单 | 无 | 阻断性/非阻断二档 + 补强建议 | AC-09/10 |
| 演练报告 | 无 | 四件产出 + 明确判定 + VG-1…VG-6 取证方式 | 质量门 / AC-11/17 |
| 三件套判据 | 无 | 委托既有 `registry.fragment_pieces`（阶段 10 硬违规修正） | §6.1 / C1 |
| 证据片段 | 无 | 6 份 `cr-NN --strict`，三件套 + AI 交互日志 | §6.1/§6.3 / AC-21 |
| 测试/覆盖率 | — | 新增 35 用例；全量 `Ran 652 tests OK`；新包 90.1%、`--target all` 91.2% | S2 / AC-22 |
| 门禁 | — | `SUMMARY passed=8 failed=0 total=8`；markdownlint 141 文件 0 issues；C4 六类 PASS | S1 |

- 阶段 1–11 门禁记录：`docs/operations/capstone-rehearse-gate-stage2..11.md`；双轴审查见 `capstone-rehearse-code-review.md` 与 `capstone-rehearse-pre-push-review.md`
- 阶段 10 清零 2 项硬违规（MD012、`_chain` 判据复用）；阶段 11 pre-push 清零 1 项硬违规（v1 与 issue #231 互链，按 §8.3 显式声明格式修正）
- 一手源核实：PyPI / GitHub API / OffSec 官方指南快照；官方无 Capstone 演练域与节奏分段表述，分段属仓库工程判断（§5.4「宜」）

## Merge Danger

- **单向门**：`ready_for_exam` 默认 `false`（核实闸 VG-2…VG-6 待取证）。若后续放宽为默认通过，将直接把「未演练」写成「已通过」，破坏 §4.5 考前硬门禁；影响半径：演练结论、PR 合并后的考前放行判定。
- **双向门**：其余均为纯新增（30 文件全 `A`、0 `M`/`D`），回滚安全；不修改 `GLOSSARY.md`、`ci.yml`、校验脚本等共享文件（ADR-0006）。
- **隔离**：演练片段落在 `evidence/`（`.gitignore`，不入库、路径不含 `-real`），不会混入正式提交；本 PR 不含真实考试利用。
- **例外说明**：pre-push 检出锁因其他 worktree 的共享文件改动而阻断；按各 worktree HEAD 复判并集为空（本 PR 未触碰共享文件），经人工确认按 ADR-0006 例外通道推送，CI S1/S2 仍正常把关。

Closes #234, #235, #236, #237, #238, #239
Refs #231, #233（#233 为 `ready-for-human`，保持 OPEN 待考前硬门禁人工最终放行）
