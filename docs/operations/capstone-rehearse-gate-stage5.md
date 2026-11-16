# 阶段 5 门禁记录 — `triage`

- 交付：#233–#239 各 1 个规范标签 · 7 条 triage 评论（6 份 agent brief + 1 份人工项清单）
- 变更：状态机 unlabeled → `needs-triage` → 目标态；brief 落 issue 评论
- 状态映射：#233 `ready-for-human`；#234–#239 `ready-for-agent`

| 编号 | 检查项 | 依据 | 实测 | 判定 | 不符合项 | 修正要求 | 复验 | 结论 |
|---|---|---|---|---|---|---|---|---|
| B8 | 标签字符串/可追溯 | §3.5 | `gh issue view --json labels` → 7/7 恰 1 个五标签之一；`check_glossary.py` PASS | 符合 | — | — | — | PASS |
| 验收① | 恰一个规范标签 | §3.5 | 脚本计数 7/7；`ready-for-human` 1 张、`ready-for-agent` 6 张 | 符合 | — | — | — | PASS |
| 验收② | brief 完整 | §3.5 | 6/6 含「目标/输入/约束/验收/验证命令」+ `AGENTS.md` C1–C8；#233 含人工项清单 | 符合 | — | — | — | PASS |
| 验收③ | 人工项一一对应 | §3.5 | #233 三项：演练目标凭据与 VG-2 取证 / 受保护 main 的 PR 合并与 CI secrets / 考前硬门禁放行（VG-5） | 符合 | — | — | — | PASS |
| 验收④ | 分类结论与理由留痕 | §3.5 | 7/7 评论含「分类结论」「理由」；7/7 含 triage disclaimer | 符合 | — | — | — | PASS |
| C4 | brief 体积 | C4 | `--artifact agent-brief` 7 次 → 741…981/1000 全 PASS | 符合 | — | — | — | PASS |
| §2.3 | 上游复核 | §2.3 | v1 7982B / v2 9984B 未变；覆盖矩阵 25/25、阻塞边无环未变 | 符合 | — | — | — | PASS |

**结论：PASS**（不符合项 0），进入阶段 6。
