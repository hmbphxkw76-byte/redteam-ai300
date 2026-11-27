# attack-multi-agent — 阶段 7 `domain-modeling` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.7 | `GLOSSARY.md` 增补 A2A 术语块：`A2A`、`多智能体拓扑`、`消息操纵`、`智能体冒充`、`共享记忆投毒`、`上下文投毒` | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_multi_agent -t . -q` → Ran 57 tests, OK (skipped=1) | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B2 `python scripts/check_glossary.py` 通过，技能文本无 `_Avoid_` 废弃同义词；B8 关联 issue #195、PR #203 | 替代（回溯） |

- 术语映射：SKILL 步骤 ID ↔ 术语条一一对应（a2a-02 消息操纵、a2a-03 智能体冒充、a2a-04 共享记忆投毒、a2a-05 上下文投毒）。
- 归一动作：统一使用「多智能体」「A2A」，未使用「agent 集群」等非规范表述。
- ADR 核对：无新增 ADR 需求，术语块与既有 ADR 无冲突，故未标注冲突项。

**结论：PASS（回溯）**。证据指针：`GLOSSARY.md:125-142`、`docs/operations/attack-multi-agent-design.md:120`；提交 `a69be85`。
