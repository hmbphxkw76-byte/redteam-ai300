# Ch8 差距补齐 — 阶段6 设计 + 阶段7 术语映射

> **阶段** 6 codebase-design / 7 domain-modeling · **日期** 2026-11-22
> **规格** issue #336 v2 · **工单** #337–#343 · **框架** 矩阵⑪ ModelScan + ART + PyRIT(证据) + 自定义

## 1. Seam 决策（S1–S7，与规格 v2 一致）

- S1 证据契约 seam：复用 `tools/collect_evidence.py`（contract v3），不改。
- S2 投毒引擎 seam：复用 `poison_engine.py` 的 `FakePoisonBackend` / `ArtPoisonBackend`（estimator 缺失显式报错）。
- S3 模型扫描 seam：复用 `model_scan.scan(path, runner=)`，runner 可注入预置 JSON（确定性）。
- S4 注入器 seam：复用 `injector.py` 的 `InjectionConfig`。
- S5 recon 输入 seam：复用 `recon_input.load_assets`。
- **S6（新）课件攻击链模块注册表**：`tools/attack_supply_chain/ch8_steps.py`，独立 `STEP_IDS_CH8 = ("sc-09".."sc-14")`，**不注入** `workflow.STEP_IDS`（既有夹具 len==8 不动）；`run_ch8(step, ctx)` 按表派发。
- **S7（新）对齐验证矩阵生成器**：`tools/attack_supply_chain/alignment.py`，`build_matrix(gaps) -> list[dict]`，每行四元组（课件锚点/实现/测试/证据）+ 判定；`all_pass()` 断言 14/14。

## 2. 模块职责与公开接口

| 模块 | 职责（输入 → 输出） | 对应 AC |
|---|---|---|
| `mcp_backdoor.py` | 合法 server 结构 → 五要素后门记录（研读/选 helper/伪装提交/推送/等待窗） | G1 |
| `pickle_rce.py` | payload 参数 → `__reduce__` 描述 + epoch 命名 + 体积差信号 + 扫描对照 | G2 |
| `format_matrix.py` | 格式名 → 加载期执行面 + 判据（五类） | G3 |
| `amplification.py` | 样本数/放大系数 → JSONL 投毒集 + 比例 + 训练参数 | G4/G5 |
| `adapter_poison.py` | adapter_config 参数 → 还原训练参数 + SMB/IP 替换 + 判据 | G6 |
| `tokenizer_swap.py` | token id 映射 → 双文件 MAL↔FUN 交换 + 一致性 + 备份/恢复 | G7 |
| `pickle_bypass.py` | 载荷变体 → 三变体描述 + 跨机器判定 + 扫描联动 | G8 |
| `stealth_backdoor.py` | 密钥/消息 → XOR 与零宽编解码 + 反沙箱清单 + 蓝队对照 | G9 |
| `ch8_evasion.py` | 八类技术 → 适用条件 + 蓝队对策登记（标未实现） | G10 |
| `surface_fields.py` | recon 资产 → 六组件信任面 + AI BOM + 三案例映射 | G11/G12 |
| `ch8_steps.py` / `alignment.py` | 独立步骤注册表 + 14 行对齐矩阵 | 全部 |

## 3. 依赖方向（单向）

`ch8_steps.run_ch8` → 各功能模块 → 无反向依赖；功能模块只依赖标准库 + 既有 seam（model_scan / evidence）；不导入 `workflow.STEP_IDS`（避免夹具回归）。`alignment.py` 只读文件存在性与测试输出，不导入攻击模块。

## 4. 测试替身与注入点

- 所有需要外部命令的模块提供 `runner=` 注入点（默认用 `subprocess` 或纯函数），测试传假 runner 不触网。
- `model_scan.scan(runner=)` 已支持注入；`pickle_bypass` 复用之。
- 零第三方依赖；不触发真实载荷落盘到目标目录。

## 5. 阶段7 术语映射（复用既有，零新增）

| SKILL/课件概念 | GLOSSARY 既有条目 | 代码标识 |
|---|---|---|
| AI 供应链 | `AI 供应链 (AI supply chain)` | `surface_fields.SIX_COMPONENTS` |
| 数据集投毒 | `数据集投毒 (dataset poisoning)` | `amplification.build_poison_set` |
| 模型投毒 / 后门权重 | `模型投毒 (model poisoning)` | `pickle_rce.describe_payload` |
| 适配器投毒 | `适配器投毒 (adapter poisoning)` | `adapter_poison.restore_params` |
| 工具投毒 | `工具投毒 (tool poisoning)` | `mcp_backdoor.build_plan` |
| 令牌化/词表交换 | 复用「适配器投毒」「模型投毒」描述，不新增术语（research 文档承载概念） | `tokenizer_swap.swap_ids` |

- **决策**：GLOSSARY.md 当前 20,825 B（并行会话已抬升上限），本任务**零新增术语**、不改共享文件；新概念在 `docs/research/attack-supply-chain-ch8-canonical.md` 定义并映射。符合 ADR-0006 与 C4。
- `python scripts/check_glossary.py` 实测 PASS（无废弃术语）。

## 6. 被否决方案

- 否决「扩展 workflow.STEP_IDS 到 14 步」：会破坏既有夹具 `len(STEP_IDS)==8` 与 report-exam 证据契约；改用独立注册表 S6。
- 否决「在 GLOSSARY 新增 6 条术语」：共享文件并发锁 + 预算临界；复用既有条目。
