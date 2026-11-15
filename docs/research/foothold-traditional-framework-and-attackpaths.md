# foothold-traditional 调研：框架选型与传统向量攻击路径

> **性质**：研究文档（非规范正文），供 `foothold-traditional` 技能落地的事实基准。
> **核验日期**：2026-11-15（GMT+8）。**结论先行**：本技能框架组合 = **纯 Kali OSCP 工具链 + 自定义 Py/Bash**，**PyRIT / garak / promptfoo 零参与**；因此主线门禁 B7（PyRIT 版本与对象图）**不适用（N/A）**，框架合规基线 B9 以「对齐矩阵⑦、主动排除 AI 框架」满足。
> **一手源优先级**：OSAI 考试事实 → 项目框架决策/矩阵文档 → 工具官方文档；二手博客不引用。

---

## 1. 框架选型合规（已核实）

| 结论 | 依据 | 判定 |
|---|---|---|
| 主攻框架 = 纯 Kali OSCP 工具链（nmap / msfconsole / impacket / proxychains / OpenSSH / Unix 提权枚举），辅助 = 自定义 Py/Bash；AI 红队框架不参与 | `docs/research/osai-skill-framework-matrix.md` 条目 ⑦（foothold-traditional，P0，D1） | 符合 |
| 分层栈定位 = 决策文档「落地层：Kali 工具链（nmap/burp/impacket/云 CLI）— 传统向量/横向/DC/云」 | `docs/research/osai-ai300-framework-decision.md` §4 角色图例与 §3.1 末行「传统向量/链内横向/DC：任何 AI 框架都覆盖不了」 | 符合 |
| PyRIT 缺席：矩阵⑦与决策文档均明确本技能「AI 框架零参与」；故 B7 不适用 | 同上两条 + `docs/operations/skill-mainline-workflow.md` §2.1 B7（仅当 PyRIT 参与时适用） | B7=N/A |
| 偏离矩阵须显式说明理由：本技能**完全对齐**矩阵⑦，无偏离 | `skill-mainline-workflow.md` §1.4 第 2 点（B9） | 符合（无偏离） |

**合规结论**：所选框架组合取自矩阵对应条目（⑦），未偏离，B9 满足；因 PyRIT 不参与，B7 标记为 N/A 而非违反。

---

## 2. OSAI 考试传统向量硬约束（已核实，S3 快照）

> 一手源：`docs/governance/references/OSAI-Exam-Guide-snapshot.md`（S3）；分值推导见决策文档 §1。

| 事实 | 内容 | 对技能的含义 |
|---|---|---|
| 形态 | 24h 监考，Tailscale VPN + 本地 Kali VM 接入 AI 赋能企业环境；2 条独立攻击链，各 3 台机，汇聚同一域控；1 台独立 AI 主机；2 台故意不脆弱（0 分，=诱饵机） | 传统向量工作在「链内 3 台机」上；入口选择须先做诱饵判定（`decoy-detect`） |
| 计分 | 8 台计分 = 100 分，75 分及格；链内构成推导为 4×AI(15) + 2×传统(10) = 80，+ 独立 AI(15) = 95，+ DC(5, 仅一次) = 100 | 本技能认领 **2 台传统向量机（10 分/台，共 20 分）** |
| 工具政策 | 完全开卷，「any tooling, framework, or technique」；AI 聊天机器人被明确允许 | Kali 工具链 + 许可 AI co-pilot 均合规 |
| 报告门槛 | 每步命令/输出/脚本/修改说明 + 截图 + **可 copy/paste 逐步复现**；PDF 入 `.7z`（无密码、≤100MB）；文档缺失 = 扣分或零分 | 每步经 `collect_evidence.py` 落盘三件套（命令+输出+截图），对齐 GOVERNANCE §质量门 |
| 链入口职责 | 任一链的初始立足点是后续全部 AI 向量利用的前置（流水线第三站） | `trad-08` 须显式产出「立足点移交清单」，显式满足 `attack-ai-agent` / `attack-rag` / `attack-mcp-tool` 的内网前置 |

---

## 3. Kali 工具链攻击路径映射（已核实，工具官方文档）

SKILL.md 的 trad-01…trad-08 命令与一手工具文档一致；逐条对齐：

| Step | 命令（骨架） | 工具官方一手源 | 判定 |
|---|---|---|---|
| trad-01 入口服务枚举 | `nmap -sV -sC -p- <ENTRY_IP>` | nmap 官方文档 `https://nmap.org/docs.html`（`-sV` 版本探测、`-sC` 默认脚本、`-p-` 全端口） | 符合 |
| trad-02 公网入口利用 | `msfconsole -q -x "use <ENTRY_EXPLOIT>; set RHOSTS ...; run"` | Metasploit Framework 官方 `https://docs.metasploit.com/`；第三方 exploit 须附来源/代码副本（GOVERNANCE §6.1） | 符合（运行时附来源） |
| trad-03 首台提权枚举 | `sudo -l; find / -perm -4000 -type f; id && <PRIVESC> && id` | Unix `sudo(8)`、`find(1)` perm 匹配、提权前后 `id(1)` 对照 | 符合 |
| trad-04 首台 flag 取证 | `whoami; id; find / -name trad_vector.txt -exec cat {} \;` | `find(1)` 定位 + `cat` 读取；双通道一致（面板提交 == 截图，GOVERNANCE §6.2） | 符合 |
| trad-05 内网横向枚举 | `proxychains nmap -sV -p- <INTERNAL_NET>` | proxychains-ng `https://github.com/haad/proxychains`（通过 pivot 代理内网流量） | 符合 |
| trad-06 凭据复用横向 | `ssh <USER>@<CHAIN1_HOST2> -i <LOOTED_KEY>` | OpenSSH `ssh(1)` `-i` 身份文件；优先复用 `loot-manage` 登记密钥，非重新爆破 | 符合 |
| trad-07 次台提权+flag | 复用 trad-03/04 模式于次台 | 同 trad-03/04 | 符合 |
| trad-08 路径沉淀+移交 | `collect_evidence.py --step trad-08 ...`（路径图与移交清单落 `loot/`） | 证据 seam 唯一化（见 §4） | 符合 |

---

## 4. 证据契约与双通道（已核实）

| 结论 | 依据 | 判定 |
|---|---|---|
| 每步经 `tools/collect_evidence.py --step trad-0N --strict` 落盘三件套 | `skills/foothold-traditional/SKILL.md` 每步证据命令；`docs/governance/GOVERNANCE.md` §质量门 | 符合 |
| 提权步骤「前后权限证明」同屏（`id` 前后对照） | SKILL.md trad-03/trad-07 + GOVERNANCE §6.2 | 符合 |
| flag 双通道一致（面板提交值 == 报告截图/正文） | GOVERNANCE §6.2；GLOSSARY「flag / 校验预言机」 | 符合 |
| 证据结构与 `report-exam` 五段式 Attack Walkthrough 直接兼容 | `docs/research/report-exam-canonical.md`（五段式）；SKILL.md 校验标准 | 符合 |
| 唯一证据 seam = `collect_evidence.py`，零新增工具 | SKILL.md 实现决策；T5 证据契约夹具 `tests/test_foothold_traditional_evidence_contract.py` | 符合 |

---

## 5. 待核实 / 已排除

### 待核实（实现前取证闸）
- **目标具体 IP / 服务版本 / 可利用 exploit**：考试运行时经 `recon-ai` 枚举结果 + trad-01 针对性枚举取得；SKILL.md 以 `<ENTRY_IP>` / `<ENTRY_EXPLOIT>` 占位，属运行时取证，非规格缺陷。
- **trad-02 第三方 exploit 来源链接 / 代码副本 / 修改说明**：运行时按 GOVERNANCE §6.1 附，规格阶段不预置具体 CVE。
- **诱饵机判定依据**：trad-02 前置须先 `decoy-detect` 判定，≤30 分钟时间盒（SKILL.md 失败与豁免）。

### 已排除（明确不采用）
- **PyRIT / garak / promptfoo 用于传统向量**：矩阵⑦与决策文档 §3.1 明确「任何 AI 框架都覆盖不了传统向量/链内横向/DC」，本技能严格排除 → 满足 B9 且 B7=N/A。
- **截图捕获实现**：仅接收路径/钩子（与全仓库约定一致，`collect_evidence.py` 不实现捕获）。
- **域控收敛 / AI 特定利用**：超出本技能范围（编排层 / `attack-ai-*` 系列）。

---

## 6. 参考源（一手优先）

- OSAI Exam Guide（S3 快照）：`docs/governance/references/OSAI-Exam-Guide-snapshot.md`
- 框架决策：`docs/research/osai-ai300-framework-decision.md` §1/§3.1/§4
- 技能×框架矩阵：`docs/research/osai-skill-framework-matrix.md` 条目 ⑦
- 主线门禁基线：`docs/operations/skill-mainline-workflow.md` §2.1（B7/B8/B9）
- 证据与双通道：docs/governance/GOVERNANCE.md §质量门 / §6.1 / §6.2；GLOSSARY「证据 / flag / 校验预言机」
- 工具官方文档：nmap.org/docs.html、docs.metasploit.com、github.com/haad/proxychains、OpenSSH `ssh(1)`/`find(1)`/`sudo(8)`/`id(1)`

---

## 门禁记录（阶段1 · research）

阶段验收：① 每条结论可定位一手源 — 是（§1-§4 逐条附 URL/路径）；② 版本号明确 — 是（PyRIT 不参与，无需版本；Kali 工具为当前稳定版，运行时取证）；③ 每条攻击路径有对象映射 — 是（§3 step→工具→一手源）；④ 待核实项命名且给取证方式 — 是（§5 待核实）；⑤ 文档落盘 `docs/research/` — 是。

| 基线 | 判定 | 证据命令 |
|---|---|---|
| B7 PyRIT 版本/对象图 | 不适用 | 矩阵⑦与决策文档 §3.1 明确本技能「AI 框架零参与」→ B7=N/A（非违反） |
| B8 可追溯性 | 符合 | 全文逐条附 `docs/research/osai-skill-framework-matrix.md#⑦`、`osai-ai300-framework-decision.md`、S3 快照、`tools/collect_evidence.py` 等路径；`GOVERNANCE.md` 路径已校正为 `docs/governance/GOVERNANCE.md` |
| B9 框架选型合规 | 符合 | 所选组合取自矩阵条目⑦（纯 Kali + 自定义），无偏离；PyRIT 主动排除，B7=N/A |

**不符合项**：无。**结论：PASS**。

> 索引（issue 评论口径，T5）：阶段1 / PASS / 不符合项 0 / 复验 `python scripts/check_token_budget.py --artifact spec-v1 docs/research/foothold-traditional-framework-and-attackpaths.md`（研究文档非规格，仅作大小自检）
