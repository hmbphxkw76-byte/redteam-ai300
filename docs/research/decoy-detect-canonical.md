# decoy-detect 规范事实源（canonical references）

> **性质**：研究/决策文档（非规范正文）。为 `decoy-detect` 技能主线落地（§3.1）锁定实现依赖的一手事实。
> **核验日期**：2026-11-15（GMT+8）。结论先行：**decoy-detect 是环境级诱饵判定技能，非攻击框架，不引入 PyRIT/garak/promptfoo**（对齐矩阵 ⑭）。

---

## 1. 已核实事实（一手源）

| # | 事实 | 来源 | 版本/锚点 |
|---|---|---|---|
| F1 | 考试环境共 10 台主机：2 条攻击链 × 3 链式 + 1 独立 + 1 域控 + **2 台诱饵机（0 分，intentionally not vulnerable）** | OSAI Exam Guide (S3) | `docs/governance/references/OSAI-Exam-Guide-snapshot.md` L131；`GOVERNANCE.md` §2.1 |
| F2 | 8 个计分目标 = 100 分；及格线 75/100 | S3 / S1 | `GOVERNANCE.md` §2.2–§2.3 |
| F3 | 应在前期识别 2 台诱饵机，对疑似诱饵目标「**建议 ≤30 分钟**」时间盒后主动放弃 | S3 | `GOVERNANCE.md` §5.3.2（措辞为「应/建议」） |
| F4 | 诱饵机 = 故意不设漏洞的主机；统一术语「诱饵机」，禁用 GLOSSARY 标注 `_Avoid_` 的废弃术语 | GLOSSARY | `GLOSSARY.md` 诱饵机条目 |
| F5 | 框架组合：纯 Kali/网络侦察 + 人工判定 + 许可 AI 助手；**无 AI 攻击框架** | 框架决策 | `osai-skill-framework-matrix.md` ⑭（D2 / P1） |
| F6 | recon-ai 已提供**单主机** `judge_decoy(present_categories)`：0 类 present AI 组件即判疑似诱饵，返回 `(decoy, reason)` | 既有实现 | `tools/recon_ai/policy.py` `judge_decoy`；`inventory.py` L69 |
| F7 | recon-ai `AssetInventory` 已含 `decoy_suspected` / `decoy_reason` / `timebox_minutes` 字段，可作 decoy-detect 输入契约 | 既有实现 | `tools/recon_ai/model.py` L135–137 |
| F8 | threat-model 为执行前置，decoy-detect 与其诱饵初筛双向衔接复核 | 治理 | `GOVERNANCE.md` §4.5；SKILL.md 第 4 节 |
| F9 | 证据五件套/三件套 + 双通道由 `tools/collect_evidence.py` 唯一提供（C1 单一事实源） | 共享工具 | `tools/collect_evidence.py` 头注释 |

---

## 2. 待核实项与核实闸

- **Q1**：SKILL.md 将时间盒升为「硬性 ≤30min」，与 §5.3 的「建议 ≤30 分钟（应）」不一致。→ 属「应→必须」强化，按 `GOVERNANCE.md` §8.3 在技能/规格中显式记录偏离理由（24h 内空耗 0 分机的失败成本高），不静默偏离。已核实：这是有意 hardening，非错误。
- **Q2**：环境级「≈2 台」全局约束如何与逐主机判定结合。→ 由 decoy-detect 第 4 节「与 threat-model 衔接」做全局计数复核；明显偏离 ≠2 时回查枚举完整性（SKILL.md 失败与豁免第 3 条）。
- **Q3**：recon-ai 的 `judge_decoy` 仅看 AI 组件 presence；decoy-detect 三维度（行为/漏洞缺失/无价值）是其超集。`decoy-detect` 直接复用 `recon_ai.policy.judge_decoy` 作为「行为特征」维度的可机读信号，不重实现（C1）。

---

## 3. 攻击路径 → 对象映射

| 技能路径 | 实现形态 | 对象/模块映射 |
|---|---|---|
| 三维度特征提取 | 纯函数（无 IO） | `tools/decoy_detect/features.py` |
| ≤30min 时间盒 | 时间盒追踪器 | `tools/decoy_detect/timebox.py` |
| 诱饵判定清单 | markdown 生成器 | `tools/decoy_detect/listgen.py` |
| 维度交叉验证 | 判定策略 | `tools/decoy_detect/policy.py` |
| 清单质量门校验 | 校验器 | `tools/decoy_detect/validate.py` |
| 证据落盘 | 委托 `collect_evidence.py` | `tools/decoy_detect/evidence.py`（seam） |
| CLI 入口 | argparse | `tools/decoy_detect/cli.py` |

**无 PyRIT**（B7 以「未引入 PyRIT 命名空间、无 `pyrit.orchestrator`/`*Orchestrator`/`AzureOpenAIChatTarget`」满足；矩阵 ⑭ 明确本技能无 AI 攻击框架）。

---

## 4. 已排除（明确不做）

- 不引入 PyRIT/garak/promptfoo（矩阵 ⑭：本技能纯侦察 + 人工判定）。
- 不含任何攻击利用（SKILL.md 失败与豁免：「仅做识别与判定」）。
- 不重实现 recon-ai 的 `judge_decoy`（C1：复用既有信号源）。

---

## 5. 来源

- OSAI Exam Guide（S3 快照）：`docs/governance/references/OSAI-Exam-Guide-snapshot.md`
- 治理宪法：`docs/governance/GOVERNANCE.md` §2.1 / §5.3 / §8.3
- 框架矩阵：`docs/research/osai-skill-framework-matrix.md` ⑭
- 术语：`GLOSSARY.md`（诱饵机）
- 既有实现：`tools/recon_ai/{policy,inventory,model}.py`
- 共享证据：`tools/collect_evidence.py`
