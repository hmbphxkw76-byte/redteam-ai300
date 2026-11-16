# 阶段 8 门禁记录 — `implement-spec`

- 交付物：`tools/tooling_automate/`（manifest/runner/reuse/summary/cli/__init__/__main__）；`measure_coverage.py` 注册目标
- 工单：#243/#244/#245/#246（S-1 唯一 seam）；#247→#248 证据契约

| 编号 | 检查项 | 依据 | 实测（命令 + 摘要） | 结论 |
|---|---|---|---|---|
| B1 | 解剖 | §4.2 | `validate_skill.py` → PASS（16 技能） | PASS |
| B2 | 术语 | §1.3 | `check_glossary.py` → PASS（51 废弃术语） | PASS |
| B3 | 语法构建 | B3 | `py_compile tools/tooling_automate/*.py` → OK；`check_token_budget.py --check` → PASS（14 锚点） | PASS |
| B4 | 证据契约 | §6.1 | 编排层不自产片段，仅透传 `collect_evidence.py --step <prefix>-NN --strict`；契约由 `test_tooling_evidence_contract` 断言（豁免：新增编排件，不新增 S2 夹具） | PASS |
| B5 | 证据 flag | §6.2 | 纯编排工具，不接触 flag/访问证明；复用既有校验结论，无 mock 比对 | PASS |
| B7 | 零 PyRIT | ADR-0004 | `test_no_pyrit_import`/`test_no_third_party` → 无 pyrit/requests/httpx/pandas | PASS |
| B8 | 可追溯 | B8 | 模块 docstring 标切片 A–D；#240/#242 互链 | PASS |
| AC 对位 | 逐条落点 | §3.8 | 01→EXPECTED_FIELDS；02→is_manual；03→compute_coverage；04→run_plan；05→strict argv；07→parse_step；08→CommandRunner；09/10→render_markdown；12→STEP_RE；13→dry_run；14→SubprocessRunner；17→exit_code；20→覆盖 89.6% | PASS |
| 凭据 | 无硬编码 | B5 | 全文无 token/密码字面量 | PASS |

__红→绿自检__：首轮 27 例 5 失败/3 错误（helper 返 dict 非 Task、argv 取位错、step 正则单 digit、断言裸文件名），均测试侧偏差；按 v2 修正后 27/27 通过，断言未放宽。

__结论：PASS__（不符合项 0），进入阶段 9（`tdd`）。
