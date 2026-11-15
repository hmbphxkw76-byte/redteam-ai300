# attack-supply-chain — 工程规格定稿 v2（可验证 / 可拆解）

> **阶段**：主线 阶段3 to-spec②（v1→v2 独立规格化，版本递增）
> **输入**：v1 全文（issue #161 / `docs/specs/attack-supply-chain-spec-v1.md`）；`docs/research/attack-supply-chain-canonical.md`；矩阵 ⑪；GOVERNANCE §8.2；CI-CD S1–S4
> **行为唯一来源**：`skills/attack-supply-chain/SKILL.md`
> **框架组合**：ModelScan + IBM ART + PyRIT(v1.1.0, 证据) + 自定义脚本

---

## 1. 布尔验收条件（AC，替换 v1 的 US 模糊表述）
> 判据格式「给定 X，当 Y，则 Z 成立」；每条附检查方式（命令 / 人工判据）。

### 攻击路径 A/B/C
- **AC-01（sc-01 发现供应链面）**：给定 recon-ai 资产清单，当执行供应链面枚举，则输出含「模型仓库 / 依赖源 / 数据管道端点 / 信任边界」四要素且每要素附端点地址。检查：证据片段字段齐全。
- **AC-02（对照基线）**：给定正常产物，当记录哈希与来源，则输出可复算 sha256 与来源 URL。检查：`sha256sum` 复算一致。
- **AC-03（sc-02 数据集投毒）**：给定语料，当执行投毒，则脚本声明来源，且对 `trigger:target` 生效并产出投毒前后样本计数对照。检查：`dataset_poison.py` + 证据片段计数差 >0。
- **AC-04（sc-03 模型/适配器投毒）**：给定基座模型，当执行投毒，则产出适配器文件，且 ModelScan 扫描该产物报告可检测恶意算子（严重度 ≥ MEDIUM）**或**显式记录未检出原因。检查：`modelscan -r json` 退出码/severity。
- **AC-05（sc-04 管道投毒）**：给定 ETL 管道，当注入 preprocess 变换，则产出注入配置并记录注入点与预期变换。检查：配置文件 diff。
- **AC-06（sc-05 依赖投毒）**：给定包索引，当初次执行投毒，则产出恶意包名+索引地址，且 requirements 解析到恶意包。检查：`pip install --dry-run` 解析结果。
- **AC-07（sc-06 触发）**：给定构建环境，当注入构建钩子，则构建时执行非预期代码并输出执行回显。检查：构建日志含回显串。
- **AC-08（sc-07 下游取证）**：给定同 prompt，当对比投毒前后输出/检索，则输出 diff 且差异可归因于投毒，含 AI 交互日志。检查：证据片段含 before/after + ai-log。
- **AC-09（sc-08 flag）**：给定 AI 向量机立足点，当执行 flag 取证，则 `whoami`/`id` 与 `ai_vector.txt` 内容同屏。检查：截图 + 文本同屏。

### 质量门（GOVERNANCE §6）
- **AC-10 可复现命令**：每步命令可直接 copy/paste，`collect_evidence.py --step <id> --strict` 通过。
- **AC-11 关键输出**：每步含关键输出原文（投毒生效/下游偏移/触发响应）。
- **AC-12 截图**：每步截图含目标标识 + 时间戳。
- **AC-13 投毒前后对照**：产出 before/after。
- **AC-14 下游行为影响**：产出 diff + AI 交互日志（§6.3）。
- **AC-15 flag 双通道**：面板提交值 == 截图/报告正文（§6.2）。
- **AC-16 report-exam 兼容**：证据结构可被 `report-exam` 的 `parse_fragment` 无损解析。

### 失败路径
- **AC-17 无供应链面**：记录判定依据并改走 attack-rag/attack-embeddings，不阻塞其余路径。
- **AC-18 部分生效**：记录命中率**数值**，不夸大。
- **AC-19 被拦截**：记录拦截证据+原因，同一被拦截动作重试 ≤1 次。
- **AC-20 诱饵机**：判定为 0 分/无供应链面后 ≤30 分钟结束并记录依据。

## 2. Testing Decisions（只测外部行为）
- TD-1 证据契约测试复用 `attack-mcp-tool`/`recon-ai` 同形夹具，断言三/五件套字段与 `--strict` 结果。
- TD-2 ModelScan 非充分性测试：干净结果 + 格式外跳过须显式记录「未检出≠安全」（AC-04 分支）。
- TD-3 ART estimator 校验测试：误用 estimator 类型构造即抛错（对应 AC-03/AC-04）。
- TD-4 失败路径逻辑测试：AC-17~AC-20 判定逻辑支持注入假后端，不依赖真实演练目标。
- TD-5 覆盖率：业务代码行覆盖率 ≥80%（CI S2）。

## 3. CI 门禁 → 验收条件映射
| 门禁 | 覆盖 AC | 命令 / 判据 |
|---|---|---|
| B3 语法/构建 | AC-10~AC-16 | `python -m py_compile`；`unittest discover` |
| B4 证据契约 | AC-10~AC-14 | `collect_evidence.py --step --strict`；`test_attack_supply_chain_evidence_contract.py` |
| B5 flag 双通道 | AC-09/AC-15 | 面板值 == 截图同屏（人工判据） |
| B6 CI S1–S4 | AC-16 | 覆盖率 ≥80%；Conventional Commits |
| B7 PyRIT | 全 | `pyrit==1.1.0`；无 `pyrit.orchestrator`/`AzureOpenAIChatTarget` |
| B8 可追溯 | 全 | issue/PR/commit 互链；每条结论附源 |

## 4. Seam 决策（S1–S5，v1 提案 → v2 定案）
- **S1 证据契约 seam（复用）**：`collect_evidence.py --strict` 统一产出三/五件套。
- **S2 投毒引擎 seam（新增）**：适配 IBM ART 投毒类，统一 `poison(dataset|model, trigger, frac) → artifact`；可切换 `PoisoningAttackBackdoor`/`FeatureCollisionAttack`/`GradientMatching`。
- **S3 模型扫描 seam（新增）**：封装 `modelscan` CLI/JSON，返回 `(findings, severity_max, exit_code)`；供 AC-04。
- **S4 注入器 seam（新增）**：统一 `inject(target, payload) → config + expected_effect`，承载依赖抢注/ETL/构建触发（sc-04/05/06）。
- **S5 recon 输入 seam（复用）**：消费 recon-ai 资产清单（JSON）作为 sc-01 起点。
- 对象图：ModelScan（静态扫描）+ ART（投毒）+ PyRIT `SQLiteMemory`/`PrettyAttackResultMemoryPrinter`（证据）；**不含** `pyrit.orchestrator`/`*Orchestrator`/`AzureOpenAIChatTarget`。

## 5. v1 → v2 差异清单（逐条理由）
- D1 US-01~US-20 → AC-01~AC-20 布尔化，每条附检查命令/人工判据（可判定性）。
- D2 新增 §2 Testing Decisions 与 §3 CI 门禁映射（v1 缺失可执行判据）。
- D3 S1–S5 由「提案」收敛为「决策」，固定接口契约（供阶段6/8）。
- D4 对象图明确排他（PyRIT 仅证据；排除 orchestrator 旧对象）。
- D5 待核实项 → 核实闸 A/B/C（承接 research §4）。
- D6 失败路径补阈值（诱饵机 ≤30min；拦截重试 ≤1 次）。

## 6. 核实闸（承接阶段1）
- 闸 A：ModelScan/ART 版本 `pip index versions` 实测回填（阶段8）。
- 闸 B：每自定义投毒脚本来源声明（阶段8 docstring）。
- 闸 C：sc-03 产物 ModelScan 扫描留证（AC-04）。

> 版本：v2 · 2026-11-15 · 取代 v1 作为下游（阶段4/6/8/9/10/11）唯一判据；v1 保留全文于 issue #161 与本目录 `-spec-v1.md`。
