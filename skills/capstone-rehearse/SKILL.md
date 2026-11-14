---
name: capstone-rehearse
priority: P2
domain: D11
scoring_unit: 通用
trigger: 所有 P0/P1 技能已就绪，且进入考前演练窗口（§5.4），需对 §4.5 编排流水线做一次全谱系走查
input: 各技能就绪状态（threat-model/recon-ai/foothold/链式 AI 利用/独立机/loot/域控/verify/report）、§4.5 流水线定义、§5.4 24h 节奏
output: 演练报告（覆盖度矩阵 / 24h 节奏时间线 / 缺口与补强清单），供 report-exam 引用、考前针对性补强
---

# capstone-rehearse — Capstone 演练

考前综合演练。在所有 P0/P1 技能就绪后，按 **§4.5 编排流水线**（threat-model → recon-ai → foothold → 链式 AI 利用 → 独立机 → loot → 域控 → verify → report）全谱系走查一遍，验收能力覆盖度与 **24h 节奏（§5.4）** 是否可执行，产出覆盖度/缺口/时间节奏报告。

## 执行体

按「流水线全谱系走查 → 24h 节奏映射 → 缺口清单 → 演练报告」四节推进；如实标注未覆盖阶段，不得假称全覆盖。

### 1. 流水线全谱系走查

1. 逐阶段核对 §4.5 九个阶段，确认对应技能已就绪且证据链贯通：
   - `threat-model`（D10）高价值排序 → `recon-ai` 资产枚举 → `foothold-traditional`（D1）入口/横向/提权 → 链式 AI 利用（`attack-rag` D5 / `attack-embeddings` D6 / `attack-multi-agent` D4 / `attack-infra` D9 / `attack-supply-chain` D8 / `attack-mcp-tool` D7 / `attack-ai-agent` D3）→ 独立机 → `loot-manage` 战利品 → 域控 `proof.txt` 单次提交 → `verify-evidence` 全量校验 → `report-exam` 报告。
2. 对每个阶段产出「就绪 / 未就绪」标记，未就绪项进入缺口清单。
3. 核对证据链：上游产物（如 recon 资产清单）能被下游（如 threat-model 排序、report-exam 引用）无损消费。

### 2. 24h 节奏映射（§5.4）

1. 为每阶段估算耗时（含诱饵机 ≤30min 时间盒 §5.3、传统链、AI 利用、域控、校验、报告）。
2. 绘制 24h 时间线，标注关键节点（如第 0h 起 threat-model、第 Xh 起 foothold、最后 N h 留给 verify+report）。
3. 若累计耗时 > 24h，给出**压缩/取舍建议**（如并行阶段、优先 AI 向量机/独立机高杠杆目标）。

### 3. 缺口清单

1. 汇总未就绪阶段、薄弱点（如某 attack 子技能缺 S2 夹具、证据链断点）。
2. 对每项缺口给出**补强建议**（对应技能迭代、证据契约加固）。
3. 明确「不影响及格的缺口」与「阻断性缺口」分级。

### 4. 演练报告产出

1. 汇总覆盖度矩阵 + 24h 时间线 + 缺口清单，产出结构化演练报告（markdown）。
2. 报告可被 `report-exam` 的演练/附录部分直接引用。
3. 结论含「是否具备实战条件」的明确判定。

## 质量门

以下产出**必须**全部具备，缺失任一即判定未过门禁：

- **覆盖度矩阵**：§4.5 每一阶段标注 就绪/未就绪，含证据链贯通核对。
- **24h 节奏时间线**：各阶段耗时 + 关键节点 + 超 24h 时的压缩建议。
- **缺口与补强清单**：未覆盖项 + 分级（阻断性/非阻断）+ 补强建议。
- 落盘片段与 `report-exam` 可衔接（复用 `loot-manage` 索引习惯）。

## 校验标准

- 演练过程可被技术读者 **copy/paste 逐步复现**（§6.1），走查路径与节奏有据可查。
- 产出与 `report-exam` 的演练/附录引用、`verify-evidence` 的验收直接兼容。
- 术语符合 `GLOSSARY.md`（用规范词，禁用 `_Avoid_` 废弃术语）。

## 失败与豁免

- 若某阶段技能未就绪，明确标注缺口而非假称覆盖；不把「未演练」写成「已通过」。
- 若 24h 节奏超出，给出压缩/取舍方案，不隐瞒超时风险。
- 本技能仅做演练验收，**不含真实考试利用**；所有结论须结合实战环境验证。
