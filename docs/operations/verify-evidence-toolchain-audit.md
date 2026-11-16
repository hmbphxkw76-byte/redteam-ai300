# verify-evidence — SKILL 点名工具链逐一核对（终检）

> 核对时间 2026-11-15 · 基线 `origin/main` + PR #241 修复 · 逐条「存在 / 接线 / 实跑」三维判定。
> 对照源：`skills/verify-evidence/SKILL.md`（86 行，含 front-matter 七字段）。

## 1. SKILL 点名的 tool / 命令模板

| SKILL 条款 | 点名的 tool / 命令 | 实现位置（单一事实源） | 实测 | 判定 |
|---|---|---|---|---|
| 执行入口 | `tools/verify_evidence.py --payload` | `main()` → `load_payload` | CLI exit 0 / `passed=true` | 已实现 |
| 执行入口 | `--from-loot loot/registry.md` | `from_loot` → `registry.parse_registry` / `parse_dual`；报告侧取片段双通道表；状态列参与已取分判定 | 登记簿夹具实跑 exit 0 | 已实现（#225 收口） |
| 执行入口 | `--fragments-dir <dir>` | `from_fragments` → `registry.fragment_pieces` + `_fragment_dual` | `test_AC01g` CLI 真跑 exit 0 | 已实现（本次修复） |
| vrf-01 | `python scripts/validate_skill.py` | `Toolchain.validate_skills` | PASS 16 技能 | 已实现 |
| vrf-02 | §4.3 / ADR-0002 评分杠杆 | `check_vrf02` → `Toolchain.skill_meta` + 分值多重集 | 16 技能 0 失配；缺目标即阻断 | 已实现 |
| vrf-03 | `grep -c '#### 确切命令' loot/<host>-*.md` | `registry.fragment_pieces`（判据唯一源，不另写正则） | AC-05 / AC-17 回归通过 | 已实现 |
| vrf-04 | `diff <(面板值) <(报告值)` | `check_vrf04` 逐字比对；面板值来自 `parse_dual` / `_fragment_dual` | 一致通过、不一致阻断 | 已实现 |
| vrf-04 续 | 截图 `whoami`/`id` + flag 同屏 | `_access_proof` / `_screenshot_section` | 文本型机判；纯图片 → `NOTE-7` | 部分实现（人工边界已声明） |
| vrf-05 | AI 交互入附录（§6.3） | `check_vrf05` 逐字包含 | 缺日志阻断；§5.5 标注 → `NOTE-9` | 部分实现 |
| vrf-06 | 四章 + 每主机五段式（§7.1/7.2） | `check_vrf06` 8 锚点；五段式 → `NOTE-10` | 逐锚点删除法回归通过 | 部分实现 |
| vrf-07 | `7z l -slt … \| grep Encrypted` / `ls -l *.7z` | `Toolchain.archive_encrypted` / `stat` / `check_naming_and_size` | 命名/体积/密码三态；无 7z → `NOTE-8` | 已实现 |
| vrf-07 续 | 24h 提交窗口（§6.4.3） | `_check_window`（注入时钟） | 超窗阻断；时间缺失 → `NOTE-5` | 已实现 |
| vrf-08 | `python scripts/check_glossary.py` | `load_avoid_terms` 动态取 GLOSSARY（同源） | PASS 50 废弃术语 | 已实现 |
| 域控约束 | `proof.txt` 单次（§2.2） | `check_proof_single`（按 `domain-controller` 键） | >1 阻断；0 记 VG-4 豁免 | 已实现 |
| 输入 | `loot-manage` 登记簿 | `tools/loot_manage/registry.py` | `parse_dual` / `fragment_pieces` 复用 | 已实现 |
| 输入 | 各技能 `collect_evidence.py` 片段 | `tools/collect_evidence.py`（生产端）/ `from_fragments`（消费端） | 真实片段生成 + 三入口消费实跑 | 已实现 |
| 输出前置 | `report-exam` 提交动作（§7.3） | `report_exam/package.py::package` 取 `submission_ready` | AC-18 委托回归通过 | 已实现 |
| CI 复用 | 机读结果 / 退出码 | `ci.yml` S1/S2、`report-toolchain.yml#L92` | PR S1/S2 + AC-12 冒烟 pass | 已实现 |
| 覆盖率 | 业务代码 ≥80% | `scripts/measure_coverage.py --target verify-evidence` | 92.3%（503/545） | 已实现 |
| 术语基准 | `GLOSSARY.md` | `scripts/check_glossary.py` | PASS（50 术语） | 已实现 |
| S1-only | 不新增 S2 证据契约夹具 | 无 `test_verify_evidence_evidence_contract.py` | 32→37 用例均为 AC 用例 | 已实现 |

## 2. 本次终检发现并修复的真实缺口

1. `--fragments-dir` 未读片段自带双通道明细表 → 含 flag 片段必触发 `vrf-04` 阻断。修复：面板值归一进 `panel_flags`、报告侧取「截图/正文中的值」、缺通道仍阻断、显式注入优先。
2. 跟进 issue **#225**（阶段 10 判断项 J-1/J-2）原为 OPEN，本次一并收口：J-1 `from_loot` 面板值自比 → 报告侧改取片段双通道表（无表时回退取证节 / 面板值）；J-2 已取分判定未消费登记簿「状态」列 → 新增 `taken`（状态「失效」不计已取分），并使主机级「未达成」记录与 `_scored` 同源。新增 `test_AC21` / `test_AC22` 两条验收用例，满足 #225 的「登记簿与报告 flag 不一致 → 阻断」。

## 3. 判定

- SKILL 25 条规范条款：**20 已实现 / 5 部分实现 / 0 未实现**。5 条部分实现均为 SKILL 已显式声明的人机边界（三处人工判据 + proof 口径修订 + 由此产生的「非全部机读」），非功能缺失；`NOTE-6/7/9/10` 均有回归用例锁定。
- 三入口实跑：payload / from-loot / fragments-dir 全通过。全量 **624 tests OK**，覆盖率 **92.6%（511/552）**，`tests.test_verify_evidence` **39 用例**。
- 未做范围外事项：截图 OCR、报告结构解析（SKILL「校验标准」显式排除）。
