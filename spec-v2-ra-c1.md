## 工程规格定稿 (v2) — recon-ai Ch9 C1 云暴露面加固

> 本文为 issue #392 规格 v1 的工程定稿（v2），v1 全文保留；差异见文末。

### 验收条件（布尔化）

| ID | 布尔验收条件 | 检查命令/判据 | Ch9 |
|---|---|---|---|
| AC-01 | 实例有 PublicIp 且 SG ingress `0.0.0.0/0` → `EXPOSED_NO_AUTH` + 端口列表（有序去重） | 单测 | L29-30 |
| AC-02 | 仅私网 IP / 仅私网 CIDR → `ABSENT(none_found)` | 单测 | — |
| AC-03 | 无鉴权头响应 200 + 模型/版本元数据 → `EXPOSED_NO_AUTH`；401/403 → `AUTH_REQUIRED`；空响应 → `ABSENT` | 单测三分支 | L31 |
| AC-04 | 版本字符串（裸/JSON）→ 记录版本 + NVD/CVE 查询建议（含 CVE-2025-23266 锚点）；无版本 → `ABSENT` | 单测 | L32 |
| AC-05 | `C1Verdict` frozen；outcome 属五值子集；非法 reason 抛 ValueError | 单测 | P-1 |
| AC-06 | 判定层零网络零命令执行；命令仅数据字符串；`shell=True`/`socket`/`requests` 不在模块 | 源码 grep + 单测 | C1-6 |
| AC-07 | 不落明文凭据：`credential_hint` 只含前缀/占位，明文值不出现 | 单测 | C1-7 |
| AC-08 | `to_asset_fields` 产出七字段齐全且与 `ASSET_FIELDS` 一致；不改 `Asset` 契约 | 单测 | C1-5 |
| AC-09 | 不新增 step_id；recon-01..07 `STEP_SPECS` 数量与判据零 diff；`MAX_ACTIVE_PORTS=8` 不变 | 单测 + git diff | P-4 |
| AC-10 | dict 兼容 `v["outcome"]`/`v.get("version")` + 轻量版 7 例零回归 | 单测 | — |
| AC-11 | 新增模块行覆盖率 ≥90% | `python scripts/verify_ra_c1_coverage.py --min 90` | 本轮门槛 |
| AC-12 | SKILL.md Ch9 段引用逐条字面存在；全量 unittest + 门禁全 PASS | `verify_ra_c1_skill_refs.py` + 实跑 | 收口 |

### 测试决策
- 只断言外部行为；离线无网络；七字段映射用真实 `ASSET_FIELDS` 对照；覆盖率 tracer 复用共享脚本（C1）。

### 门禁映射
AC-01..10 → 单测(S2)；AC-11 → 覆盖率脚本；AC-12 → 引用核验 + 全量门禁。

### 风险闸
- R-1：端点是否真未鉴权由运行时观测确认，本模块只判传入响应；不阻断。
- P-4：不新增 step_id、不执行主动扫描；不阻断。

### v1→v2 差异
1. 10 条 US 收敛为 12 条布尔 AC；2. AC-03 三分支明确 L31 未鉴权语义；3. AC-08 明确七字段无损；4. AC-09 锁定 step_id/端口上限；5. AC-11 门槛 80%→≥90%；6. AC-12 明确引用核对。
