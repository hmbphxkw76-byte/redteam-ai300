# verify-evidence 规范事实库（canonical references）

> **性质**：研究/事实文档（非规范正文）。供 `skills/verify-evidence/SKILL.md` 落地为 `tools/verify_evidence.py` 时使用。
> **核验日期**：2026-11-15（GMT+8）。每条结论附一手来源（条款行号或源码位置）；待核实项逐条命名并给出取证方式。
> **依据**：`docs/governance/GOVERNANCE.md` v1.1、`docs/standards/CI-CD.md` v1.1、`docs/governance/references/OSAI-Exam-Guide-snapshot.md`（S3 快照）、`skills/verify-evidence/SKILL.md`、`report_exam/_types.py`、`tools/loot_manage/registry.py`、`tools/collect_evidence.py`。

---

## 1. 定位与边界

- **能力域 D11**（SKILL front-matter `domain: D11`，与 `report-exam` 对齐）· **优先级 P0**（GOVERNANCE §4.3.1(c)「直接决定是否及格（报告、证据校验）」）· **计分单元 通用**（防失分，不直接产出 flag）。
- **触发**：`report-exam` 已产出报告与归档、进入提交窗口前（SKILL `trigger`）。
- **PyRIT 对象图**：**无**。本技能为 S1-only 静态校验域，不调用任何 `*Attack`/`OpenAIChatTarget`（SKILL「失败与豁免」末段；B7 对本技能的判定形式是「确认为零 PyRIT 依赖」，而非对象映射）。`requirements.txt` 锁定 `pyrit==1.1.0`（ADR-0004），本技能不 import。

## 2. 规范一手源清单（条款 → 判定对象）

| 规范条款 | 位置锚点 | 本技能的判定对象 |
|---|---|---|
| 计分模型 8 目标 100 分；AI 15/传统 10/独立 15/域控 5 | `GOVERNANCE.md#L54-L58`（§2.2.1） | vrf-02 分值加总与目标键集 |
| 域控 `proof.txt` 仅可提交一次 | `GOVERNANCE.md#L57`（§2.2.3） | `proof-single` 检查 |
| 失分条款：面板**与**报告须同时提供 flag 内容与截图 | `GOVERNANCE.md#L68`（§2.4.2） | vrf-04 阻断判据 |
| 五要素 + 七字段 front-matter | `GOVERNANCE.md#L106-L113`（§4.2） | vrf-01（`scripts/validate_skill.py`） |
| 优先级分层判据 | `GOVERNANCE.md#L115-L118`（§4.3）+ ADR-0002 | vrf-02（杠杆一致性） |
| AI 工具使用纪律 | `GOVERNANCE.md#L173-L180`（§5.5） | vrf-05 人工校验标注 |
| 每步 = 命令 + 输出 + 截图；copy/paste 可复现 | `GOVERNANCE.md#L182-L184`（§6.1） | vrf-03、vrf-06 |
| flag 双通道一致 + 访问证明（`whoami`/`id` + flag 同屏） | `GOVERNANCE.md#L186-L188`（§6.2） | vrf-04 |
| AI 交互入附录，标准不低于其它工具 | `GOVERNANCE.md#L190-L191`（§6.3） | vrf-05 |
| PDF 命名 / `.7z` 无密码 / ≤100MB / **24h 内**、提交后不可修改 | `GOVERNANCE.md#L193-L196`（§6.4）；S3 快照 `#L68-L74`、`#L88-L92` | vrf-07 |
| 报告四章结构 + 每主机五段式 | `GOVERNANCE.md#L202-L210`（§7.1/§7.2） | vrf-06 |
| 提交为终态，提交前**必须**经 verify-evidence 全量校验 | `GOVERNANCE.md#L212-L213`（§7.3） | 退出码 0 才允许提交 |
| 八项合规检查清单 | `GOVERNANCE.md#L223-L233`（§8.2） | vrf-01…vrf-08 编号即检查单编号 |
| 不合规处理（豁免须显式声明） | `GOVERNANCE.md#L235-L237`（§8.3） | 豁免项记录格式 |

**S3 官方原文（快照逐字，唯一权威）**：`docs/governance/references/OSAI-Exam-Guide-snapshot.md#L74` — “Learners must submit their report within 24 hours of completing the exam. Failure to meet this deadline will result in an automatic exam failure.” → 24h 为**硬性自动不及格**，故 vrf-07 的窗口判定属阻断项，不可降级为警告。

**事实归属澄清（防误标）**：`trad_vector.txt` / `ai_vector.txt` / `proof.txt` 文件名**不在 S3 原文**，来自 S1（官方报告 PDF 第 5 页），见快照 `#L142` 的显式声明。引用时不得标注为 S3。

## 3. 输入契约（三段，均为既有实现，只引路径）

| 输入 | 权威定义 | 本技能读取的字段 |
|---|---|---|
| 证据片段 | `report_exam/_types.py#Fragment`（`step_id`/`command`/`output`/`screenshot`/`ai_log`/`flag`/`host`） | 三件套齐全性、flag 值、AI 日志 |
| 片段解析 | `report_exam/index.py#parse_fragment`（`#### 确切命令`/`#### 关键输出`/`#### 截图`/`#### AI 交互日志`/`#### flag 取证（双通道一致）`） | 段落定位（契约：改段落结构须回归该解析器） |
| 战利品登记簿 | `tools/loot_manage/registry.py#parse_dual`（`面板=<值>；截图=<路径>`）、`#fragment_pieces`（三件套布尔） | 双通道值、三件套判据 |
| 采集器 | `tools/collect_evidence.py`（`--step`/`--cmd`/`--out`/`--flag-panel`/`--flag-shot`） | 片段生产端，本技能不调用 |

**单一事实源约束（AGENTS.md C1）**：三件套与双通道判据已存在于 `registry.py`；本技能的校验器**必须复用**该实现，不得另写一套更宽的判定（否则门禁判据被下游重实现放宽）。

## 4. 现状核实（代码级，2026-11-15）

已落地：`tools/verify_evidence.py`（203 行，纯标准库，退出码 0/1/2）、`tests/test_verify_evidence.py`（165 行，10 用例）、`report_exam/package.py` 委托调用（`#L115` `verify()`）、CI 注册 `ci.yml#L55`（py_compile）与 `report-toolchain.yml#L92`（`verify-evidence: passed` 断言）。工单 #51–#54 已关闭。

**缺口（按条款归类，构成本次主线的实现目标）**：

| 编号 | 缺口 | 条款 | 影响 |
|---|---|---|---|
| G1 | vrf-01 仅校验报告内 `# OSID:` 与版权行，未调用 `validate_skill.py` 做「已纳管技能五要素」终检 | §4.2 / §8.2-1 | 检查单 1 未闭环 |
| G2 | vrf-02 判据为章节标题存在性（`Target Inventory & Point Allocation`），未校验 8 目标键集与分值加总 = 100 | §2.2 / §4.3 / ADR-0002 | 无法证明「优先级与评分杠杆一致」 |
| G3 | vrf-03 读 payload 布尔字段，未复用 `registry.fragment_pieces` 原文判据 | §6.1 / C1 | 两套判据存在漂移 |
| G4 | vrf-04 只比对 `host→panel` 值，未判「访问证明截图含 `whoami`/`id` + flag 同屏」，未消费登记簿双通道单元格 | §6.2.2 | 失分条款防线不完整 |
| G5 | vrf-07 无 24h 窗口判定（无 `exam_end_at`/`submit_at` 入参） | §6.4.3 / S3 快照 `#L74` | 硬性自动不及格项未被机器判定 |
| G6 | 无登记簿直连入口（`--from-loot`），输入须外部预构造 JSON | SKILL `input` 字段 | 「复用 loot-manage 登记簿」在执行体层未闭环 |
| G7 | `proof-single` 用 `"proof.txt" in flag` 字符串匹配，与目标键解耦 | §2.2.3 | 误判风险（flag 值含该子串即误计） |

## 5. 核验清单

**已核实**：§2 全部条款行号与原文；S3 24h 与命名原文；`Fragment`/`parse_fragment`/`parse_dual`/`fragment_pieces` 接口签名；CI 两处接线；`pyrit==1.1.0` 锁定且本技能零依赖。

**待核实（核实闸，逐条命名）**：

| 编号 | 待核实项 | 取证方式 |
|---|---|---|
| VG-1 | 报告章节名 `Target Inventory & Point Allocation` 是否官方模板用语 | 比对 `report_exam` 骨架 `skeleton.py` 与 S1 报告 PDF 第 5 页；不一致则改为按 `SCORED_HOSTS` 键集判定，不依赖标题 |
| VG-2 | 「访问证明」是否必须含 `whoami`/`id` 当屏 | S1 官方报告示例截图；无原文支撑时降级为人工判据并在 SKILL 注明 |
| VG-3 | pandoc/typst 与 7z 是否在目标环境可用（产物真跑） | `python -m report_exam build`；已在 `report-toolchain.yml` 真跑，本技能 dry-run 记 pending |
| VG-4 | 真实取分（OSID、真实 flag、24h 窗口） | 人工考试边界，本地仅以夹具自证 |

**已排除**：PyRIT 对象映射（本技能零 PyRIT 依赖）；截图 OCR 值级比对（不在 S1/S3 要求内，成本过高，改为同屏文字断言 + 人工判据）。

---

## 门禁记录（阶段 1 · research）

| 编号 | 检查项 | 依据 | 实测结果（命令 + 输出摘要） | 判定 | 不符合项描述 | 修正要求（文件 + 位置 + 动作 + 复验命令） | 复验结果 | 结论 |
|---|---|---|---|---|---|---|---|---|
| B7 | PyRIT 版本与对象图 | ADR-0004 / B7 | `grep -n pyrit requirements.txt` → `pyrit==1.1.0`；本技能零 `pyrit` import（`grep -rn pyrit tools/verify_evidence.py` 空输出） | 符合 | — | — | — | PASS |
| B8 | 可追溯性 | B8 | 每条结论附 `GOVERNANCE.md#L行号` 或源码位置；VG-1…VG-4 均给出取证方式 | 符合 | — | — | — | PASS |
| 验收① | 结论可定位 | §3.1 | §2 表 13 行全部带锚点 | 符合 | — | — | — | PASS |
| 验收② | 版本号明确 | §3.1 | §1 标注 `pyrit==1.1.0` 且声明零依赖 | 符合 | — | — | — | PASS |
| 验收③ | 攻击路径映射 | §3.1 | 本技能无攻击路径；以「检查项 ↔ 条款」映射替代（§2 表） | 符合 | 例外已显式说明（§1 PyRIT 行） | — | — | PASS |
| 验收④ | 待核实项命名 | §3.1 | VG-1…VG-4 四条，各带取证方式 | 符合 | — | — | — | PASS |
| 验收⑤ | 落盘位置 | §3.1 | `docs/research/verify-evidence-canonical.md` | 符合 | — | — | — | PASS |

**结论：PASS** — 0 不符合项；进入阶段 2（`to-spec` ①）。
