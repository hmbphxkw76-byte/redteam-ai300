# foothold-ad 优化方案与实施清单

> 依据：`docs/research/ai300-lab-scenario-coverage.md` §4（P0/P1 缺口排序）。
> 一手源：Ch11 §0.2/§2–§3.6（三域森林、ACL 决策表）、MegaCorpOne 手册 §5.3（域与信任）、§5.4（ACL 矩阵）。
> 性质：方案 + 实施清单。§9 声明本轮未执行的主线阶段（C8 不改判定语义）。

## 1. 问题陈述

覆盖分析给出 50 个场景中 8 项未覆盖、13 项部分覆盖，其中两项为结构性缺口：

| 缺口 | 依据 | 后果 |
|---|---|---|
| AD 域渗透与域控收敛无承载技能 | 覆盖报告 §4 P0 第 1 行；`skills/` 内 Kerberos / DCSync / ADCS 零命中 | Ch11 的 Domain Admin 目标与 `proof.txt` 无法由技能产出，`capstone-rehearse` 只能登记缺口 |
| 影子 API 端点发现 | 覆盖报告 §4 P0 第 2 行；`recon-ai` recon-01..07 未含未公开 location | Ch2 侦察链在资产清单层断链 |

本方案只解决第一项（可实施、可验证）；第二项给出方案与契约影响评估，不实施（§8）。

## 2. 技能边界

AD 面与既有技能的职责切分，避免判据重叠（C1）：

| 能力 | 承载技能 | 边界说明 |
|---|---|---|
| 公网入口、本地提权、内网横向、`trad_vector.txt` | `foothold-traditional` trad-01..10 | 既有判据不动；本文档不修改该技能任何一行 |
| AD 特有面：Kerberos 票据、ADCS 模板、目录复制、域信任、域控收敛 | **`foothold-ad` ad-01..ad-08** | 只处理「已取得域内立足点之后」的域级升级 |
| 立足点移交 | `foothold-traditional` trad-08 → `foothold-ad` ad-01 | 复用既有移交清单字段（会话/凭据/路由/战利品索引），不新造格式 |
| 凭据/flag 登记 | `loot-manage` loot-01..05 | 每取得票据、哈希指纹或 `proof.txt` 即时登记 |
| 演练走查与缺口 | `capstone-rehearse` | 只判定就绪度，不执行 AD 利用 |

**移交契约**：`foothold-ad` 的前置输入为 trad-08 移交清单中的三项——域内主机会话、可用凭据（含指纹）、可达域控地址。缺任一项即 `BLOCKED` 并回退 `foothold-traditional`，不自行重做入口。

## 3. 步骤设计

八步，覆盖课程 Ch11 攻击路径第 5–10 步的 AD 段。每步产出「命令 + 输出 + 截图」三件套，flag 与 `proof.txt` 走双通道。

| 步骤 | 能力 | 输入工件 | 判据（布尔） | 证据 |
|---|---|---|---|---|
| ad-01 | 域环境测绘与信任枚举 | `ldapsearch` / `nltest` 输出、`trusts.json` | 根域与子域、信任方向、SID 过滤状态齐备；缺项记 `UNDETERMINED` | 三件套 + 分析注记 |
| ad-02 | Kerberos 可攻击账户枚举 | BloodHound `users.json` 子集 | SPN 且启用、无需预认证、非约束委派三类各自成表 | 三件套 + 账户清单 |
| ad-03 | 票据获取与 Kerberoast/AS-REP | `GetUserSPNs` / `GetNPUsers` 输出 | 取得票据哈希且含加密类型；失败记 `NOT_VULNERABLE` 并给出依据 | 三件套 + 哈希指纹（不落明文） |
| ad-04 | ADCS 模板利用面判定 | Certipy `find` JSON | ESC1（可控主体 + 认证 EKU + 低权可注册）、ESC8（HTTP 注册 + NTLM 中继面）分别判定 | 三件套 + 模板清单 |
| ad-05 | 目录复制权限（DCSync 面） | ACL 导出（对象 ACE） | 非 DC 主体持有 `DS-Replication-Get-Changes-All` 即成链；仅 `Get-Changes` 记部分 | 三件套 + 主体清单 |
| ad-06 | 域信任滥用路径 | 信任 + 跨域组成员 | 双向可传递信任下存在跨域高权主体或 SID 过滤关闭即成链 | 三件套 + 路径图 |
| ad-07 | 域控收敛与 `proof.txt` 取证 | 域控会话 | `whoami`/`id` 与 `proof.txt` 同屏；双通道一致 | 五件套 + 双通道表 |
| ad-08 | 攻击路径沉淀与移交 | 前七步产物 | 路径图 + 凭据索引 + 对 `report-exam` 的无损片段 | 三件套 + 路径图 |

判据取值域沿用仓库既有五值语义（`EXPLOITED` / `EXPOSED_NO_AUTH` / `AUTH_REQUIRED` / `ABSENT` / `BLOCKED`），不新造第六值；无法判定统一 `UNDETERMINED` 并在注记说明依据。

## 4. 技术选型

- **零第三方依赖**：仅标准库。AD 工具（Impacket / Certipy / BloodHound）只作为**工件生产者**，本包只解析其导出结果，不 import、不封装、不调用。
- **零 PyRIT**：AD 面不涉及 LLM 交互，不引入 `pyrit`。
- **离线优先**：所有判据以文件为输入，可在无域环境下自测；无工件即 `BLOCKED`。
- **单一网络 seam**：若需实跑命令，统一经注入的 `CommandRunner`（与 `tooling-automate` 同构），测试用 Fake。
- **凭据不落盘**：哈希仅存「算法 + 前 8 位 + 长度 + 位置」指纹，对齐 `foothold-traditional` ch9 的 P-1 约束。

## 5. 实现结构

| 模块 | 单一职责 | 公开接口 |
|---|---|---|
| `model` | 类型与取值域 | `Verdict`、`StepResult`、`Finding`、`STEP_IDS`、`STEP_TITLES` |
| `artifact` | 工件解析（容错、缺字段不猜） | `load_json`、`parse_directory`、`parse_templates`、`parse_acl`、`parse_trusts`、`fingerprint_hash` |
| `analyze` | 六类判据的纯函数 | `kerberoastable`、`asrep_roastable`、`unconstrained`、`adcs_risks`、`dcsync_principals`、`trust_risks`、`path_to_domain_admin` |
| `evidence` | 参数组装（不自建证据实现） | `build_evidence_argv`、`summarize` |
| `runner` | 从工件目录编排八步 | `run`（返回 `RunReport`）、`plan_steps` |
| `cli` | 命令行与退出码 | `main` |

依赖单向：`cli → runner → {artifact, analyze, evidence} → model`，无环。

## 6. 风险与失败模式

| 风险 | 判定 | 处置 |
|---|---|---|
| 无域环境 / 无工件 | `BLOCKED` | 记录缺失文件名与依据，不生成占位结论 |
| 工件字段缺失（如无 SID 过滤状态） | `UNDETERMINED` | 注记写「字段缺失」，不按默认值推断 |
| 哈希以明文出现在导出中 | 立即掩码 | 只留指纹；测试断言明文不出现在任何输出 |
| 凭据复用被判为越权 | 阻断 | 跨域动作前核对 ACL 决策表（Ch11 §3.6），无对应放行即阻断 |
| 课程目标（Domain Admin）与考试计分混淆 | 语境门 | 仅 `course-capstone` 语境要求 `proof.txt`；`osai-rehearsal` 语境按计分单元产出 |

## 7. 实施清单

依赖顺序执行，每项含验收命令。状态列在验证报告中回填。

| ID | 变更 | 验收命令 | 前置 |
|---|---|---|---|
| I-1 | 新增 `skills/foothold-ad/SKILL.md` | `python scripts/validate_skill.py` | 无 |
| I-2 | 新增 `tools/foothold_ad/{model,artifact,analyze,evidence,runner,cli,__main__,__init__}.py` | `python scripts/check_tools_compile.py` | I-1 |
| I-3 | 新增 `tests/foothold_ad/`（≥6 模块） | `python -m unittest discover -s tests/foothold_ad -t .` | I-2 |
| I-4 | 新包覆盖率 ≥90% | `python scripts/measure_coverage.py --target foothold-ad` | I-3 |
| I-5 | `GLOSSARY.md` 腾位并新增 AD 术语 4–5 条 | `python scripts/check_glossary.py` | I-1 |
| I-6 | `docs/contracts/consumers.md` 新增 `foothold-ad` 行（状态 `未合入`） | `python scripts/check_contract_consumers.py` | I-2 |
| I-7 | `scripts/tools_manifest.json` 登记编译包与覆盖率目标 | `python scripts/check_tools_compile.py --check-missing` | I-2 |
| I-8 | `GOVERNANCE.md` §4.4 登记技能行 | `python scripts/validate_skill.py` | I-1 |
| I-9 | `skills/capstone-rehearse/SKILL.md` 流水线接入 `foothold-ad` | `python scripts/check_token_budget.py --check` | I-1 |
| I-10 | 全量回归 | `python -m unittest discover -s tests -t .` | I-1..I-9 |
| I-11 | 预算与格式门禁 | `python scripts/check_token_budget.py --check`；`npx markdownlint-cli2` | I-10 |
| I-12 | 技能引用校验 | `python scripts/verify_skill_refs.py` | I-9 |

## 8. 未纳入范围：recon-ai 影子端点（仅方案）

**问题**：Ch2 §4.3 要求发现 webapp02 的 2 条未公开 location（影子端点），当前 recon-01..07 无对应判据。

**方案 A（推荐）**：并入 recon-05「契约提取」的既有产出——已取的 `/openapi.json` 路径清单与 HTML/JS 引用做差集，命中记入该步「关键输出」，不新增 step_id。
**方案 B**：新增 `recon-08`，需同步七字段资产清单契约与 `docs/contracts/consumers.md`，破坏性变更。

**契约影响**：方案 A 不改 `recon-01..07` 与 `ASSET_FIELDS`，仅扩「关键输出」；方案 B 触发契约版本递增，仍留待后续按 G0 判定。

**状态（2026-11-25）**：方案 A **已实施**——`tools/recon_ai/shadow.py`（离线差集与置信度定级，13 例测试）+ `recon-05`「关键输出」+ `ch2.analyze` 的 `kind=shadow` 观测分支。

## 9. 主线待补声明

本增量按「方案 + 可验证实现」交付，**未执行**完整 11 阶段主线。待补与理由：

| 阶段 | 状态 | 理由 |
|---|---|---|
| 1 research | 部分 | 本方案的一手源为课程文档 Ch11 与靶场手册；对外部权威源（MITRE ATT&CK、Certipy/BloodHound 文档）尚未逐条核实，须在正式落地前补 |
| 2 / 3 to-spec v1 / v2 | 未执行 | 两遍规格须独立留痕（C8），本增量以 SKILL.md 行为规格替代，不等于 to-spec 产物 |
| 4–10 | 未执行 | 依赖 v2 定稿 |
| 11 全量门禁 | 未执行 | 依赖前序阶段 |

据此，`foothold-ad` 当前状态应记为**可执行增量**，不得在 `capstone-rehearse` 中标记为「已就绪」，只能记 `PARTIAL`。

## 10. 最佳实践对齐（无真实环境）

离线模式下没有实时目标可复核，工件即唯一事实源。六项改进把「可追溯、不臆断、可复现」写成机器可验证的约束：

| ID | 改进 | 落点 | 验收 |
|---|---|---|---|
| I-13 | 工件来源与完整性（provenance） | `tools/foothold_ad/provenance.py`、`cli verify`、`RunReport.provenance` | 完整清单退出码 0；篡改或字段缺失退出码 1 且列出不可信文件 |
| I-14 | schema 版本与向前兼容 | `artifact.SCHEMA_VERSION` + `check_schema` + runner 三级处置 | 不支持主版本 → `UNDETERMINED`（非 `BLOCKED`），注记含 `schema_version` |
| I-15 | 未知枚举不推断 | `analyze.TRUST_DIRECTIONS` / `DELEGATION_VALUES` / ESC 签发要求 / EPA | 未知方向、未知委派、缺审批或缺授权签名一律 `UNDETERMINED` |
| I-16 | 畸形与对抗输入 | `load_json` 体积上限、编码、递归深度；负向用例 | 空文件/截断/非 UTF-8/超深/超大/类型错乱六类均不产生假结论 |
| I-17 | 确定性与快照 | `RunReport.digest()` | 同输入两次一致；JSON 键序变化不影响 digest |
| I-18 | 采集前置清单（preflight） | `tools/foothold_ad/preflight.py`、`cli preflight` | 缺失/已存在分层输出；含采集命令、期望字段、依赖步骤 |

**输入质量三级处置**（I-14/I-16 的统一口径）：

1. 文件缺失或损坏（非 UTF-8 / 非 JSON / 超限）→ 依赖步骤 `BLOCKED`，`parse_errors` 记录原因；
2. `schema_version` 不受支持 → 依赖步骤 `UNDETERMINED`，`schema_errors` 记录版本；
3. 已解析但字段缺失或取值未知 → 判据层 `UNDETERMINED`，注记写明缺哪项。

「不可信」不改变判据，只约束**能否作为证据提交**：`provenance.ok=false` 时按 SKILL.md 质量门处理。

## 11. 标准映射（一手源已核实）

| 步骤 | 技术 | 标准编号 | 来源（2026-11-25 核实） |
|---|---|---|---|
| ad-02 / ad-03 | Kerberoasting | T1558.003 | `attack.mitre.org/techniques/T1558/`（子技术列表） |
| ad-03 | AS-REP Roasting | T1558.004 | 同上 |
| ad-05 | DCSync | T1003.006 | `attack.mitre.org/techniques/T1003/` |
| ad-04 | 证书窃取与伪造 | T1649 | `attack.mitre.org/techniques/T1649/` |
| ad-06 | SID 历史注入 / SID 过滤 | T1134.005 | `attack.mitre.org/techniques/T1134/` |
| ad-04 | ESC1 / ESC8 | Certified Pre-Owned（SpecterOps，2021） | `specterops.io/research/certified-pre-owned` |

**判据随之收紧**（对齐官方定义，非新增语义）：

- **ESC1** 需同时满足：无审批**且**无授权签名（原实现只看审批）、可控主体、客户端认证 EKU、低权可注册。任一签发要求字段缺失记 `UNDETERMINED`。
- **ESC8** 需 HTTP 注册端点**且** EPA 未启用（原实现仅看端点存在）。EPA 状态缺失记 `UNDETERMINED`；EPA 已启用不算命中。
