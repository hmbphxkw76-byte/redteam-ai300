# verify-evidence — 工程规格 v2（定稿 · 可验证性收敛）

> **阶段**：主线 阶段 3 `to-spec` ②（工程规格定稿）
> **输入**：v1（`docs/specs/verify-evidence-spec-v1.md` / issue #204 正文）、`docs/research/verify-evidence-canonical.md`（缺口 G1–G7、核实闸 VG-1–VG-4）、`docs/standards/CI-CD.md` v1.1
> **性质**：v1 保留全文不动，本文件只做「可验证 / 可拆解 / 可交接」收敛；活版本见 issue #204 的 `## 工程规格定稿 (v2)` 评论。

---

## 1. 布尔验收条件（AC，逐条可判定）

| AC | 对应 US | 验收条件（布尔） | 判定方式 |
|---|---|---|---|
| AC-01 | US-01/02/03 | 同一信息集下 `--payload <json>` 与 `--from-loot <registry>`（含 `--report`/`--appendix`）两入口 `checks` 逐键相等；只给登记簿不给报告时报告侧判据必然阻断 | `unittest` 断言字典相等 + 反例 |
| AC-02 | US-04 | 载荷文件不存在 / JSON 非法 / 登记簿路径不存在 → 退出码 2 且 stdout 无 `passed` 字段 | `python -m unittest tests.test_verify_evidence` |
| AC-03 | US-05 | 注入的假技能校验器返回错误列表非空 → `vrf-01=false` 且 `blocking` 含 `vrf-01`；返回空 → `vrf-01=true` | 注入替身 + 断言 |
| AC-04 | US-06 | 8 目标键集齐全且分值合计 == 100（AI 15/传统 10/独立 15/域控 5）→ `vrf-02=true`；缺目标或合计≠100 或单目标分值错 → `false`，`blocking` 指名目标键 | 夹具矩阵逐项断言 |
| AC-05 | US-07 | 已取分步骤缺三件套任一 → `vrf-03=false` + `blocking`；未取分步骤缺件 → 仅入 `missing`，`passed` 不受影响 | 断言 `checks`/`missing` |
| AC-06 | US-08 | 面板值 == 报告值（逐字）→ `vrf-04=true`；缺面板值或不等 → `false` + `blocking` | 两组夹具 |
| AC-07 | US-09 | 访问证明文本取自「截图」节内联记录或显式 `access_proof` 字段（命令块不参与）：含 `whoami`/`id` 且 flag 同屏 → 通过；有无同屏文本但缺 token → 阻断；纯图片无内联文本 → 记 `NOTE-7` 人工判据 | 三类夹具 |
| AC-08 | US-10 | 片段 AI 日志逐字出现在附录 → `vrf-05=true`；有日志而附录缺 → `false` + `blocking` | 两组夹具 |
| AC-09 | US-11 | 四章必需品与锚点齐全 → `vrf-06=true`；缺任一 → `false` 且 `blocking` 指明缺失锚点 | 逐锚点删除法 |
| AC-10 | US-12 | 命名合规 + 归档无密码 + ≤100MB → `vrf-07=true`；命名错/超 100MB/产物缺失/已加密 → `false` + `blocking`；无 7z 致密码态不可判 → 记 `NOTE-8` | 临时目录夹具 + 注入加密态 |
| AC-11 | US-13 | `submit_at - exam_end_at ≤ 24h` → 通过；超窗或时间戳非法/倒序 → `false` + `blocking`（硬性）；两者缺失 → 记 `NOTE-5` 人工判据 | 注入固定时间戳 |
| AC-12 | US-18 | `--no-artifacts` 时 `checks['vrf-07'] is None`、`pending` 含 `VG-3`、`submission_ready=false`，且 `passed` 不受影响 | 断言三值 |
| AC-13 | US-14 | 废弃术语出现在叙述正文 → `vrf-08=false`；仅出现在证据区间 → `true` | 两组夹具 |
| AC-14 | US-15 | 域控目标 flag 记录数 ≤1 → `proof-single=true`；≥2 → `false` + `blocking`；判定按目标键（`domain-controller`），非 `flag` 值子串匹配 | 含「flag 值含 proof.txt 子串」反例夹具 |
| AC-15 | US-16/17 | 输出 JSON 含 `schema_version`、`checks`（`vrf-01`…`vrf-08`、`proof-single` 共 9 键）、`blocking`、`missing`、`pending`、`failed_checks`、`passed`、`submission_ready`；缺任一键即失败 | 键集断言 |
| AC-16 | US-16 | 退出码与 `passed` 一致：通过 0 / 阻断 1 / 用法错误 2；人读摘要含阻断数与缺失数 | CLI 三态夹具 |
| AC-17 | US-01 | 三件套判定复用登记簿既有实现（以替身断言被调用），本技能不另立判据 | 替身调用计数 |
| AC-18 | US-19 | `report_exam` 委托调用不破：真实构建日志含 `verify-evidence: passed` | `report-toolchain.yml` 断言 |
| AC-19 | — | 业务代码行覆盖率 ≥80% | `scripts/measure_coverage.py` |
| AC-20 | — | 全量 `unittest` 通过（0 失败 0 错误） | `python -m unittest discover -s tests` |

**冲突处理**：AC 之间无互斥；AC-12 与 AC-16 的 `passed` 语义一致（`pending` 不计阻断）。

## 2. Testing Decisions

1. **只测外部行为**：断言单位是「输入 → `checks` 布尔表 / `blocking` / `missing` / `pending` / 退出码」，不断言私有函数调用顺序。AC-17 的替身计数是唯一例外，理由是「判据单一事实源」本身是验收对象。
2. **替身边界**：技能校验器、术语检查器、文件系统 stat、时钟四类经注入点替换；不 mock 标准库 `json`。
3. **夹具组织**：以 `TemporaryDirectory` 构造「合规包 / 每 AC 一个不合规包」，复用既有 `tests/test_verify_evidence.py` 的构造器风格（`payload()` / `frag()`），新增 `loot` 文本夹具与假时钟。
4. **红—绿—重构**：每条 AC 先写失败用例（红）并保留输出摘要，再最小改动转绿，最后重构复跑。
5. **既有参考测试**：`tests/test_verify_evidence.py`（10 用例，全部保留且必须继续通过）、`tests/test_report_exam.py`（委托调用回归）、`tests/test_loot_manage.py`（三件套判据同源回归）。
6. **不新增 S2 证据契约夹具**：本技能不产生 per-step 攻击证据（S1-only），S2 覆盖即本文件的 AC 用例集。

## 3. CI 门禁映射

| AC | CI 阶段 | 落地检查 |
|---|---|---|
| AC-02/05/06/07/08/09/10/11/12/13/14/15/16/17 | S2 | `python -m unittest discover -s tests` |
| AC-01/03/04 | S2 | 同上（含注入替身用例） |
| AC-19 | S2 | `scripts/measure_coverage.py`，门限 80 |
| AC-18 | S3 构建链（`report-toolchain.yml`） | `grep -q "verify-evidence: passed"` |
| AC-20 | S1 + S2 | `py_compile` + unittest 全量 |
| 全 AC | S1 | `validate_skill.py`、`check_glossary.py`、`check_token_budget.py --check` |

## 4. 收敛决策（对象图与 seam）

- **seam 不变**：S-1…S-4 四处（v1 §4 已确认），v2 只固定其输入输出形状：S-1 产出统一输入字典；S-2 每判据返回 `(ok, blocking, missing, pending)` 四元组；S-3 为可注入工具链对象；S-4 输出 `schema_version` 版本化的 JSON + 摘要文本。
- **模块边界**：保持单模块路径（CI `py_compile` 与 `report_exam/package.py` 已按该路径接线），内部按 S-1…S-4 分层，不为分层新增包目录（避免改动 CI 与下游加载路径）。
- **PyRIT**：零依赖不变（B7 判定形式为「无 `pyrit` import」）。

## 5. v1 → v2 差异清单

| # | v1 表述 | v2 收敛 | 理由 |
|---|---|---|---|
| 1 | US-12/13 合并描述命名与体积 | 拆为 AC-10（命名/体积）与 AC-11（24h 窗口） | 24h 为硬性自动不及格项，须独立判定 |
| 2 | 「复用登记簿既有实现」（软表述） | AC-17：替身断言被调用 | 让「单一事实源」可验证 |
| 3 | 未定义输出结构 | AC-15：9 键 + `schema_version` | CI 消费需稳定契约 |
| 4 | proof 单次「按 flag 记录数」 | AC-14：按目标键判定，含子串反例 | 消除 G7 误判 |
| 5 | 访问证明仅文字描述 | AC-07：`whoami`/`id` + flag 同屏布尔判据 | 失分条款须机器可判 |
| 6 | 未规定入口形态 | AC-01：`--payload` 与 `--from-loot` 结果等价 | 闭环 G6 |
| 7 | 未规定注册顺序 | AC-02：用法错误退出码 2 且无 `passed` | 防静默通过 |

## 6. 风险与核实闸

| 编号 | 风险 | 处置 |
|---|---|---|
| VG-1 | 报告章节名可能非官方用语 | 实现不依赖标题字符串，按目标键集 + 分值表判定（AC-04/AC-09） |
| VG-2 | 访问证明是否必须含 `whoami`/`id` 无 S3 原文 | AC-07 实现为「可配置必需标记集」，默认 `whoami`/`id`，SKILL 标注为人工判据兜底 |
| VG-3 | pandoc/7z 未生成时不可提交 | AC-12 pending 语义，`submission_ready=false` |
| VG-4 | 真实取分不可本地复现 | 人工考试边界，夹具自证；CI 以 dry-run + 假时间戳覆盖 |
| R-1 | 既有 10 用例回归被新判据打断 | AC-20 + 保留 `tests/test_verify_evidence.py` 全部用例；不顺从不许放宽判据 |

**NOTE 标记口径**（区别于 VG 核实闸：NOTE 为「机器不可判、须人工确认」的缺口项，只进 `missing`，不阻断 `passed`、也不改变 `submission_ready` 之外的语义）：NOTE-5 提交窗口时间未提供；NOTE-6 目标分值表未提供；NOTE-7 访问证明无内联文本（纯图片）；NOTE-8 归档密码态不可判（无 7z）。VG-3/VG-4 仍按 §6 定义作为 pending 核实闸。
