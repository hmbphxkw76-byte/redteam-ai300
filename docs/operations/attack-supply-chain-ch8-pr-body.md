## 变更摘要

Ch8 差距 G1–G14 全量落地：sc-09..14 独立步骤注册表（不改 `STEP_IDS`）+ 12 个确定性本地模块，覆盖 MCP 源码后门、Pickle RCE、格式矩阵、投毒放大、LoRA、Tokenizer、扫描器绕过、隐身后门与八类登记；SKILL.md 增执行体与边界。规格 #336，工单 #337–#343。

```
change → tools/attack_supply_chain/{12 new modules}
        → tests/attack_supply_chain/{7 new tests}
        → skills/attack-supply-chain/SKILL.md (+sc-09..14, +3 boundaries)
        → scripts/tools_manifest.json (register)
call   → ch8_steps.run_ch8(step, ctx) → module (纯函数, runner 可注入)
verify → alignment --render → 14/14 PASS
```

## 纳管信息

- **组件类型**：`skill`（D8 / P0）
- **目标计分单元**：`AI向量机`
- **端到端演示**：`alignment --render` 14/14 PASS；`unittest test_ch8_steps -v` 六步全绿；覆盖率 87.7%。

## 治理合规自检

- [x] 已按 §4.2 五要素解剖编写（front-matter 七字段 + 执行体/质量门/校验标准/失败与豁免）
- [x] 术语符合 `GLOSSARY.md`（无 `_Avoid_` 废弃术语；零新增术语，复用既有条目）
- [x] 本地已通过：`python scripts/validate_skill.py && python scripts/check_glossary.py && python scripts/check_token_budget.py --check`
- [x] 本地测试通过：全量 1,062 OK(skipped=3)；Ch8 46 例 OK；覆盖率 89.7%≥80%

## 契约变更清单

**变更元素**：无（共享证据契约 contract v3 未改）。before→after：证据字段语义不变。
**受影响**消费者：`report-exam` / `verify-evidence`（sc-09..14 沿用 `--step --strict` 三/五件套；既有 sc-01..08 与 `parse_fragment` 回归通过，test_ch8_contract.py 3 例）。
**兼容**性判定：完全兼容，无迁移；`tools_manifest.json` 仅登记新模块/测试，无语义变更。

## Evidence

- 对齐验证矩阵：14/14 PASS（G1–G14 每行含课件锚点 / 实现文件 / 测试 / 证据四元组），见 `python -m tools.attack_supply_chain.alignment --render`。
- 静态门禁：validate_skill 16 技能 PASS；check_glossary 66 废弃术语 PASS；token_budget PASS；check_tools_compile 211 文件 0 失败；markdownlint 0 issues。
- 测试：全量 1,062 OK(skipped=3)；Ch8 46 例；覆盖率 89.7%≥80%。

## Merge Danger

- 单向门：既有 `STEP_IDS`（len==8）与 sc-01..08 证据片段结构不得扩展；新步骤只在独立注册表 `ch8_steps.STEP_IDS_CH8`。
- 双向门：SKILL.md 执行体与 `alignment.py` 的 ROWS 四元组须同步；新增模块须同步 `tools_manifest.json` 才计入覆盖率。
- 影响半径：仅 attack-supply-chain 技能与 manifest 登记；不改共享文件（GLOSSARY.md / check_token_budget.py / ci.yml 等），无并行会话冲突。
