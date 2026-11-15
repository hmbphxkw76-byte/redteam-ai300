# loot-manage 一手源核实（canonical research）

> **性质**：研究文档（非规范正文）。`/主线 loot-manage` 阶段 1 产出，作为阶段 2/3/6/8 的事实源。
> **核验日期**：2026-11-15（GMT+8）。结论先行：loot-manage 是 **P0 运维型技能**，框架组合为「结构化凭据库（脚本/笔记）+ 许可 AI 助手，**无攻击框架**」（矩阵 ⑧）；其落地交付物为 `loot/registry.md` 单一事实源登记簿 + 校验工具，**不引入 PyRIT、不引入外部攻击框架**（B7/B9 以「框架无关」满足，属合规而非偏离）。
> **核验口径**：每条结论附一手来源路径；版本明确；攻击路径（loot-01..04）均映射到可机读契约；待核实项逐条命名。

---

## 1. 技能定位与框架组合（已核实）

| 项 | 事实 | 一手来源 |
|---|---|---|
| 优先级 / 能力域 / 计分单元 | P0 · D1（红队生命周期资产管理）+ D10（攻击路径沉淀）· 通用 | `skills/loot-manage/SKILL.md`（front-matter） |
| 框架组合 | 结构化凭据库（脚本/笔记）+ 许可 AI 助手；**无攻击框架** | `docs/research/osai-skill-framework-matrix.md` §2 ⑧ |
| 框架无关理由 | 运维型技能，价值在「不漏证、不乱证」，框架无法替代 | 同上 ⑧ 选择理由 |
| 与决策文档一致性 | 不采用单一框架；PyRIT 仅做 AI 向量深度利用内核，本技能不属其占优场景 | `docs/research/osai-ai300-framework-decision.md` §3.1（传统/运维类框架缺席） |

**结论**：阶段 8 实现**不得**引入 `pyrit` 依赖或任何攻击框架；B7（PyRIT 版本与对象图）与 B9（框架选型合规）以「矩阵 ⑧ 框架无关」满足，须在门禁记录显式标注，不构成偏离。

---

## 2. 登记簿表结构与执行体（已核实）

来源：`skills/loot-manage/SKILL.md`「执行体」。

- 单一 markdown 表，列结构**固定 8 列**：`编号 | 类型 | 内容 | 来源主机 | 证据片段路径 | 时间戳 | 状态 | 双通道（面板值 + 截图路径）`。
- 四个执行动作（即本技能「攻击路径」）：
  - **loot-01 凭据登记**（类型=`凭据`）：命令模板 `printf '| L-<编号> | 凭据 | <USER>:<SECRET> | <来源主机> | loot/<step>.md | <ISO8601> | 有效 | — |' >> loot/registry.md`。
  - **loot-02 会话登记**（类型=`会话`）：类型=`会话`，内容=接入方式，状态=存活/失效；横向移动前须查表复用存活会话与有效凭据。
  - **loot-03 flag 登记（双通道占位）**（类型=`flag`）：类型=`flag`，双通道列=``面板=<FLAG_VALUE>；截图=<screenshot 路径>``；域控 `proof.txt` 须显式标注「仅可提交一次」。
  - **loot-04 攻击路径与索引沉淀**：登记簿末尾「`### 攻击路径`」小节追加路径摘要；核对全表索引（证据路径存在、flag 双通道齐全）。
- 行为唯一来源为 SKILL.md；登记簿**不重复存储证据本体**，仅存 `证据片段路径` 指针（指向 `collect_evidence.py` 产物）。

---

## 3. 证据契约映射（已核实）

| loot 动作 | 引用契约 | 一手来源 |
|---|---|---|
| loot-01/02/03 证据片段路径 | `tools/collect_evidence.py` 产物（`--step <prefix>-NN` 落盘 markdown 片段，三件套：确切命令+关键输出+截图） | `tools/collect_evidence.py` `REQUIRED_PIECES` |
| loot-03 flag 双通道 | 控制面板提交值 == 报告/截图值，二者一致；任一缺失即失分 | `docs/governance/GOVERNANCE.md` §6.2；`tools/verify_evidence.py` `vrf-04` |
| 五件套/三件套完整性 | 三件套必需，AI 交互日志 + flag 双通道可选；`--strict` 强制失败 | `tools/collect_evidence.py` `OPTIONAL_PIECES` / `--strict` |
| 域控 proof.txt | 仅可提交一次；登记时显式标注 | `skills/loot-manage/SKILL.md` loot-03 第 3 点；`tools/verify_evidence.py` `proof-single` |

**结论**：本技能自身不重新取证（截图豁免，见 §6）；其契约是**消费**上游证据片段路径与双通道占位，供 `verify-evidence` / `report-exam` 无损回溯。

---

## 4. 质量门（已核实，须由落地工具机读校验）

来源：`skills/loot-manage/SKILL.md`「质量门」。可机读项与人工项分离：

| # | 质量门 | 可机读 | 校验方式（落地工具） |
|---|---|---|---|
| 1 | 登记簿存在且 8 列表结构齐全 | 是 | 解析表头列名集合 == 固定 8 列 |
| 2 | 每行可追溯：来源主机与证据片段路径均真实存在 | 部分 | 证据片段路径文件存在（来源主机为自由文本，人工核对） |
| 3 | 每个 flag 均有双通道占位 | 是 | flag 行双通道列含 `面板=` 与 `截图=` |
| 4 | 无战利品散落对话上下文 | 否（纪律） | 人工；本工具提供编号 L-N 指代规范 |
| 5 | 登记动作即时（取得即登记） | 否（纪律） | 人工；工具提供 `register` 即时追加 |

---

## 5. 校验标准（已核实）

来源：`skills/loot-manage/SKILL.md`「校验标准」：① 可被 `report-exam` 无损复用（任一登记行经证据片段路径还原完整三件套）；② 可被 `verify-evidence` 消费（flag 双通道占位支持逐项核对）；③ 横向复用有效（状态标注准确）；④ 术语符合 `GLOSSARY.md`（用「战利品/攻击链/诱饵机」，禁用 `_Avoid_` 废弃术语）。

---

## 6. 失败与豁免（已核实）

来源：`skills/loot-manage/SKILL.md`「失败与豁免」：① 凭据/会话失效→更新状态列为「失效」保留原行（历史可追溯），不得删除；② 全程无战利品→记录空态与原因，作为 `capstone-rehearse` 缺口输入；③ **登记簿不含截图本体（仅路径），截图捕获实现不在本技能范围**（Out of scope，豁免依据）；④ 登记行引用证据片段缺失→补齐引用路径后再过质量门，禁止以对话上下文记忆替代证据。

---

## 7. 术语核对（已核实 / 已识别 gap）

- `GLOSSARY.md` 已定义且本技能复用：**flag**（§考试与评分）、**域控**（proof.txt 仅一次）、**诱饵机**、**攻击链**（区分：本技能用「攻击路径」沉淀，见下）、**证据片段**（collect_evidence 原子单元）、**双通道**（flag 双通道）。
- **已识别 gap（阶段 7 须补）**：`GLOSSARY.md` 未定义 **战利品**、**战利品登记簿（registry）**、**攻击路径**（与「攻击链」不同：路径为单技能内「入口→主机→横向」摘要，链为跨 3 主机的计分路径）。须补条目并标注禁用同义词（如「战利品」禁「loot 散落」式误用；「攻击路径」禁与「攻击链」混用）。
- `_Avoid_` 预警机制：`tools/collect_evidence.py` 与 `tools/verify_evidence.py` 均从 `GLOSSARY.md` 动态读取废弃术语；落地工具应复用同一解析源（避免术语判据漂移）。

---

## 8. CI 门禁映射（已核实）

| 治理条款 | 落地动作 |
|---|---|
| `docs/standards/CI-CD.md` S1-2 术语一致性 `check_glossary.py` | 阶段 7 补 GLOSSARY 后全量通过 |
| S1-6 共享工具语法编译 | `python -m py_compile tools/loot_manage/*.py` |
| S2 自动化测试 ≥80% 覆盖率 | 阶段 9 `tests/test_loot_manage_*.py`（标准库 unittest，零依赖） |
| S1-1 Markdown 规范 | SKILL.md / 登记簿注释合规 |

---

## 9. 待核实 / 已排除清单

- **已核实**：§1–§8 全部事实，来源均为本仓库一手文件（SKILL.md / 矩阵 / 决策 / collect_evidence.py / verify_evidence.py / GOVERNANCE §6 / GLOSSARY / CI-CD）。
- **待核实（实现前取证闸）**：
  - G1：演练环境（OSAI 考试外）实际 `loot/registry.md` 占位目录约定——落地采用仓库根 `loot/`（与 SKILL.md 命令模板一致），待阶段 8 落盘时以空骨架确认。
  - G2：`register` 工具的 `proof.txt` 单次提交标注是否纳入机读校验——阶段 6/8 设计为「flag 行若内容含 `proof.txt` 则双通道列须含「仅可提交一次」标注」的软校验。
- **已排除**：
  - PyRIT / garak / promptfoo / Kali 工具链——均不适用于本运维技能（矩阵 ⑧ / 决策 §3.1）。
  - 截图捕获实现——SKILL.md 明确 Out of scope 豁免（§6.③）。
  - 任何把战利品内容外发到托管服务的逻辑——与考试离线/保密硬约束冲突，禁止。

---

## 11. 阶段 1 门禁记录（G0 · B7/B8/B9）

| 基线 | 判定 | 证据命令 | 结论 |
|---|---|---|---|
| B7 PyRIT 版本与对象图 | 符合（N/A） | `grep -rniE "pyrit\.orchestrator\|Orchestrator\|AzureOpenAIChatTarget" skills/loot-manage docs/research/loot-manage-canonical.md` → 无命中 | loot-manage 框架无关（矩阵 ⑧），不引入 PyRIT，合规非偏离 |
| B8 可追溯性 | 符合 | `grep -cE "docs/research/\|skills/loot-manage\|tools/\|docs/governance\|GLOSSARY" docs/research/loot-manage-canonical.md` → 18 条路径来源 | 每条结论附一手路径源 |
| B9 框架选型合规 | 符合 | 已读 `osai-ai300-framework-decision.md` 与 `osai-skill-framework-matrix.md`；`grep -n "loot-manage（D1,D10" 矩阵` → 第 91 行 ⑧ | 框架组合取自矩阵 ⑧（结构化凭据库+许可AI，无攻击框架） |

**不符合项**：0。**结论：PASS**。复验命令同上。issue 索引摘要（阶段 1 / PASS / 0 / 复验=上述三条 grep）。

---

## 10. 版本与破坏性变更

- 本技能**无外部框架版本依赖**（pyrit 不适用）。
- 工具仅依赖 Python 标准库（与 `collect_evidence.py` / `verify_evidence.py` 一致），零第三方依赖，`requirements.txt` 无需变更。
- 破坏性变更风险点：登记簿表头列名顺序若被后续 SKILL 修订调整，须同步 `tools/loot_manage/` 解析——已在阶段 6 seam 设计中以「表头列名集合」而非「索引位置」匹配以降低脆弱性。
