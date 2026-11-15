## 变更摘要

`verify-evidence` 按主线 11 阶段落地（规格 issue #204，父工单 #205）：把 GOVERNANCE §8.2 八项检查单从「标题存在性 + 布尔字段」的启发式升级为**可机读、可回归**的九项判据，并补齐四类真实缺口（技能终检、分值口径、访问证明同屏、24h 窗口）。

```text
tools/verify_evidence.py   S-1 输入归一 → S-2 九项判据 → S-3 可注入工具链 → S-4 版本化输出
  ├─ --from-loot loot/registry.md     （直读登记簿双通道与片段，复用 loot_manage 判据）
  ├─ --payload  report_exam 载荷      （report-exam 提交前置，路径未变）
  └─ --no-artifacts                   （dry-run → 核实闸，永不标记可提交）
```

## 纳管信息

- **组件类型**：`skill`（`verify-evidence`）+ `流水线`（覆盖率目标注册）
- **对齐能力域**：`D11`
- **优先级**：`P0`
- **目标计分单元**：`通用`
- **端到端演示**：`python tools/verify_evidence.py --from-loot loot/registry.md --summary` → 机读 JSON + 人读摘要；CI 由 `report-toolchain.yml` 断言 `verify-evidence: passed`

## Evidence

| 判据 | 改前 | 改后 | 依据 |
|---|---|---|---|
| vrf-01 | 仅查报告内 OSID/版权 | 追加 `validate_skill.py` 终检（可注入） | §4.2 |
| vrf-02 | 章节标题存在性 | 8 目标键集 + 分值多重集 + 合计 100 | §2.2 / ADR-0002 |
| vrf-03 | payload 布尔字段 | 有原文时委托登记簿 `fragment_pieces` | §6.1 / C1 |
| vrf-04 | 仅面板值比对 | 追加访问证明同屏（`whoami`/`id` + flag） | §6.2.2 |
| vrf-07 | 命名/体积 | 追加 24h 窗口（硬阻断）与归档加密判定 | §6.4.2 / §6.4.3 |
| proof-single | flag 值子串匹配 | 按 `domain-controller` 目标键 | §2.2.3 |
| 键集 | 两侧各写一份 | `tools/scored_targets.py` 唯一事实源 | C1 |

- 测试：`tests/test_verify_evidence.py` 10 → 29 用例（AC-01…AC-18 逐条覆盖 + 键集单一事实源）；全量 `Ran 521 tests, OK`
- 覆盖率：`measure_coverage.py --target verify-evidence` → 92.3%（门槛 80）
- 文档：规格 v1/v2、调研、设计、9 份阶段门禁记录、术语表 4 条

## Merge Danger

- **单向门**：`proof-single` 判定口径变更后不可回退——回退会让「flag 值含 `proof.txt` 子串」重新误计。影响半径：`tests/test_report_exam.py::test_AC09`（夹具已对齐）、任何引用 `verify_evidence.verify()` 返回结构的外部脚本（新增 `schema_version` 键为向后兼容扩增）。
- **双向门**：其余判据均为收紧/补齐，回滚安全。
- 共享文件改动：`scripts/measure_coverage.py`（新增 `verify-evidence` 目标）与 `GLOSSARY.md`（4 条术语，14995/15000 字节，余量极小，后续新增术语须先压缩）。

跟进：J-1/J-2 → #225。

Closes #204, #205, #206, #207, #208, #209, #210, #212
