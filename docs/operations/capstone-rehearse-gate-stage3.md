# 阶段 3 门禁记录 — `to-spec` ②（v2 定稿）

- 交付：`docs/specs/capstone-rehearse-spec-v2.md` · #231 v2 评论
- 变更：v2（25 AC/14 D/6 VG）；canonical 订正；v1 未改
- 不符合项 1：阶段 1 事实归属偏差/G-A 未收敛；按 §2.2-4 修正并复跑两阶段全项

| 编号 | 检查项 | 依据 | 实测 | 判定 | 不符合项 | 修正要求 | 复验 | 结论 |
|---|---|---|---|---|---|---|---|---|
| B1 | 解剖 | §4.2 | `validate_skill.py` → PASS(16) | 符合 | — | — | — | PASS |
| B2 | 术语 | §1.3 | `check_glossary.py` → PASS(50) | 符合 | — | — | — | PASS |
| B6 | CI | S1–S4 | `check_token_budget.py --check` → PASS | 符合 | — | — | — | PASS |
| B7 | PyRIT | §2.1 | canonical §5 交叉验证；AC-23；实现侧旧名 0 | 符合 | 版本归属偏差 | §5 订正 + G-F；重跑全项 | PASS | PASS |
| B8 | 追溯 | B8 | D1–D14、VG-1…6 带取证方式；§5 附官方 URL | 符合 | G-A 未收敛 | VG-1 关闭 + D14 | PASS | PASS |
| 验收① | US→AC | §3.3 | 32/32 US 覆盖，25 AC | 符合 | — | — | — | PASS |
| 验收② | AC 判据 | §3.3 | 每 AC 第 4 列为命令/夹具/人工判据 | 符合 | — | — | — | PASS |
| 验收③ | 核实项 | §3.3 | G-A 关闭；G-B…G-F → VG-2…6 带取证方式 | 符合 | — | — | — | PASS |
| 验收④ | 差异 | §3.3 | D1–D14 逐条 + 理由 | 符合 | — | — | — | PASS |
| 验收⑤ | 单活版本 | §3.3 | 「活版本=v2」+ v1 保留 + #231 互链 | 符合 | — | — | — | PASS |
| 验收⑥ | 版本递增 | §3.3 | v1 7982B(US) vs v2 9984B(AC) | 符合 | — | — | — | PASS |
| C4 | 体积 | C4 | `--artifact spec-v2` → 9984/10000 | 符合 | 首轮 11795 BLOCKED | 压缩叙述，AC/D/VG 全留 | PASS | PASS |
| §2.3 | 上游复核 | §2.3 | v1 7982B/32 US 未变；canonical 门禁 1851B | 符合 | 见 B7/B8 | 同上 | PASS | PASS |

**结论：PASS**（不符合项 1，已闭环），进入阶段 4。
