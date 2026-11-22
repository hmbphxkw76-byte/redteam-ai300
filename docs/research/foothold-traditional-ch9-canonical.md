# foothold-traditional Ch9 扩展事实索引

> **版本** v1.0 · **状态** 已核实 · **性质** Ch9 初始访问扩展单一可信源
> **取证日期** 2026-11-22 · **上游** `skills/foothold-traditional/SKILL.md`
> **课程源** `Ch9-AI-Infrastructure-and-Deployment-Exploits.html`（Listing 1-2、56-57、图 7）

## 0. 结论摘要
1. Ch9 的云侧初始访问以 SSRF 读 `/proc/self/environ` 取 Lambda 临时凭据为入口（Listing 1），属"公网入口利用"阶段，符合本技能 D1 定位。
2. GPU 立足点场景为 SSH 受限账号 + `sudo -l` 列出包装脚本（Listing 56-57），提权本体（CVE-2025-23266）已在 attack-infra ch9-gpu 实现；本技能只承担立足点枚举前段。

## 1. 已核实清单
| # | 事实 | 来源 |
|---|---|---|
| T-1 | `sts:GetCallerIdentity` 无需权限、显式 deny 亦返回同信息（凭据验证 infallible） | <https://docs.aws.amazon.com/cli/latest/reference/sts/get-caller-identity.html> |
| T-2 | `curl "…/api/export?template_url=file:///proc/self/environ"` 经 SSRF 读环境变量（课程教学命令） | Ch9 Listing 1（课程源，非厂商文档） |
| T-3 | `sudo -l` 列出 NOPASSWD 包装脚本，为提权入口枚举标准手法 | Ch9 Listing 56（课程源）；Kali OSCP 工具链（矩阵 ⑦） |
| T-4 | 框架组合 = 纯 Kali OSCP 工具链 + 自定义，AI 框架零参与 | `docs/research/osai-skill-framework-matrix.md` ⑦ |

## 2. 映射
| 步骤 | Ch9 | 成功判据（布尔） | 失败分支 |
|---|---|---|---|
| trad-09 SSRF 凭据入口 | L1-2 | 响应含 AWS_ACCESS_KEY_ID/SECRET/SESSION_TOKEN 键名 → 产指纹（不落明文） | 无键名 → ABSENT |
| trad-10 GPU 立足点枚举 | L56-57 | `sudo -l` 含 NOPASSWD 包装脚本 → 记录入口 | 无 → ABSENT |

## 3. 门禁记录（阶段 1）

| 编号 | 本阶段变更项 | 判定 | 复验命令 | 结论 |
|---|---|---|---|---|
| B7 | 新增 T-4（框架组合：零 AI 框架） | 符合 | `grep -nE "pyrit\.orchestrator|AzureOpenAIChatTarget" tools/foothold_traditional/` → 无 | PASS |
| B8 | 新增 T-1..T-4（各带来源） | 符合 | `grep -c "https://" docs/research/foothold-traditional-ch9-canonical.md` → ≥2 | PASS |
| B9 | 组合取矩阵 ⑦ 纯 Kali | 符合 | `sed -n '85,89p' docs/research/osai-skill-framework-matrix.md` | PASS |

**阶段结论**：`PASS`。复验：`python scripts/check_glossary.py && python scripts/validate_skill.py`。
