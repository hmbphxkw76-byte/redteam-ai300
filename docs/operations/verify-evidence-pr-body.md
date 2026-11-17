## 变更摘要

`verify-evidence` 按主线 11 阶段落地（规格 #204，父工单 #205）：把 GOVERNANCE §8.2 八项检查单从「标题存在性 + 布尔字段」升级为**可机读、可回归**的九项判据，并逐条对齐 `skills/verify-evidence/SKILL.md`（覆盖矩阵见 `docs/operations/verify-evidence-skill-coverage.md`）。

```text
tools/verify_evidence.py  S-1 输入归一 → S-2 九项判据 → S-3 可注入工具链 → S-4 版本化输出
  ├─ --from-loot loot/registry.md   登记簿 + 报告
  ├─ --fragments-dir <dir>          一批 collect_evidence 片段
  ├─ --payload <json>               report-exam 载荷（提交前置，路径未变）
  └─ --no-artifacts                 dry-run → 核实闸，永不标记可提交
```

## 纳管信息

- **组件类型**：`skill` + `流水线`（覆盖率目标注册）
- **对齐能力域**：`D11` · **优先级**：`P0` · **目标计分单元**：`通用`
- **端到端演示**：`python tools/verify_evidence.py --from-loot <reg> --report <md> --no-artifacts --summary` → 机读 JSON + 人读摘要；CI 由 `report-toolchain.yml` 断言 `verify-evidence: passed`

## Evidence

| 判据 | 改前 | 改后 | 依据 |
|---|---|---|---|
| vrf-01 | 仅查 OSID/版权 | 追加 `validate_skill.py` 终检 | §4.2 |
| vrf-02 | 章节标题存在性 | 高杠杆技能不得 P2（ADR-0002）+ 8 目标/分值 100 | §4.3 / §2.2 |
| vrf-03 | payload 布尔字段 | 委托登记簿 `fragment_pieces` | §6.1 / C1 |
| vrf-04 | 仅面板值 | 追加访问证明（只读截图节内联文本） | §6.2.2 |
| vrf-07 | 命名/体积 | 追加 24h 窗口（硬阻断）+ 归档加密 | §6.4.2/§6.4.3 |
| proof-single | flag 子串匹配 | 按 `domain-controller` 键 | §2.2.3 |
| 键集 | 两侧各写一份 | `tools/scored_targets.py` 唯一源 | C1 |

- 测试：`tests/shared_tools/test_verify_evidence.py` 10 → 32 用例；全量 `Ran 578 tests, OK`
- 覆盖率：`measure_coverage.py --target verify-evidence` → 92.1%（门槛 80）
- 本轮补齐：脚本直跑 `ModuleNotFoundError`（SKILL 文档写法本身不可用）、vrf-02 优先级漏判、`--fragments-dir` 缺入口、NOTE-9/10 人工判据留痕
- 文档：规格 v1/v2、调研、设计、双轴审查、SKILL 覆盖矩阵、阶段门禁 2–11

## Merge Danger

- **单向门**：`proof-single` 改按目标键判定，回退会让「flag 含 `proof.txt` 子串」重新误计。影响半径：`tests/test_report_exam.py::test_AC09`（夹具已对齐）、任何消费 `verify()` 返回结构的外部脚本（`schema_version` 为向后兼容扩增）。
- **双向门**：其余判据均为收紧/补齐，回滚安全。
- 共享文件：`scripts/measure_coverage.py`（新增 target，纯增量）、`GLOSSARY.md`（+12 行、0 删除，16442/16500 字节，余量极小）。

跟进：J-1/J-2 → #225。

Closes #204, #205, #206, #207, #208, #209, #210, #212
