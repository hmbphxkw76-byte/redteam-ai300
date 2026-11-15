# attack-supply-chain 实现一手源核实（canonical）

> **性质**：研究/核实文档（非规范正文）。作为 `skills/attack-supply-chain/SKILL.md` 主线落地的阶段 1 输入。
> **核验日期**：2026-11-15（GMT+8）。
> **框架组合（取自矩阵条目 ⑪）**：**ModelScan**（模型/pickle 恶意代码检测）+ **IBM ART**（投毒/提取/规避全谱）+ **PyRIT v1.1.0**（证据编排 `SQLiteMemory`）；自定义脚本覆盖依赖/命名空间抢注与数据管道注入。
> **对齐标准**：OWASP Agentic ASI04（Agentic Supply Chain Vulnerabilities）+ OWASP LLM03（训练数据投毒）/ LLM05（供应链）。
> **冲突优先级**：官方考试事实（S1/S2/S3）> GOVERNANCE 必须条款 > CI-CD 门禁 > 本规范。本核实文档低于上述，且不与 `osai-skill-framework-matrix.md` ⑪ 冲突。

---

## 1. 总体结论

`attack-supply-chain` 不是单一框架可覆盖的场景。PyRIT 在供应链面**非主角**（决策文档 §3.1 已核实其无原生供应链攻击策略，仅做证据编排）；**ModelScan + IBM ART 是该面的权威主控**，自定义脚本补 PyRIT/ART 覆盖盲区（依赖抢注、ETL 注入、构建触发）。

对象映射总表（攻击路径 → 工具）：

| SKILL 路径 | 工具/手段 | 角色 |
|---|---|---|
| sc-01 发现供应链面 | `recon-ai` 资产清单 + `curl`/`pip index` 自定义枚举 | 复用 recon |
| sc-02 数据集投毒 | **IBM ART** 投毒攻击（`FeatureCollisionAttack`/`GradientMatching`/`PoisoningAttackBackdoor`）+ 自定义 `dataset_poison.py` | 攻击 |
| sc-03 模型/适配器投毒 | **IBM ART** 后门/特征碰撞投毒 + 自定义 `model_poison.py`；产出产物经 **ModelScan** 静态扫描留证 | 攻击 + 扫描留证 |
| sc-04 数据管道投毒 | 自定义 `pipeline_poison.py`（ETL/preprocess 注入） | 攻击 |
| sc-05 依赖/包投毒 | 自定义 `dep_poison.py`（typosquat/替换）+ `pip index` | 攻击 |
| sc-06 构建/运行时触发 | 自定义 `trigger_poison.py`（setup/构建钩子执行非预期代码） | 攻击 |
| sc-07 下游模型行为影响取证 | 投毒前后输出/检索 diff + **PyRIT `SQLiteMemory`** 结构化证据 + AI 交互日志 | 证据编排 |
| sc-08 flag 取证（AI向量机） | `whoami`/`id`/`find ai_vector.txt` + PyRIT 证据 seam | 取证 |

---

## 2. 工具事实（逐条核实）

### 2.1 ModelScan（Protect AI，现 Palo Alto Prisma AIRS）
- **仓库/许可**：`github.com/protectai/modelscan`，Apache-2.0（核实于 Protect AI README 与 aisecreviews 复核）。
- **本质**：机器学习模型文件的**静态分析扫描器**，针对模型序列化攻击（Model Serialization Attack）——反序列化时自动执行嵌入代码。它**逐字节读取模型文件、不加载/不执行模型代码**，因此安全。
- **支持格式**：H5、Pickle（PyTorch `torch.save`/`torch.load`、sklearn/XGBoost 经 cloudpickle/dill/joblib）、TensorFlow `SavedModel`、Keras H5/V3。safetensors 无执行面，非 pickle 解析目标。
- **CLI/API 事实**：`pip install modelscan`；`modelscan -p /path/to/model`；JSON 输出 `-r json -o results.json`；**退出码** 0=干净、1=发现问题、其余为扫描错误/用法错误（CI 门控可据此分支）；严重度分级 CRITICAL/HIGH/MEDIUM/LOW。
- **版本**：PyPI 报告 **0.8.8**（2026-11）；最后一次提交 2026-02。→ **待核实**：安装时 `pip index versions modelscan` 复核当前版本，考试前复测。
- **能力边界（硬限制）**：纯静态、签名/算子扫描器，非沙箱、非行为分析；**无法捕获全新混淆后门**；未覆盖格式会跳过（用 `--show-skipped` 查看）。干净结果 = "未发现已知不安全算子"，非"可证明安全加载"。

### 2.2 IBM ART — Adversarial Robustness Toolbox（Trusted-AI，现 Linux Foundation）
- **仓库/许可**：`github.com/Trusted-AI/adversarial-robustness-toolbox`，MIT。
- **四类威胁覆盖**：evasion（规避，40+ 攻击）、**poisoning（投毒）**、extraction（提取）、inference（推理/成员/属性推断、MIFace、DatabaseReconstruction）。
- **投毒攻击实现**（位于 `art/attacks/poisoning/`）：`PoisoningAttackBackdoor`、`CleanLabelBackdoor`、`PoisoningAttackSVM`、`FeatureCollisionAttack`、`BullseyePolytope`、`AdversarialEmbedding`、`HiddenTriggerBackdoor`、`GradientMatching`、`SleeperAgentAttack`、`BadDet`。
- **防御/检测**（位于 `art/defences/detector/poison/`）：`ActivationDefence`、`SpectralSignatureDefense`、`RONI`、`ProvenanceDefense`——可用于 sc-07 投毒前后行为/中毒样本取证对照。
- **API 事实**：统一接口 `Attack.attack_params`/`set_params`/`_estimator_requirements`；投毒类 `poison(x, y=None, **kwargs)`；**estimator 类型在构造期即校验**（`_estimator_requirements`），误用立即抛错。支持 TF2+/PyTorch/Keras/sklearn/XGBoost/LightGBM/CatBoost。
- **版本**：**v1.20.1（2025-07）**（register-ai-security-tooling-landscape 复核，状态 active）。→ **待核实**：考试前复测 `pip index versions adversarial-robustness-toolbox`。

### 2.3 PyRIT（证据编排内核，非攻击主角）
- **版本/对象图**：`pyrit==1.1.0`（以 `docs/research/pyrit-canonical-references.md` 为单一可信源；本技能**不使用** `pyrit.orchestrator`/`*Orchestrator`/`AzureOpenAIChatTarget`）。
- **在 SC 的角色**：仅以 `SQLiteMemory` + `PrettyAttackResultMemoryPrinter` 产出结构化、可逐步复现证据，对应 SKILL 强制的 `tools/collect_evidence.py` 证据契约；不在 SC 发起多轮攻击编排。
- **对齐决策文档 §3.1**：PyRIT 在 SC 仅做证据补位，不替代 ModelScan/ART。

---

## 3. 已核实 / 待核实 / 已排除

### 已核实
- ModelScan：静态扫描、不执行模型、CLI/JSON/退出码/严重度分级、格式覆盖、Apache-2.0、仓库归属。
- IBM ART：四类威胁、投毒攻击具体类名、防御检测器类名、构造期 estimator 校验、MIT、跨框架支持。
- PyRIT：v1.1.0 仅证据角色，SC 不启用攻击对象图。
- 框架组合与矩阵条目 ⑪ 一致（B9 合规）。

### 待核实（实现前取证闸）
- ModelScan 当前 PyPI 版本（报告 0.8.8）——实现时 `pip index versions modelscan` 复核。
- IBM ART 当前版本（报告 v1.20.1）——实现时 `pip index versions adversarial-robustness-toolbox` 复核。
- 自定义脚本（`dataset_poison.py`/`model_poison.py`/`pipeline_poison.py`/`dep_poison.py`/`trigger_poison.py`）的"须记录来源"——每个示意脚本须注明出处（论文/官方示例/自研），禁止无来源投毒实现。
- ModelScan 对 legacy 非 zip `.bin` 的规避报道（2026-07 单研究者 PoC）——作为扫描局限记录在 SKILL 质量门，不阻断。

### 已排除
- **promptfoo**（MCP/agent 固化层）：SC 非其主控场景，矩阵 ⑪ 未纳入；不在本技能使用。
- **garak**（首扫层）：SC 非模型层漏洞扫描，矩阵 ⑪ 未纳入。
- 纯 Kali 工具链：SC 属 AI 场景，主控为 ModelScan/ART，Kali 仅作辅助网络 recon（sc-01）。

---

## 4. 实现前取证闸（G0 §2.1 B8 留痕点）
- 闸 A：ModelScan / ART 版本在安装时以 `pip index versions` 实测回填本表。
- 闸 B：每个自定义投毒脚本的来源声明（论文/官方示例/自研）落地于脚本 docstring 与 SKILL 注释。
- 闸 C：sc-03 产出产物须经 ModelScan `--show-skipped` 扫描并留证，证明恶意载荷可被静态检测（攻击有效性的反向证据）。

## 5. 参考源（一手优先）
- ModelScan README：`github.com/protectai/modelscan`
- IBM ART：`github.com/Trusted-AI/adversarial-robustness-toolbox`；投毒模块 `art/attacks/poisoning/`、检测 `art/defences/detector/poison/`
- PyRIT 规范：`docs/research/pyrit-canonical-references.md`
- 框架决策与矩阵：`docs/research/osai-ai300-framework-decision.md` §3.1、`docs/research/osai-skill-framework-matrix.md` 条目 ⑪
- 交叉复核：aisecreviews（ModelScan 复核）、register-ai-security-tooling-landscape（ART v1.20.1）、bestaisecuritytools（ModelScan 角色）

---

## 6. 阶段门禁记录（G0 · 阶段1 research）

> 依据 `docs/operations/skill-mainline-workflow.md` §2。本阶段仅校验 B7/B8/B9（§3.1 规定）。

| 编号 | 检查项 | 依据 | 实测结果（命令 + 输出摘要） | 判定 | 不符合项描述 | 修正要求 | 复验结果 | 结论 |
|---|---|---|---|---|---|---|---|---|
| B7 | PyRIT 版本与对象图 | §2.1 B7；`pyrit-canonical-references.md` | SC 技能仅以 PyRIT `SQLiteMemory` 做证据编排，未使用 `pyrit.orchestrator`/`*Orchestrator`/`AzureOpenAIChatTarget` | 符合 | — | — | — | — |
| B8 | 可追溯性 | §2.1 B8 | 全文逐条结论附源 URL（ModelScan README / ART 仓库 / 决策文档 §3.1 / 矩阵 ⑪）；issue/PR 互链于后续阶段建立 | 符合 | — | — | — | — |
| B9 | 框架选型合规 | §2.1 B9；矩阵 ⑪ | 组合 = ModelScan + IBM ART + PyRIT(v1.1.0)，取自矩阵条目 ⑪；PyRIT 仅证据补位，未越界到攻击主角 | 符合 | — | — | — | — |

- **上游复核（§2.3）**：本阶段为流程第 1 阶段，无上游交付物；N/A。
- **不符合项**：0。
- **阶段结论**：**PASS**（B7/B8/B9 全项符合，无不符合项）。

### 门禁索引（issue 评论口径 · T5）
阶段1 / 结论 PASS / 不符合项 0 / 复验命令：`python scripts/check_glossary.py`（B8 术语于阶段7 复验）；版本闸见 §4 闸 A/B/C。
