# foothold-traditional Ch9 加固事实索引（A3 SSRF + C2 GPU 立足点）

> **版本** v1.0 · **状态** 已核实 · **性质** 本轮加固单一可信源
> **取证日期** 2026-11-22 · **上游** `skills/foothold-traditional/SKILL.md`
> **既有轻量版** `docs/research/foothold-traditional-ch9-canonical.md`（T-1..T-4；本轮不推翻，仅升级实现质量）
> **课程源** `Ch9-AI-Infrastructure-and-Deployment-Exploits.html`（Listing 1-2、56-63）

## 0. 结论
1. A3 云 SSRF 入口的事实基础已由 AWS 一手源确认：Lambda 运行时**定义** `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` / `AWS_SESSION_TOKEN` 三个环境变量（来自执行角色），且官方建议敏感值改用 Secrets Manager——说明 env 泄漏是真实风险面。
2. C2 GPU 逃逸的"初始立足点"指以受限账号 SSH 到 GPU 主机、经 `sudo -l` 找到 NOPASSWD 包装脚本；提权本体（CVE-2025-23266，NVIDIA Container Toolkit ≤1.17.7，CWE-426，CVSS 9.0）已在 `docs/research/attack-infra-ch9-canonical.md` C-9 核实，本轮只做立足点环节，不重复提权。
3. 既有轻量版（PR #357）返回裸 `dict`、无 `collect_evidence.py --strict` 落盘、无五值 verdict 类型、覆盖率未测——本轮为加固，不改 Ch9 事实判据。

## 1. 已核实清单（一手源逐条）

| # | 事实 | 来源（URL / 锚点） | 课程锚点 |
|---|---|---|---|
| H-1 | Lambda 运行时定义 `AWS_ACCESS_KEY_ID`、`AWS_SECRET_ACCESS_KEY`、`AWS_SESSION_TOKEN`（来自 execution role）；敏感值官方建议改用 Secrets Manager | <https://docs.aws.amazon.com/lambda/latest/dg/configuration-envvars.html> — 原文：「AWS_ACCESS_KEY, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN – The access keys obtained from the function's execution role」 | Listing 1-2 |
| H-2 | `sts:GetCallerIdentity` 无需权限，显式 deny 亦返回同信息；返回 UserId/Account/Arn | <https://docs.aws.amazon.com/cli/latest/reference/sts/get-caller-identity.html> — 「No permissions are required to perform this operation…the same information is returned when access is denied」 | Listing 1 |
| H-3 | CVE-2025-23266：NVIDIA Container Toolkit ≤1.17.7、CWE-426 不可信搜索路径、CVSS 3.1=9.0；初始化 hook 提权执行任意代码 | 本仓 `docs/research/attack-infra-ch9-canonical.md#1 C-9`（NVD/CNA 已核实，C1 指针引用不复述） | Listing 56-63 |
| H-4 | foothold-traditional 框架组合 = 纯 Kali OSCP 工具链 + 自定义，AI 框架零参与 | `docs/research/osai-skill-framework-matrix.md` ⑦ | — |
| H-5 | 每步证据三件套（命令/输出/截图）+ 五值结论 + flag 双通道为不可豁免（C8） | `AGENTS.md#C8`；`docs/contracts/collect_evidence.contract.md#1` | — |
| H-6 | `collect_evidence.py --strict` 在三件套不全时退出码 1；`--shot-cmd` 满足截图要件（钩子记录） | `tools/collect_evidence.py:168`（`has_shot = bool(screenshot) or bool(shot_cmd)`） | — |

## 2. 映射（要求↔事实↔判据）

| 步骤 | Ch9 | 成功判据（布尔） | 失败分支 |
|---|---|---|---|
| trad-09 SSRF→env harvest | L1-2 | SSRF 响应含 H-1 三键名 → EXPLOITED/EXPOSED_NO_AUTH 候选，且仅产指纹（前缀/长度/位置） | 无键名→ABSENT(none_found)；被拒→AUTH_REQUIRED(forbidden) |
| trad-10 GPU 立足点 | L56-63 | `sudo -l` 含 `(root) NOPASSWD:` 包装脚本 → 记录入口，与 H-3 提权条件可衔接 | 无 NOPASSWD→ABSENT(none_found)；无 shell→AUTH_REQUIRED(no_tool) |
| 身份验证（可选） | L1 | `GetCallerIdentity` 返回 Arn → 提权 EXPLOITED（H-2 无需权限） | 无 Arn→不夸大 |

## 3. 判据前提与陷阱
- **P-1 指纹化**：凭据值一律 `_redact` 后才进 output；fingerprints 只含键名+长度+位置（对齐既有 D-2/AC-09）。
- **P-2 五值结论**：`outcome ∈ {ABSENT, AUTH_REQUIRED, EXPOSED_NO_AUTH, EXPLOITED, BLOCKED}`，reason 取既有枚举。
- **P-3 证据不可豁免**：每步必须经 `collect_evidence.py --strict` 落盘三件套；`shot_cmd` 作为截图钩子记录（H-6）。
- **P-4 立足点边界**：本技能只判"可达提权入口"，不执行 CVE-2025-23266 载荷（属 attack-infra ch9-gpu，H-3）。

## 4. 待核实 / 已排除
- **R-1**：`/api/export?template_url` 的确切参数名与响应形态属课程源可复现命令，非 AWS 公开 API；实现按 Ch9 Listing 1 字面编码，标"课程源"。
- **D-1**：不引入 PyRIT/任何 AI 框架（H-4）；不实现 GPU 提权本体（H-3/P-4）；不落明文凭据（P-1）。

## 5. 门禁记录（阶段 1）

| 编号 | 本阶段变更项 | 判定 | 复验命令 | 结论 |
|---|---|---|---|---|
| B7 | 新增 H-4（零 AI 框架） | 符合 | `grep -rnE "pyrit\.orchestrator|Orchestrator" tools/foothold_traditional/` → 无 | PASS |
| B8 | H-1..H-6 各带来源 | 符合 | `grep -c "https://\|本仓\|AGENTS.md" docs/research/foothold-traditional-ch9-hardening-canonical.md` | PASS |
| B9 | 框架组合取矩阵 ⑦ | 符合 | `sed -n '85,89p' docs/research/osai-skill-framework-matrix.md` | PASS |

**阶段结论**：`PASS`。复验：`python scripts/check_glossary.py && python scripts/validate_skill.py`。
