# 工程规格定稿 (v2) — OSAI 考试就绪优化

> 阶段 3 `to-spec` ② · 输入：本 issue 规格 v1 全文 + `docs/research/osai-exam-readiness-canonical.md`
> 本版把 v1 的每条 User Story 收敛为布尔验收条件；v1 不被取代，二者互链。

## 1. 验收条件（布尔，逐条可判定）

| ID | 验收条件 | 判定命令 / 人工判据 | 对应 v1 Story |
|---|---|---|---|
| AC-01 | 默认（演练）模式下，仅提供 `--shot-cmd` 的证据片段 `complete=true` 且 `shot_status=待补录` | `python -m unittest tests.shared_tools.test_collect_evidence.CollectEvidenceTests.test_shot_status_pending_when_hook_only` | S1/S7 |
| AC-02 | 考试模式下，仅提供 `--shot-cmd` 时 `complete=false`、`missing` 含「截图（真实文件）」、`--strict` 退出码 1 | 新增单测断言退出码与 `missing` | S1 |
| AC-03 | 考试模式下，提供真实 PNG（含 `IEND`）时 `complete=true`，`shot_status=已提供` | 新增单测 | S1 |
| AC-04 | 考试模式不新增、不改名、不删除任何片段节标题；golden 片段解析字段不变 | `python -m unittest tests.cross.test_contract_drift.ParseFragmentGoldenTests` | S7 |
| AC-05 | 计分目标模式下，缺少面板/截图双通道值时 `complete=false`；`--flag` 兼容形式仍判为一致 | 新增单测 | S2 |
| AC-06 | `docs/operations/osai-target-map.md` 以 8 行为最小表，逐行含目标ID/分值/类型/技能/证据路径/flag状态/报告小节/状态；不含真实 flag 值 | 行数与列断言 + grep 无 flag 值 | S2/S6/S10 |
| AC-07 | 证据管线只读目标映射、片段与清单，不为任何目标生成或补全截图/flag；缺件时输出 `BLOCKED` 与具体路径 | 新增单测：构造缺 PNG 的目标，断言退出码与非空缺口列表 | S2/S10 |
| AC-08 | 阶段状态机按固定顺序推进，交接校验失败时停留当前阶段并返回失败；不执行攻击、不联网 | 新增单测：注入失败 handoff，断言阶段未前进 | S3 |
| AC-09 | 报告预检能发现 `{{...}}` / `NOT ATTEMPTED` / `待补录` 占位，并输出所在文件与行号 | 新增单测 | S4 |
| AC-10 | 提交校验覆盖 PDF 命名、`.7z` 命名、无密码、≤100MB、仅 PDF 入档；本地 MD5 可计算且可与期望值比较 | 新增单测：正例与命名错例 | S5 |
| AC-11 | 新增校验均为独立脚本/独立步骤，不修改 CI 并发长行 | `git diff` 仅出现新增脚本与独立测试 | S8 |
| AC-12 | 新增术语数为 0；`check_glossary` 通过 | `python scripts/check_glossary.py` | S8/S10 |
| AC-13 | 全量测试通过，新增业务代码行覆盖率 ≥80% | `python -m unittest discover -s tests -t .` + coverage | S9 |
| AC-14 | 每项改动在最终报告中有需求、动作、验证命令、预期结果、实际状态五列 | 报告文件逐行核对 | S11 |
| AC-15 | 不生成任何正式提交件、真实 flag 或伪截图；演练产物均在标题或正文标注「演练」 | 全仓搜索与人工核对 | S10 |

## 2. Testing Decisions

- 只测外部行为：CLI 退出码、manifest 字段、片段文本、报告/提交判定结果。
- 使用 `tempfile` 构造假 PNG（含 `IEND`）与假片段；不复用演练证据作为测试夹具以避免污染。
- 红阶段先写失败用例并留输出；绿阶段最小改动；重构阶段复跑全量。
- `report_exam.index.parse_fragment` golden 测试作为契约不可变基线。
- 覆盖率以新增模块为分母；既有模块回归以全量测试通过为准。

## 3. 门禁映射

| 验收条件 | B1 | B2 | B3 | B4 | B5 | B6 | B7 | B8 | B9 |
|---|---|---|---|---|---|---|---|---|---|
| AC-01..05 | | ✓ | ✓ | ✓ | ✓ | ✓ | | ✓ | |
| AC-06..08 | | ✓ | ✓ | | | ✓ | | ✓ | ✓ |
| AC-09..11 | | ✓ | ✓ | | | ✓ | | ✓ | |
| AC-12..15 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

## 4. 风险与核实闸

- **R1 兼容性**：考试模式默认关闭；既有 `--strict` 语义不变，避免 17 技能回归失败（缓解：AC-01）。
- **R2 契约漂移**：任何节标题变更均视为硬违规（缓解：AC-04）。
- **R3 并发冲突**：共享文件只追加独立文件，不改长行（缓解：AC-11）。
- **R4 证据伪造**：管线只读不写；考试事实保持待核实（缓解：AC-07/AC-15）。
- **核实闸 G-1**：AC-02/03 的红阶段输出须真实存在；G-2：AC-13 全量通过方可进入代码审查；G-3：阶段 11 前 `checkout_lock --check` 必须 PASS。

## 5. v1 → v2 差异清单

1. 七节 User Stories 展开为 15 条布尔 AC，并逐条给出命令/判据。
2. 明确考试模式与演练模式并存的兼容性约束（v1 只说「保留既有演练语义」）。
3. 新增目标映射最小表结构（8 行、8 列）与「不写真实 flag」约束。
4. 新增提交校验的四项官方规则与 MD5 本地侧边界。
5. 新增三条核实闸；v1 未定义。

## 6. 结果说明

本版不取代 v1；v1 仍是行为级唯一来源。任何 AC 未满足即 `BLOCKED`，须停留原阶段重跑。
