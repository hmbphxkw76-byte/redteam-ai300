# recon-ai Ch9 云基础设施侦察扩展事实索引

> v1.0 · 已核实 · 上游 `skills/recon-ai/SKILL.md` · 课程源 Ch9 L1169-1292（Listing 29-32）
> 框架组合取矩阵 ⑥（garak 首扫 + Kali + 许可 AI；只读侦察，不利用）。

## 0. 结论
Ch9 云侧侦察含两类既有 recon-ai 7 步未覆盖的只读观察：EC2 实例枚举与安全组 ingress 暴露面（L29-30）、模型服务器版本号→已知 CVE 关联（L32）。二者均为只读，不违反 recon-ai「不执行攻击/不做爆破」边界。

## 1. 已核实
| # | 事实 | 来源 |
|---|---|---|
| R-1 | `aws ec2 describe-instances` 只读列举实例与标签 | Ch9 L1169/Listing 29（课程源）；矩阵 ⑥ Kali/云 CLI |
| R-2 | `aws ec2 describe-security-groups` 暴露 0.0.0.0/0 ingress | Ch9 L1222/Listing 30 |
| R-3 | `curl <vLLM>/version` 返回精确版本号以对齐已知 CVE | Ch9 L1280-1292/Listing 32 |
| R-4 | recon-ai 边界：只读、不新增 step_id 除非留痕 | `skills/recon-ai/SKILL.md` 功能边界 |

## 2. 映射
| 能力 | 成功判据 | 失败分支 |
|---|---|---|
| cloud-surface | 实例有 PublicIp 且 SG 含 0.0.0.0/0 → 暴露面命中 | 无公网 IP → ABSENT |
| version-cve | 版本字符串可由 endpoint 取得 → 记录版本 + CVE 查询建议 | 无版本 → ABSENT |

## 3. 门禁（阶段 1）
| 编号 | 变更项 | 判定 | 复验命令 | 结论 |
|---|---|---|---|---|
| B7 | R-4 只读无框架 | 符合 | `grep -nE "pyrit\.orchestrator\|Orchestrator" tools/recon_ai/ch9_cloud_surface.py` → 无 | PASS |
| B8 | R-1..R-4 带来源 | 符合 | `grep -c "Ch9\|矩阵" docs/research/recon-ai-ch9-canonical.md` | PASS |
| B9 | 矩阵 ⑥ | 符合 | `sed -n '79,83p' docs/research/osai-skill-framework-matrix.md` | PASS |
