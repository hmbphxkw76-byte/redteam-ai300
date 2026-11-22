# loot-manage Ch9 B5 云凭据指纹登记加固事实索引

> **版本** v1.0 · **状态** 已核实 · **性质** 本轮加固单一可信源
> **取证日期** 2026-11-22 · **上游轻量版** `docs/research/loot-manage-ch9-canonical.md`（L-1..L-4，保留）
> **框架组合（矩阵 ⑧）** 结构化凭据库 + 许可 AI；无攻击框架。

## 0. 结论
1. B5 的核心是**六服务凭据来源可追溯**：S3 / SecretsManager / SSM / CloudWatch / ModelRegistry / ECR 猎取所得凭据，登记为「前缀 + 长度 + 位置」指纹，明文一律禁止落盘。
2. 轻量版（PR #360）只支持通用 `(prefix,length,location)`、dict 返回、无服务分类、无来源追溯、无 ≥90% 覆盖——本轮升级为类型化 `CloudFingerprintVerdict` + 六服务枚举 + 来源字段 + 下游无损回溯实测。
3. 登记簿 8 列 schema 与证据片段契约不变：`verify_evidence.from_loot` 消费 `parse_registry`/`parse_dual`/`fragment_pieces`，本轮保证这些字段零漂移（B5-3）。

## 1. 已核实清单

| # | 事实 | 来源 |
|---|---|---|
| B5-1 | SecretsManager `GetSecretValue` 返回 `SecretString`/`SecretBinary`（敏感字段，不入 CloudTrail），需 `secretsmanager:GetSecretValue` | <https://docs.aws.amazon.com/cli/latest/reference/secretsmanager/get-secret-value.html>（一手，取证 2026-11-22） |
| B5-2 | SSM `GetParameter` 对 `SecureString` 用 `--with-decryption` 返回明文 `Value`，授权 `ssm:GetParameter` | <https://docs.aws.amazon.com/cli/latest/reference/ssm/get-parameter.html>（一手，取证 2026-11-22） |
| B5-3 | 下游 `verify_evidence.from_loot` 只消费既有判据：`id`→step_id、`host`、`evidence`→片段路径、`dual`→panel/shot、`status`→taken、`fragment_pieces` 三件套 | 本仓 `tools/verify_evidence.py:302-340`（一手实现） |
| B5-4 | 登记簿固定 8 列，类型 ∈{凭据,会话,flag}，编号 L-<n>，主机不得为空 | 本仓 `tools/loot_manage/registry.py:15-22,236`（一手） |
| B5-5 | 五服务（S3/CloudWatch/ModelRegistry/ECR + Lambda env）凭据面已在 Ch9 canonical 核实 | 本仓 `docs/research/attack-infra-ch9-canonical.md` C-4/C-10/C-11（C1 指针，不复述） |
| B5-6 | 框架组合 ⑧ 无攻击框架 | `docs/research/osai-skill-framework-matrix.md` ⑧ |

## 2. 六服务枚举与来源追溯

| 服务 | 指纹位置锚点 | 一手依据 |
|---|---|---|
| S3 | s3-bucket-policy / s3-env | B5-5 |
| SecretsManager | secretsmanager-secret | B5-1 |
| SSM | ssm-secure-parameter | B5-2 |
| CloudWatch | cloudwatch-logs | B5-5 |
| ModelRegistry | model-registry | B5-5 |
| ECR | ecr-repo-credentials | B5-5 |

`来源追溯` = (服务, 位置锚点, 来源主机, 证据片段路径) 四元组，全部进入登记簿既有列（content 含服务/位置，host/evidence 原样），不新增列（B5-4）。

## 3. 判据前提与陷阱
- **P-1 明文禁落盘**：content 只含前缀(≤8 字符且无 `:=@/`)+长度+位置；明文取值一律拒绝，包括引号包裹形式。
- **P-2 类型化**：`CloudFingerprintVerdict` frozen dataclass（不可变路由字段 + dict 兼容 shim）。
- **P-3 无损回溯**：登记后 `verify_evidence.from_loot` 产出的 step_id/host/evidence/pieces 与登记输入一致（实测，非声明）。
- **P-4 零回归**：registry 8 列、既有 loot-01..04 与轻量版测试零 diff；不引入 AI 框架。

## 4. 待核实 / 已排除
- **R-1**：服务名与位置锚点为教学级枚举，实际凭据值由上游 attack-infra 观测注入，本模块不虚构；不阻断。
- **D-1**：不执行云 API 调用、不新增登记簿列、不改动 verify-evidence/report-exam 判据。

## 5. 门禁记录（阶段 1）

| 编号 | 本阶段变更项 | 判定 | 复验命令 | 结论 |
|---|---|---|---|---|
| B7 | B5-6 零 AI 框架 | 符合 | `grep -rnE "pyrit\.orchestrator|Orchestrator" tools/loot_manage/ch9_b5*.py` → 无 | PASS |
| B8 | B5-1..B5-6 带来源 | 符合 | `grep -c "https://\|本仓\|矩阵" docs/research/loot-manage-b5-hardening-canonical.md` | PASS |
| B9 | 框架组合 ⑧ | 符合 | `sed -n '91,96p' docs/research/osai-skill-framework-matrix.md` | PASS |

**阶段结论**：`PASS`。复验：`python scripts/check_glossary.py && python scripts/validate_skill.py`。
