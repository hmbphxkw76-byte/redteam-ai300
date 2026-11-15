# attack-embeddings 工程规格定稿 v2（可验证 / 可拆解 / 可交接）

> 输入：规格 v1（issue #158 上文）+ 阶段 1 调研（`docs/research/attack-embeddings-canonical.md`，G0 PASS）
> 版本：v1 → v2（递增）。本版本把「做什么」收敛为可判定、可拆解的定稿；行为与 v1 一致，不引入新行为。
> 框架组合（矩阵 ⑨）：vec2text + PyRIT(v1.1.0) + 自定义脚本。

## 1. 验收条件（每条 User Story → 布尔判据 + 检查命令/人工判据）

| AC | 来源 US | 布尔验收条件 | 检查命令 / 人工判据 |
|---|---|---|---|
| AC-1 | US-1 | `curl <API>/v1/models` 或本地夹具返回模型清单，且含 ≥1 个 embedding 模型条目 | `pytest tests/test_attack_embeddings.py -k test_surface_enumeration` |
| AC-2 | US-2 | 探测文本提交后返回 JSON 含 `dimensions` 与 `model` 字段；baseline 相似度记录落盘 | `pytest -k test_probe_dimensions`；人工核验 loot 基线文件 |
| AC-3 | US-3 | `Vec2TextInverter` 对合成 32-token 样本 exact-match 率 ≥ 0.5（本地夹具，记录对照 S-1 的 92%）；输出还原文本 | `pytest -k test_invert_exact_match`；人工核验还原率报告 |
| AC-4 | US-4 | `MembershipInference.noisy_neighbors` 对 member/non-member 困惑度差的 ROC AUC ≥ 0.65（本地夹具，对照 S-7 的 0.73） | `pytest -k test_membership_auc`；人工核验 AUC 曲线 |
| AC-5 | US-5 | `AdversarialEmbedder` 扰动后目标查询 top-k 相似度偏移 ≥ 阈值 或 检索排名变化；输出 before/after | `pytest -k test_adversarial_shift`；人工核验偏移量 |
| AC-6 | US-6 | `VectorLookup.query(store, concept, topk)` 返回 ≥1 文档块含源文本；越权场景返回未授权文档 | `pytest -k test_vector_lookup`；越权命中为人工判据 |
| AC-7 | US-7 | `RagImpactDiff` 产出 baseline vs manipulated 检索差异，且含 AI 交互日志路径 | `pytest -k test_rag_impact`；人工核验日志路径 |
| AC-8 | US-8 | emb-08 证据含 `whoami`/`id` + `ai_vector.txt` 内容同屏；flag 双通道一致或可经校验预言机等价 | `pytest tests/test_<name>_evidence_contract.py`；人工核验双通道 |
| AC-9 | US-9 | 各证据步骤含可 copy/paste 命令；tests 端到端复现无外部依赖（仅本地夹具） | `pytest tests/test_attack_embeddings.py` 全绿 |
| AC-10 | US-10 | 每步三件套齐全；evidence_contract 断言「命令+输出+截图」三件套与 AI 交互日志 | `pytest tests/test_attack_embeddings_evidence_contract.py` |
| AC-11 | US-11 | 降级路径（无接口/部分生效/被拦截/诱饵机）有对应处理且不空耗（诱饵机 ≤30min 结束） | `pytest -k test_fallback_paths`；人工核验降级日志 |

## 2. 测试决策（只测外部行为）

- 反演/MIA/对抗/向量库/下游影响均测**可观测结果**（还原率、AUC、相似度偏移、命中、差异），不断言内部 token 替换算法。
- 既有参考夹具：`tests/` 中 `collect_evidence` 的 evidence_contract 模式；参考 `attack-rag` 夹具。
- 主测试面：本地合成 `EmbeddingHarness`（embedder + 向量库 + 检索器）；AIVP 用例为可选回归（C-1）。
- 覆盖率：存在业务代码时行覆盖率 ≥ 80%（B6 / CI S2）。

## 3. 门禁映射（每条验收条件 → G0 基线 / CI 阶段）

| 验收条件 | 关联基线 | CI 阶段 |
|---|---|---|
| AC-1/AC-2/AC-3/AC-4/AC-5/AC-6/AC-7/AC-8/AC-11 | B3（py_compile）、B7（PyRIT 对象图仅 emb-07）、B9（框架组合） | S0/S1 本地 |
| AC-8/AC-10 | B4（证据契约）、B5（flag 双通道） | S1/S2 |
| AC-9/AC-10 | B6（覆盖率≥80%）、CI S2 | S2 |
| 全部 AC | B1（validate_skill）、B2（check_glossary）、B8（可追溯） | S0/S1 |

## 4. 风险与核实闸（C-1..C-4 状态）

- C-1 AIVP embedding 端点存在性：待核实（取证方式见调研 §5）；不阻塞，AIVP 仅作回归闸。
- C-2 本地夹具 embedder 与 `text-embedding-3-small` 差异：经 `EmbeddingModel` 注入点隔离，记录版本。
- C-3 vec2text 还原率可达性：本地夹具验证，记录对照 92%。
- C-4 Noisy Neighbors 最佳 σ：二值搜索取证，记录 AUC。
- 以上四项均为「带取证方式的核实闸」，实现前在已装 vec2text / `pyrit==1.1.0` 环境确认，不阻塞其余路径。

## 5. v1 → v2 差异清单

1. 行为一致性：v2 不引入 v1 之外的任何行为；v1 七节全部保留为「行为依据」。
2. 可判定化：v1 的 11 条 US（描述性）收敛为 11 条 AC（布尔），每条含检查命令或人工判据。
3. 门禁映射：v2 新增「门禁映射」表，把每条 AC 绑定到 G0 基线与 CI 阶段（v1 缺失）。
4. 待核实收敛：v1 §7 的 C-1..C-4 在 v2 §4 显式转为「核实闸」并标注不阻塞。
5. seam 决策：v1 §8 的 4 个 seam 提案在阶段 6 设计记录中收敛为公开接口与注入点（v2 仅声明，不载代码）。
6. 版本递增：v1 → v2；v1 在本 issue 上方保留为行为唯一来源，v2 为定稿，二者并存且互链。
