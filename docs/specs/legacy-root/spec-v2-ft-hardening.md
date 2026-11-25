## 工程规格定稿 (v2) — foothold-traditional Ch9 A3/C2 加固

> 取代关系：本文为 issue #370 规格 v1 的工程定稿，v1 全文保留；差异见文末。

### 验收条件（布尔化）

| ID | 布尔验收条件 | 检查命令/判据 | Ch9 |
|---|---|---|---|
| AC-01 | 响应含 `AWS_ACCESS_KEY_ID`/`AWS_SECRET_ACCESS_KEY`/`AWS_SESSION_TOKEN` 三键 → `TriadVerdict.outcome=EXPOSED_NO_AUTH`，`fingerprints` 恰 3 条且只含(键名,长度,位置) | 单测断言 | L1-2 |
| AC-02 | 响应无 AWS 凭据键名 → `ABSENT` 且 `reason=none_found` | 单测 | — |
| AC-03 | 凭据值（如 `AKIAEXAMPLE...`）不出现在 `verdict.output` 与任何 fingerprint 字段 | 单测 + grep 明文 | P-1 |
| AC-04 | `GetCallerIdentity` 返回含 `Arn` → `EXPLOITED`；返回非 2xx 或 deny → 不夸大，保持 `EXPOSED_NO_AUTH` | 单测两分支 | L1/H-2 |
| AC-05 | `sudo -l` 含 `(root) NOPASSWD: /path/script` → `EXPOSED_NO_AUTH` 且 `wrappers` 含该路径 | 单测 | L56-63 |
| AC-06 | 无 NOPASSWD → `ABSENT(none_found)`；命令 127 → `ABSENT(no_tool)` | 单测两分支 | — |
| AC-07 | `TriadVerdict.outcome` 取五值之一；ABSENT/BLOCKED 的 reason 属既有枚举 | 单测断言 | C8 |
| AC-08 | 每个 verdict 可生成 `collect_evidence.py --step <id> --cmd --output --shot-cmd --strict` 参数列表；strict 非零 → `evidence_ok=False` 且记录 error | 单测 + CLI 参数断言 | H-6 |
| AC-09 | 每步命令可直接 copy/paste，不含 shell=True、不含未参数化拼接 | 源码 grep + 单测 | C8 |
| AC-10 | `tools/foothold_traditional/` 全部模块行覆盖率 ≥90% | `python scripts/verify_ch9_ft_coverage.py --min 90` | 本轮门槛 |
| AC-11 | SKILL.md 引用的每个工具/模块/函数名在字面存在（`ch9_entry.py`、`TriadVerdict`、`emit_strict_evidence` 等） | `python scripts/verify_skill_refs.py` 逐条断言 | 收口要求 |
| AC-12 | 既有 trad-01..08 判据、证据契约测试、全量测试零回归 | 全量 unittest + diff 核对 | §2.3 |

### 测试决策
- 只断言外部行为；FakeCommand 离线覆盖 10 条路径；证据 CLI 参数以列表断言。
- 覆盖率 tracer 复用 `scripts/measure_coverage.py#executable_lines/measure`，不复制 tracer 逻辑（C1）。

### 门禁映射
AC-01..09 → 单测（S2）；AC-10 → 覆盖率脚本；AC-11 → 引用核验脚本；AC-12 → 全量 unittest + diff；全部 → B1/B2/B7/B8 + C4 预算。

### 风险闸
- R-1：`/api/export?template_url` 参数名属课程源，按 Listing 1 字面编码，标"课程源，非 AWS 公开 API"；不阻断。
- P-4：GPU 提权本体不在此技能；只判立足点，标指针引用；不阻断。

### v1→v2 差异
1. 10 条 User Stories 收敛为 12 条布尔 AC；2. 补门禁映射与覆盖率脚本命令；3. AC-11 明确 SKILL.md 引用逐条核对；4. 明确 R-1/P-4 为核实闸不阻断；5. AC-10 门槛由 CI 全局 80% 抬至本技能 ≥90%。
