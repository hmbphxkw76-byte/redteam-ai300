## Problem Statement

既有 B5 轻量版（PR #360）只支持通用 `(prefix, length, location)` 三元组与裸 dict 返回：无六服务分类（S3/SecretsManager/SSM/CloudWatch/ModelRegistry/ECR）、无一手源支撑的服务→位置锚点映射、无类型化结论、无下游 `verify-evidence.from_loot` 无损回溯实测、覆盖率未达本轮 ≥90%。演练者无法凭登记簿证明凭据来源可追溯，评审者也无法机器复核。

## Solution

在既有 `tools/loot_manage/ch9_cloud.py` 之上加固：新增 `ch9_b5_model.py` 定义 `CloudFingerprintVerdict`（frozen dataclass）+ 六服务枚举 + 来源四元组；`register_cloud_fingerprint` 升级为类型化返回并接受服务参数；content 仍为「前缀…(len=N) @ 位置」，但前缀携带服务标签以形成来源追溯；保持 8 列 schema 与证据片段契约不变；新增下游无损回溯实测测试与 ≥90% 覆盖率核验。

## User Stories

1. 作为演练者，我想把 S3/SecretsManager/SSM/CloudWatch/ModelRegistry/ECR 六服务猎取凭据登记为指纹，以便不漏证。
2. 我想每条指纹含服务+位置+来源主机+证据片段路径，以便可追溯。
3. 我想明文（含引号包裹）一律被拒且不落盘，以便合规。
4. 作为评审者，我想 `verify_evidence.from_loot` 能从登记簿无损还原 step_id/host/evidence/三件套，以便报告复用。
5. 作为评审者，我想 report-exam 消费的登记簿 8 列 schema 零漂移，以便零迁移。
6. 作为质量负责人，我想覆盖率 ≥90%，以便满足本轮门槛。
7. 作为维护者，我想轻量版 dict 访问零回归，以便不破坏既有调用方。
8. 作为评审者，我想 SKILL.md 引用的每个工具/函数字面存在，以便端到端复核。
9. 作为演练者，我想无效输入（缺服务/位置/主机、明文前缀）被标明确 reason，以便编排层降级。
10. 作为质量门负责人，我想既有 loot-01..04 判据零 diff，以便零回归。

## Implementation Decisions

- 新增 `ch9_b5_model.py`：`CloudFingerprintVerdict`（frozen + `__getitem__`/`.get` shim）、`CLOUD_SERVICES` 六值枚举、`SOURCES` 服务→位置锚点映射。
- 重写 `ch9_cloud.py`：`register_cloud_fingerprint(text, prefix, length, location, host, evidence, service=..., timestamp="")` 返回 verdict；保留旧签名兼容（service 默认通用）。
- 明文拒绝覆盖裸值/双引号/单引号三种形态（复用前轮加固教训）。
- 不改 `registry.py` 任何列/状态/校验语义；content 格式扩展为 `服务:前缀…(len=N) @ 位置`（服务标签为枚举字面，非明文）。
- 新增 `scripts/verify_lm_b5_coverage.py` 复用 `measure_coverage.measure`（不改共享 manifest），与 `scripts/verify_lm_b5_skill_refs.py`。

## Testing Decisions

- 只断言外部行为：verdict 字段、登记簿文本、下游 `from_loot` 输出，不测私有辅助。
- 覆盖六服务 × 明文三形态 × 缺项 × 下游回溯 × dict shim；FakeCommand 离线。
- 覆盖率 tracer 复用共享脚本，目标 ≥90%。

## Out of Scope

- 不执行云 API 调用；不新增登记簿列；不改动 verify-evidence/report-exam/registration 判据。
- 不引入 PyRIT 或任何 AI 框架（矩阵 ⑧）。

## Further Notes

- 事实见 `docs/research/loot-manage-b5-hardening-canonical.md`（B5-1..B5-6、P-1..P-4）。
- 上游轻量版事实 `loot-manage-ch9-canonical.md` 保留，本轮只升级实现质量与来源追溯。
