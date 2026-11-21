## Summary

Closes #292

Ch4 A2A 对齐全量主线落地（11 阶段全 PASS）：

```text
threat-model      → 四模式/框架风险/三层信任边界/四类向量
recon-ai          → recon-05 Agent Card 只读探针 + OpenAPI/注册端点补录 + SIEM 基线
attack-multi-agent→ 六类 A2A 攻击面 + 字段级判据 + 收尾/防御映射
tools/recon_ai    → _agent_card() + judge_agent 优先级（既有信号优先）
tests/recon_ai    → test_recon_ai_a2a.py（5 tests）
docs/operations   → 设计/实现/TDD/审查/推送前评审/本 PR
```

能力域：D10 / D2 / D4；优先级：P1 / P0 / P1；目标计分单元：通用 / 通用 / AI向量机。

## Evidence

- 改前：三技能缺 C1–C20 逐项对照；recon-05 无 `/.well-known/agent.json` 探针。
- 改后三 SKILL.md（checker 口径 LF 字节）：5916 / 11957 / 11743，均 ≤12000。
- 红：A2A 4 tests，2 FAIL（探针缺失、card 未判存在）；绿：4 OK；阶段 10 补共存用例后 5 OK。
- recon group 93 OK；attack-multi-agent 证据契约 3 OK 且 `a2a-01..08` 恰好 8 次调用。
- 全量 897 tests OK (skipped=3)；覆盖率 89.3%。
- S1：`check_token_budget` / `validate_skill` / `check_glossary` / 契约清单+消费者 / `tools_compile` / `evidence_contract` / `checkout_lock` 全 PASS；markdownlint 0 issues。

## Merge Danger

- 单向门：不新增 step_id；七字段资产清单契约与 `collect_evidence.py` 共享契约不回退。
- 双向门：attack-multi-agent 通过资产 ID / `loot/recon-05-agent-sys.md` 引用 recon-ai 枚举产物，不重复命令定义。
- 影响半径：3 个 SKILL.md、1 个 probes.py、1 个新测试、6 个新文档；无共享文件改动。
- V4 显式偏离：recon-ai 未接入 garak 首扫，理由见 `a2a-ch4-mainline-design.md`。
- V3 人工核实闸：真实演练目标与 SIEM 需授权取证；本地静态校验不替代实跑。

## End-to-end demo

`recon-05` 读取 Agent Card → recon-05/07 证据片段 → threat-model 标注模式/边界 → attack-multi-agent 执行六类攻击面并按字段判据取证 → `report-exam` 无损复用。

## 契约变更清单

- 变更元素：无（未改 `collect_evidence.py` / `docs/contracts/**` / step_id / 七字段契约）。
- before→after：证据片段字段契约不变；recon-05 新增只读 Agent Card 请求但仍复用 recon-05 step_id。
- 受影响消费者：`report-exam`、`verify-evidence`、`loot-manage` 按既有字段继续消费；attack-multi-agent 改为引用 recon-ai 枚举产物。
- 兼容：向后兼容；无契约版本变更；`check_contract_manifest --check` 与 `check_contract_consumers --check` PASS。
