## Problem Statement

既有 C1 轻量版（PR #366）只覆盖 EC2/SG 暴露面与版本关联（Listing 29-30、32），缺 Listing 31「未鉴权模型端点探测」；且返回裸 dict、无类型化五值语义、无七字段资产清单对齐、无 ≥90% 覆盖率门槛。编排层与评审者无法机器复核三类观察的只读边界与端口约束。

## Solution

升级 `ch9_cloud_surface.py` 为类型化 `C1Verdict` + 三判定（analyze_instance / probe_unauth_endpoint / correlate_version），新增 Listing 31 未鉴权端点判定；保持被动优先、active 才追加定向端口（≤8）、只读、零网络调用、不落明文凭据；提供七字段资产清单无损映射；覆盖率 ≥90% 复用共享 tracer。

## User Stories

1. 作为演练者，我想枚举 EC2 公网实例与 0.0.0.0/0 ingress，以便定位云暴露面（L29-30）。
2. 我想探测模型端点在未带鉴权头时是否返回模型元数据，以便确认未鉴权访问面（L31）。
3. 我想把模型服务器版本关联到 CVE 查询建议，以便排优先级（L32）。
4. 我想全程只读、被动优先，主动探测仅 ≤8 端口，以便不越界（C1-6）。
5. 我想凭据只留前缀/占位，不落明文，以便合规。
6. 作为评审者，我想判定结果可映射为七字段资产清单且不丢字段，以便报告复用。
7. 作为质量负责人，我想覆盖率 ≥90%，以便满足本轮门槛。
8. 作为评审者，我想 SKILL.md 引用逐条字面存在，以便端到端复核。
9. 作为维护者，我想轻量版 dict 访问零回归，以便不破坏既有调用方。
10. 作为编排者，我想不新增 step_id，以便兼容 recon-01..07 清单契约。

## Implementation Decisions

- 新增 `ch9_c1_model.py`：`C1Verdict` frozen dataclass + dict shim；outcome 取五值语义子集（EXPOSED_NO_AUTH/AUTH_REQUIRED/ABSENT/BLOCKED）。
- 重写 `ch9_cloud_surface.py`：保留两个公开函数与旧 dict 访问；新增 `probe_unauth_endpoint`；命令仅为数据字符串，判定层零网络。
- 新增 `ch9_c1_asset.py#to_asset_fields`：把 verdict 映射为七字段（credential_hint 只指纹）；不改 `Asset`/`ASSET_FIELDS`。
- 不新增 step_id；C1 作为 recon-01 云侧旁路观测在 SKILL.md 留痕。
- 独立覆盖脚本 `verify_ra_c1_coverage.py` 复用 `measure_coverage.measure()`，零共享文件改动。

## Testing Decisions

- 只断言外部行为：verdict 字段、七字段映射、约束（无 shell=True/无 socket/端口上限常量）。
- 覆盖三判定命中/缺项/拒绝/明文不落盘/七字段无损/dict shim；离线。
- 覆盖率 tracer 复用共享脚本，≥90%。

## Out of Scope

- 不执行云 API / 网络请求 / 主动扫描（判定层纯函数）。
- 不新增 step_id；不改 recon-01..07 判据与七字段契约。
- 不引入 PyRIT 或任何 AI 框架参与判定（矩阵 ⑥）。

## Further Notes

- 事实见 `docs/research/recon-ai-c1-hardening-canonical.md`（C1-1..C1-7、P-1..P-4）。
- 上游轻量版 `recon-ai-ch9-canonical.md` 保留，本轮只升级实现质量与补 Listing 31。
