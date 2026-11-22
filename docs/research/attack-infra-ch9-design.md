# 设计记录 — attack-infra Ch9 扩展

> 阶段 6 产物 · 输入：规格 #345 v2、子工单 #347..#353、既有 `tools/attack_infra/` 边界。
> 单一事实源：判据见 `docs/research/attack-infra-ch9-canonical.md`，本文件只记模块/接口/依赖方向。

## 1. seam 决策（与阶段 2 一致）

- **复用唯一 seam**：`RunContext`（既有 `tools/attack_infra/model.py#RunContext`），其 `command` / `transport` / `evidence` / `shot` 为可注入依赖。
- 新增能力不创建第二个注入点；外部世界（云 CLI、kubectl、HTTP、文件）全部经既有四依赖访问。
- 新增模块只接收 `RunContext`，返回既有 `StepVerdict` 同构结论（此处扩展 step_id 命名空间为 `ch9-*`）。

## 2. 模块职责与公开接口

| 模块 | 单一职责 | 公开接口 | 依赖 |
|---|---|---|---|
| `ch9_model` | Ch9 结论类型（凭据指纹、能力矩阵、步骤结论），不 import 本项目模块 | `Ch9Outcome`, `CredFingerprint`, `CapabilityMatrix`, `Ch9Verdict` | 标准库 |
| `ch9_iam` | 解析策略 JSON、trust policy 判定、角色链结论 | `enumerate_policies`, `trust_allows`, `chain_verdict` | `ch9_model`, ctx.command |
| `ch9_k8s` | SA token 路径判定、API URL 构造、跨 ns 规则对比、JWT sub 提取、能力矩阵 | `token_surface`, `same_rules_across_ns`, `jwt_subject`, `capability_matrix` | `ch9_model`, ctx.transport, ctx.command |
| `ch9_secrets` | 五服务凭据指纹化、版本/日志命中 | `hunt_services`, `ssm_old_password`, `filter_log_hits` | `ch9_model`, ctx.command |
| `ch9_container` | Pod 卷只读性判定与请求拦截效果 | `writable_shared_volume`, `intercept_verdict` | `ch9_model`, ctx.transport |
| `ch9_scope` | 范围闸门与 OPSEC 建议集 | `scope_gate`, `opsec_advice` | `ch9_model` |
| `ch9_gpu` | 版本阈值与注入面判定 | `gpu_escape_verdict` | `ch9_model`, ctx.command |

## 3. 依赖方向（单向，无环）

```
ch9_iam / ch9_k8s / ch9_secrets / ch9_container / ch9_scope / ch9_gpu
        ↓ (仅依赖类型与 RunContext 注入)
ch9_model  ←  RunContext(既有)  ←  command / transport / evidence / shot(既有 seam)
```

- 上层能力模块互不 import；`ch9_model` 不 import 任何本项目模块（对齐既有 `model.py` 设计）。
- 对象图构造收敛位置：`tools/attack_infra/runner.py`（既有 runner 扩展注册 Ch9 步骤），不新增第二编排入口。

## 4. 测试替身策略

- `FakeCommand`（返回可编排 `CommandResult`）、`FakeTransport`（返回可编排 `HttpResponse`）复用既有测试夹具。
- 所有模块在替身下离线可跑；不发真实网络请求、不调用真实云 CLI。
- 断言只看 `Ch9Verdict.outcome/reason/command/output` 与证据字段，不测私有辅助函数。

## 5. 权衡与被否决方案

- **否决**：为每个 Ch9 能力建独立 seam（如单独 inject policy provider）——会增加接缝数，违反 §6"seam 越少越好"与阶段 2 结论。
- **否决**：把 Ch9 能力塞进既有 `path_a/b/c`——会改动既有判据与 step_id，违反 §2.3 上游复核与 AC-20。
- **取舍**：GPU 逃逸只做"条件判定 + 降级"，不做实际载荷编译执行；理由：NVD(C-9) 只确认影响面与 CWE，不提供可复现载荷的一手细节，且演练靶场未证实存在（R-3）。

## 6. ADR / 冲突标注

- 无新增 ADR；三层隔离（ADR-0006）由 worktree 与 push 前锁检查承载。
- 未偏离框架矩阵 ⑫（Kali + 云 CLI + 自定义）；无 PyRIT 对象图（D-1/B7）。
