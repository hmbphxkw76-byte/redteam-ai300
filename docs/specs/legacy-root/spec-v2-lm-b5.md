## 工程规格定稿 (v2) — loot-manage Ch9 B5 六服务凭据指纹加固

> 本文为 issue #385 规格 v1 的工程定稿（v2），v1 全文保留；差异见文末。

### 验收条件（布尔化）

| ID | 布尔验收条件 | 检查命令/判据 | B5 |
|---|---|---|---|
| AC-01 | 六服务枚举 S3/SecretsManager/SSM/CloudWatch/ModelRegistry/ECR 全部可登记，content 含服务标签+前缀+长度+位置 | 单测六服务参数化 | B5-1/2/5 |
| AC-02 | 明文前缀（裸/双引号/单引号含 `:=@/` 或 >8 字符）被拒，reason=plaintext_rejected，登记簿不变 | 单测三形态 | P-1 |
| AC-03 | 缺服务/位置/长度/主机 → ok=False 且 reason 明确，登记簿不变 | 单测四路径 | — |
| AC-04 | `CloudFingerprintVerdict` frozen；reason 属枚举；非法构造抛 ValueError | 单测 | P-2 |
| AC-05 | 登记簿保持 8 列、类型=凭据、编号 L-<n>、`parse_registry` PASS | 单测 + registry.validate | B5-4 |
| AC-06 | `verify_evidence.from_loot` 从登记簿还原 step_id/host/evidence 路径与登记输入一致，且 `fragment_pieces` 三件套齐全 | 单测（临时片段文件） | B5-3 |
| AC-07 | report-exam 消费的 8 列 schema 与双通道/状态列零漂移 | git diff + 单测 | B5-3 |
| AC-08 | dict 兼容 `v["ok"]`/`v.get("content")` 有效，轻量版 7 例零回归 | 单测 | — |
| AC-09 | 新增模块行覆盖率 ≥90% | `python scripts/verify_lm_b5_coverage.py --min 90` | 本轮门槛 |
| AC-10 | SKILL.md Ch9 段引用模块/函数/路径字面存在 | `python scripts/verify_lm_b5_skill_refs.py` | 收口要求 |
| AC-11 | registry.py / verify-evidence / report-exam / 既有 loot-01..04 零 diff | git diff 核对 | P-4 |
| AC-12 | 全量 unittest 零回归；glossary/validate/budget 全 PASS | 实跑 | — |

### 测试决策
- 只断言外部行为；六服务参数化 + 明文三形态 + 下游 from_loot 实测；覆盖率 tracer 复用共享脚本（C1）。

### 门禁映射
AC-01..08 → 单测(S2)；AC-09 → 覆盖率脚本；AC-10 → 引用核验；AC-11/12 → diff + 全量门禁。

### 风险闸
- R-1：服务/位置锚点为教学级枚举，真实值由上游注入，本模块不虚构；不阻断。
- P-4：不执行云 API、不改下游判据；不阻断。

### v1→v2 差异
1. 10 条 US 收敛为 12 条布尔 AC；2. AC-06 明确下游 from_loot 无损回溯实测；3. AC-02 明确明文三形态；4. AC-04 明确 frozen + shim；5. AC-09 门槛 80%→≥90%；6. AC-10 明确引用逐条核对。
