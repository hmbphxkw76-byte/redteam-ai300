# 阶段 8 门禁记录 — `implement-spec`

- 交付：`tools/capstone_rehearse/` 8 模块 + 契约测试 + `implementation.md` +6 片段
- 不符合项 1：契约断言不符 → 1 failure；已修正重跑全项

| 编号 | 检查项 | 依据 | 实测 | 判定 | 不符合项 | 修正要求 | 复验 | 结论 |
|---|---|---|---|---|---|---|---|---|
| B1 | 解剖 | §4.2 | `validate_skill` → PASS(16) | 符合 | — | — | — | PASS |
| B2 | 术语 | §1.3 | `check_glossary` → PASS(50) | 符合 | — | — | — | PASS |
| B3 | 语法/构建 | §2.1 | `py_compile` 9 文件 OK；unittest → 621 OK(skip2) | 符合 | 1 failure | 改断言；重跑全量 | OK 621 | PASS |
| B4 | 证据契约 | §2.1 | 6 份 `--strict` 三件套齐全+AI日志；契约测试 4 例 OK | 符合 | — | — | — | PASS |
| B5 | 证据/flag | §2.1 | 双通道「否/未提供」不伪造；演练域无 flag | 符合 | — | — | — | PASS |
| B7 | PyRIT | §2.1 | 扫描 `import pyrit`/旧名 → 0 | 符合 | — | — | — | PASS |
| B8 | 追溯 | B8 | 矩阵 25 AC→位置；报告 4 锚点；#233 互链 | 符合 | — | — | — | PASS |
| 验① | AC 有实现 | §3.8 | 矩阵 25/25 | 符合 | — | — | — | PASS |
| 验② | py_compile | §3.8 | 9 文件 OK | 符合 | — | — | — | PASS |
| 验③ | 对象图 B7 | §3.8 | 零 PyRIT；`rehearse()` 唯一构造点 | 符合 | — | — | — | PASS |
| 验④ | 每步三件套 | §3.8 | cr-01…06 各 1/1/1/1，strict 6/6 | 符合 | — | — | — | PASS |
| 验⑤ | 无硬编码凭据 | §3.8 | grep key/secret/password/token → 0 | 符合 | — | — | — | PASS |
| 验⑥ | 变更清单 | §3.8 | #234–#239 ↔ 8 模块 + 1 测试 | 符合 | — | — | — | PASS |
| C4 | 预算 | C4 | `--check` → PASS | 符合 | — | — | — | PASS |
| §2.3 | 上游复核 | §2.3 | v1 7982B/32 US、v2 9984B 未变 | 符合 | — | — | — | PASS |

**结论：PASS**（不符合项 1，已闭环），进入阶段 9。
