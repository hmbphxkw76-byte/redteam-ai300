# attack-infra Ch9 扩展实现事实索引

> **版本** v1.0 · **状态** 已核实 · **性质** attack-infra Ch9 扩展单一可信源
> **取证日期** 2026-11-22（GMT+8）· **取证方式** 一手官方源抓取（命令/URL 逐条留痕）
> **上游** `skills/attack-infra/SKILL.md` · `docs/research/attack-infra-canonical.md`（F-1..F-21，既有判据不改动）
> **课程源** `D:\视频\OffSec   AI-300 Advanced AI Red Teaming\Ch9-AI-Infrastructure-and-Deployment-Exploits.html`（Listing 号即本文引用锚点）
> **职责边界** 只记录 Ch9 扩展手法所依赖的事实；不复制 GOVERNANCE 条款 / GLOSSARY / B1–B8 定义（C1）。

---

## 0. 结论摘要

1. Ch9 的两条攻击链（云 IAM 提权链、K8s 身份链）依赖的 API 语义均可在一手官方文档核实，且不与既有 F-1..F-21 判据冲突。
2. CVE-2025-23266 由 NVD/CNA（NVIDIA）确认：NVIDIA Container Toolkit ≤1.17.7、CWE-426 不可信搜索路径、CVSS 3.1 基分 9.0，影响面为容器初始化 hook 以提权执行任意代码；与 Ch9 演示的 toolkit 1.17.7 一致。
3. `sts:GetCallerIdentity` 官方明确"无需权限、显式拒绝亦返回同样信息"——支持 Ch9 Tip；但 CloudTrail 噪声属 Ch9 教学断言，一手 AWS 文档仅确认"管理员可通过 CloudTrail 审计"，噪声量化标为待核实 R-1。
4. 既有 `tools/attack_infra/` 不实现以下任何手法（grep 实证见 §4）：SSRF、assume-role、SecretsManager/SSM/CloudWatch 服务侧列举、SA token 读取、SelfSubjectRulesReview 原始调用、Argo 身份链、sidecar/init、GPU。故全部为新增模块，非改写既有判据。

---

## 1. 已核实清单（一手源逐条）

| # | 事实 | 来源（URL，逐条命中） | 输出摘要 / 课程锚点 |
|---|---|---|---|
| C-1 | `aws sts assume-role --role-arn <ARN> --role-session-name <NAME>` 返回临时凭据；源身份须持 `sts:AssumeRole`；会话默认 1h，role chaining 上限 1h | <https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-cli.html> | 「role chaining – using permissions from a role to access a second role」；Listing 2/8/10/14 |
| C-2 | trust policy 中 `Principal: {"AWS":"arn:aws:iam::<acct>:root"}` 表示账户内主体，配合自身 `sts:AssumeRole` 即可扮演 | 同上（trust policy 示例段 + `Principal` 语义） | Listing 8「root principal = any principal in the account」 |
| C-3 | ABAC 用 `aws:ResourceTag/<key>` 条件键按资源标签授权；描述类动作（如 `ec2:DescribeInstances` / `List*`）常以 `Resource:"*"` 授权，无法按资源标签收窄 | <https://docs.aws.amazon.com/IAM/latest/UserGuide/access_tags.html> | 示例策略中 `ec2:DescribeInstances` 的 `Resource:"*"`；Listing 6/9/29 |
| C-4 | `aws sts get-caller-identity` 返回 UserId/Account/Arn，**No permissions are required**；显式 deny 仍可执行（拒绝与成功返回同一信息） | <https://docs.aws.amazon.com/cli/latest/reference/sts/get-caller-identity.html> | 「Permissions are not required because the same information is returned when access is denied」；Listing 1 + Tip |
| C-5 | `iam:PassRole` 不应以 ResourceTag 控制授权（官方明确做法不可靠） | <https://docs.aws.amazon.com/IAM/latest/UserGuide/access_tags.html> | 「Do not try to control who can pass a role by tagging the role…does not have reliable results」；Listing 6/9 的 PassRoleToSageMaker |
| C-6 | Pod 默认由 SA admission controller 挂载 projected volume：serviceAccountToken(path=token) + ca.crt(ConfigMap) + namespace(downwardAPI)；容器内三文件可读；TokenRequest 令牌默认 1h 绑定 Pod | <https://kubernetes.io/docs/reference/access-authn-authz/service-accounts-admin/> | 「Any container within the Pod that mounts this particular volume can access the above information」；Listing 39/42 |
| C-7 | v1.24 前自动创建 Secret 型长期 SA token；手动创建 Secret 可获"永不过期"token；JWT `sub` 形如 `system:serviceaccount:<ns>:<name>` | 同上（Manual Secret management / legacy 段） | Listing 47/48 的 argo-controller-token 解码 |
| C-8 | `kubectl auth can-i --list --namespace=foo` 列出全部允许动作；`--as=system:serviceaccount:dev:foo -n prod` 冒充 service account（需 impersonation 权限） | <https://kubernetes.io/docs/reference/kubectl/generated/kubectl_auth/kubectl_auth_can-i/> | 「List all allowed actions in namespace "foo"」；Listing 40/43 |
| C-9 | CVE-2025-23266：NVIDIA Container Toolkit ≤1.17.7（CDI 模式，1.17.5 前）与 GPU Operator ≤25.3.0 受影响；初始化 hook 可提权执行任意代码；CWE-426；CVSS 3.1 = 9.0 CRITICAL（AV:A/AC:L/PR:L/UI:N/S:C/C:H/I:H/A:H） | <https://nvd.nist.gov/vuln/detail/CVE-2025-23266>（Source: NVIDIA Corporation，Published 2025-07-18） | Listing 58/图 7 的 toolkit 1.17.7 + runc 链；CWE-426 不可信搜索路径 ↔ LD_PRELOAD 注入面 |
| C-10 | CloudWatch Logs filter pattern：大小写敏感；`%regex%` 正则；支持 `|` OR；filter patterns 用于 FilterLogEvents / subscription / metric filters | <https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/FilterAndPatternSyntax.html> | Listing 24/25 + Tip（FilterLogEvents 精确过滤） |
| C-11 | SSM Parameter Store 为 Systems Manager 工具之一，用于"Securely store data referenced by applications"；Parameter Store 含 String/SecureString 类型 | <https://docs.aws.amazon.com/systems-manager/latest/userguide/param-store.html>（经 what-is-systems-manager 页确认工具集） | Listing 19-21；String 类型无需 KMS、版本历史含旧口令属课程断言（R-2） |

---

## 2. Ch9 要求 ↔ 一手事实 ↔ 实现映射

| 步骤 | Ch9 Listing | 一手事实 | 成功判据（布尔化） | 失败分支 |
|---|---|---|---|---|
| iam-01 IAM 角色与策略枚举 | L5-7 | C-3/C-5 | 能列出 inline/attached 策略并解析 Statement[].Action/Resource/Condition | 无 IAM 读权限 → AUTH_REQUIRED |
| iam-02 trust policy 可扮演判定 | L8-10 | C-1/C-2 | trust policy Principal 为账户 root/自身且策略含 sts:AssumeRole → 可 assume | 明确 Deny → BLOCKED |
| iam-03 角色链提权 | L11-14、图 3 | C-1/C-3 | 链末端角色含 `*:*` 或跨项目 ARN → 记录为提权成功；每跳产出凭据指纹 | 链断 → 记录断点，不夸大 |
| k8s-01 SA token 读取与端点构造 | L39/42-43 | C-6 | 三文件( token/ca.crt/namespace )存在且 KUBERNETES_SERVICE_HOST/PORT 可读 → 可构造 API | automountServiceAccountToken=false → ABSENT |
| k8s-02 跨 namespace 权限判定 | L43-44 | C-8 | 两个 namespace 的 SelfSubjectRulesReview 规则一致 → 判为 ClusterRole | 规则不同 → namespaced Role，记差异 |
| k8s-03 身份链（读+写） | L47-52、Table 2 | C-7/C-8 | 身份 A 能读 secrets、身份 B 能 create pods → 组合判为可接管集群 | 缺任一能力 → 记录不足，不判接管 |
| sec-01 五服务凭据狩猎 | L15-28 | C-4/C-10/C-11 | 每服务至少一类命中，凭据仅产指纹（前缀+长度+位置） | 命中但无读权限 → 记范围，不落明文 |
| ctr-01 sidecar/init 共享卷拦截 | L54-55 | C-6（同 Pod 共享卷事实） | 存在 readOnly:false 的共享卷且可被 sidecar exec → 判可篡改 | 全只读 → ABSENT |
| gpu-01 GPU 逃逸 | L56-63、图 7 | C-9 | toolkit 版本≤1.17.7 且存在 hook/LD_PRELOAD 注入面 → EXPLOITED 候选；无靶场 → BLOCKED | 无 GPU 工具链 → BLOCKED，不伪造 |

---

## 3. 判据前提与陷阱

- **P-1 只读优先**：云侧列举/读取与单次推理为默认动作；写操作（assume-role 后的变更、模型加载/卸载）须显式开关（对齐既有 canonical P-4 与 SKILL.md infra-02..05）。
- **P-2 凭据只产指纹**：任何服务命中的凭据均只记前缀+长度+位置，明文不落片段（既有 AC-09 / D-3）。
- **P-3 范围闸门**：发现跨项目资源（如 Rainy Day）时，只读发现可记录，主动利用须有扩权依据；无依据即 BLOCKED 并留痕（Ch9 Warning L739/L1190；本项目无对应治理条款，故以 SKILL.md 失败与豁免承载）。
- **P-4 目标侧回显判定**：`id`/`whoami` 命中本机身份不判目标侧成功（既有 path_c `_echo_is_local`，AC-11），GPU/C2 复用同一判据。

---

## 4. 待核实（R）

| # | 事项 | 取证方式 |
|---|---|---|
| R-1 | Ch9「GetCallerIdentity 生成 CloudTrail 噪声」的量化依据 | 一手 AWS 文档仅确认可审计；噪声量属教学断言，实现中按 OPSEC 建议处理但不写死量化 |
| R-2 | SSM 参数版本历史含旧口令、`String` vs `SecureString` 的 KMS 差异细节 | 需 `aws ssm get-parameter-history` 一手命令页；实现中只按 Ch9 Listing 21 结构解析，不扩展语义 |
| R-3 | CVE-2025-23266 的 Go hook 空环境继承 / runc setenv 技术细节 | NVD 只给 CWE-426 与影响版本；实现按 Ch9 Listing 58/图 7 描述编码，技术细节以课程源为据并标注「课程源，非 NVD 逐字」 |

---

## 5. 已排除（D）

- **D-1** 引入 `pyrit.orchestrator` / `*Orchestrator` / `AzureOpenAIChatTarget`：既有 canonical D-1 与 B7 禁用；Infra/Cloud 手法框架普遍缺席（矩阵 ⑫），无需 PyRIT 对象图。
- **D-2** 明文凭据落片段：既有 AC-09 / D-3 禁止。
- **D-3** 改写既有 infra-01..08 判据与五值结论：本扩展为新增模块，既有判据保持（§2.3 上游复核）。

---

## 6. 门禁记录（阶段 1）

| 编号 | 检查项 | 依据 | 实测（命令 + 摘要） | 判定 | 结论 |
|---|---|---|---|---|---|
| B7 | PyRIT 版本与对象图 | §2.1 | `grep -rn "pyrit\.\|Orchestrator" docs/research/attack-infra-ch9-canonical.md` → 仅 D-1 排除项 | 符合 | PASS |
| B8 | 可追溯性 | §2.1 | C-1..C-11 每条带官方 URL；R-1..R-3 带取证方式 | 符合 | PASS |
| B9 | 框架选型合规 | §1.4 | 已读两份框架资料；矩阵 ⑫= Kali+云CLI+自定义，本文所有模块走云 CLI / kubectl / 标准库，无 PyRIT 对象 | 符合 | PASS |
| AC-1 | 每条结论可定位一手源 | §3.1 | 「来源」列无空值 | 符合 | PASS |
| AC-2 | 版本号明确 | §3.1 | toolkit≤1.17.7 / GPU Operator≤25.3.0（C-9）；pyrit 不引入 | 符合 | PASS |
| AC-3 | 每条攻击路径有映射 | §3.1 | §2 表覆盖 iam-01..03/k8s-01..03/sec-01/ctr-01/gpu-01（9/9） | 符合 | PASS |
| AC-4 | 待核实项命名 + 取证方式 | §3.1 | R-1..R-3 | 符合 | PASS |
| AC-5 | 落盘 docs/research/ | §3.1 | 本文件 | 符合 | PASS |

**阶段结论**：`PASS`。复验命令：`python scripts/check_glossary.py && python scripts/validate_skill.py && python -m unittest discover -s tests -t .`。
