# attack-multi-agent — 阶段 2 `to-spec ①` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.2 | `docs/specs/attack-multi-agent-spec-v1.md` 七节齐全（背景/使用者/输入/输出/约束/失败/不在范围），无文件路径与代码片段 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_multi_agent -t . -q` → Ran 57 tests, OK (skipped=1) | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B1 SKILL 五要素对齐 v1 三路径与质量门；B2 术语取 GLOSSARY「A2A／多智能体拓扑／消息操纵」条；B8 关联 issue #63、#294 | 替代（回溯） |

- 七节与 SKILL.md 执行体的对应：§5 对应三条攻击路径与收尾 flag；§6 对应「失败与豁免」六条；§2 对应 front-matter `trigger`。
- 术语核验：v1 使用「多智能体」「A2A」「消息操纵」「智能体冒充」「共享记忆投毒」「上下文投毒」，未用废弃同义词。
- 越界检查：v1 未出现 `tools/` 路径、命令行或代码块，符合「只写 What」。

**结论：PASS（回溯）**。证据指针：`docs/specs/attack-multi-agent-spec-v1.md`、`skills/attack-multi-agent/SKILL.md:1-13`；提交 `a69be85`。
