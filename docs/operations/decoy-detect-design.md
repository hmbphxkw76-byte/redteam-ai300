# decoy-detect 设计记录（codebase-design）

> 依据 `docs/operations/skill-mainline-workflow.md` §3.6。决策支持工具，非攻击框架（对齐矩阵 ⑭）。代码位置 `tools/decoy_detect/`。
> 行为唯一来源：`skills/decoy-detect/SKILL.md`。证据格式唯一来源：`tools/collect_evidence.py`（C1）。

## 1. 模块职责与依赖方向（单向，无环）

```
cli.py ──▶ runner（编排，阶段 8 内聚于 cli 的 run()）
            ├─▶ features.extract / classify_dimensions   (纯函数)
            ├─▶ timebox.TimeBoxTracker                    (纯类)
            ├─▶ policy.decide                            (纯函数)
            ├─▶ listgen.render_markdown                  (纯函数)
            ├─▶ validate.validate_quality_gate          (纯函数)
            └─▶ evidence.EvidenceWriter                  (seam → collect_evidence.py)
model.py（数据模型，被所有模块 import，自身不 import 本包任何模块）
```

- `model.py` 为叶子节点（零本项目依赖），保证可纯单测。
- 所有业务逻辑（features/timebox/policy/listgen/validate）为**纯函数/纯类**，IO 仅在 `cli.py` 与 `evidence.py` 发生 → 测试只测外部行为（v2 AC / 阶段 9）。
- `evidence.py` 复用 `recon_ai.evidence.EvidenceWriter` 的「子进程调用共享收集器」模式（C1：不重实现证据格式）。

## 2. 公开接口（深模块，仅两个入口）

- `cli.main(argv) → int`（退出码：0 完成且质量门通过 / 1 质量门或契约违规 / 2 用法错误）
- 业务 API（供测试直接调用，不依赖 CLI）：
  - `features.extract(inventory: dict) -> HostSignals`
  - `features.classify_dimensions(signals: HostSignals) -> List[Dimension]`
  - `timebox.TimeBoxTracker`（start/stop/elapsed/exceeded）
  - `policy.decide(hit, cross_validated) -> JudgmentConclusion`
  - `listgen.render_markdown(judgments, expected_decoys=2) -> str`
  - `validate.validate_quality_gate(judgments, timebox_limit) -> List[str]`

## 3. seam 清单（与阶段 2 提案一致）

| seam | 位置 | 形态 |
|---|---|---|
| 输入 seam | `features.extract` | 消费 recon-ai `AssetInventory` JSON（`decoy_suspected`/`decoy_reason`/`present_categories`） |
| 证据 seam | `evidence.py` | 委托 `collect_evidence.py`（C1 单一事实源） |
| 输出 seam | `listgen.render_markdown` | markdown 清单，5 字段，可被 `report-exam` 引用 |

## 4. 对象图构造收敛

单入口 `cli.run()` 运行时装配：`TimeBoxTracker` → 对每台主机 `extract` → `classify_dimensions` → `TimeBoxTracker` 计时 → `policy.decide` → 收集 `DecoyJudgment` → `validate_quality_gate` → `listgen.render_markdown` → 逐条 `EvidenceWriter.emit`。无 PyRIT 对象图（B7 满足）。

## 5. 复用既有信号（C1，不重实现）

- `recon_ai.policy.judge_decoy(present_categories)`：作为「行为特征」维度的可机读信号源；`features.extract` 读取 `AssetInventory.decoy_suspected` 字段，不直接调用 judge_decoy（输入已是 recon-ai 产物）。
- `recon_ai.model.AssetInventory`：`load_inventory(path)` 解析其 JSON（`tools/decoy_detect/model.py` 提供轻量 loader，仅读字段，不依赖 recon_ai 包以保证解耦）。

## 6. 权衡与被否决方案

- **不引入 PyRIT/garak/promptfoo**：矩阵 ⑭ 明确本技能无 AI 攻击框架；判定是确定性规则，无需 LLM judge（B7 满足）。
- **不重实现 recon-ai 的 judge_decoy**：C1 单一事实源；decoy-detect 是环境级超集（时间盒 + 三维度超集 + 全局对账）。
- **测试覆盖业务模块而非 CLI IO**：IO 分支用临时夹具 + 假 collect_evidence（subprocess 隔离）覆盖，保证覆盖率 ≥80% 且不断言实现细节。
