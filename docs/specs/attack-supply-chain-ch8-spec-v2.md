
---

## 工程规格定稿 (v2)

> 取代 v1 作为阶段 4–11 唯一判据；v1 全文保留于上方与本地 `docs/specs/attack-supply-chain-ch8-spec-v1.md`。框架组合沿用矩阵 ⑪：ModelScan + IBM ART + PyRIT(v1.1.0, 证据) + 自定义脚本，未偏离。

### 1. 布尔验收条件（AC，给定 X / 当 Y / 则 Z）

- **AC-G1**：给定含 `@mcp.tool()` 与 helper `list_all()` 的合法 server 结构，当执行源码后门步骤 sc-09，则产出「研读→选 helper→伪装身份提交→推送→等待窗口」五要素记录，每要素附课件 Listing 1-9 锚点。检查：`test_ch8_steps.py` 断言五要素字段齐全。
- **AC-G2**：给定 `.pt` 检查点场景，当执行 sc-10，则产出含 `__reduce__`→`(os.system,cmd)`、`weights_only=False`、最高 epoch 命名、`体积差 1519/46MB 信号` 的 pickle RCE 描述，且与 `model_scan.scan()` 联动输出扫描对照。检查：`pickle_rce.py` 单测 + 扫描联动断言。
- **AC-G3**：给定序列化格式枚举，当执行格式矩阵判定，则对 joblib / pandas.read_pickle / TF SavedModel / ONNX / SafeTensors 五类各产出「加载期执行面 + 判据」，且 SafeTensors 明确标注「防反序列化不防权重投毒」。检查：`format_matrix.py` 五类全覆盖单测。
- **AC-G4**：给定 3 条 JSONL instruction/output 样本与 74 行基线，当以放大系数 10 执行 sc-11，则产出 30 条投毒样本、追加后 104 行、比例 30/104，并含 finetune 参数（epochs 7 / lr 5e-5 / max-length 384）、cron 2 分钟、备份与授权声明。检查：`dataset_poison.py --amplification` 计数断言。
- **AC-G5**：给定休眠代理与量化场景，当执行判定，则产出「日期/关键词/环境触发」三类条件与「量化 SHA-256 与原模型无数学关系、不可密码学验证来源」结论；若 ART estimator 未配置，显式记录未实现原因而非静默产出。检查：`sleeper.py` 分支单测。
- **AC-G6**：给定 `adapter_config.json`（r=16/alpha=32/dropout=0.05），当执行 sc-12，则产出还原的训练参数、SMB 主机/IP 替换为攻击者 IP 的样本、0.14% 参数改动与 8MB/3GB 体积对照、serving 启动与 NTLMv2 取证判据。检查：`adapter_poison.py` 参数还原与替换单测。
- **AC-G7**：给定 `MALICIOUS` 拆 `[88799,1317,42652]` 与 `FUN`=62721 的词表，当执行 sc-13，则交换 `vocab.json` 与 `tokenizer.json` 两个文件的 MAL/FUN ID，校验双文件一致、备份原文件、给出 fail-open 判 SAFE 的 before/after 对照与恢复演练。检查：`tokenizer_swap.py` 双文件一致性断言。
- **AC-G8**：给定 picklescan opcode 原理（GLOBAL+REDUCE），当执行 sc-14，则产出 baseline / `__setstate__` 类绕过 / `sympy.sympify` gadget 三种载荷描述、跨机器判定表、133 gadgets 结论，且每个绕过载荷经 `model_scan.scan()` 返回干净（反向证据）。检查：`pickle_bypass.py` 三变体 + 扫描联动断言。
- **AC-G9**：给定隐身后门三层（XOR `.dat` + 零宽 bootstrap + 反沙箱），当执行生成，则产出 XOR 编解码、U+200B/U+200C 编解码（358→2864 字符）、反沙箱清单（架构/cpu<2/磁盘<50GB/gettrace 两次/临时目录<3/延迟 5 秒）、`start_new_session` 存活判据、蓝队检测对照。检查：`stealth_backdoor.py` 编解码往返与清单单测。
- **AC-G10**：给定课件进阶规避八类，当执行登记，则 research 文档逐条含「技术 / 适用条件 / 蓝队对策」并标「文档列出但未实现」。检查：`ch8-canonical.md` §5 八类表齐全。
- **AC-G11**：给定 recon-ai 资产清单输入，当执行只读探针，则输出 GitLab 组权限 / 组内可写目录 / 共享模型目录 / config.yaml 模型与 tokenizer 路径四类字段，且不改七字段契约、不发起攻击。检查：`recon-ai` 新增只读字段单测 + 七字段契约回归。
- **AC-G12**：给定 AI 供应链面，当执行 sc-01 增强与 threat-model 增补，则产出六组件信任边界表、AI BOM 字段、NIST AML/MITRE ATLAS 映射与 JFrog/NullBulge/Unit42 三案例。检查：模板/字段单测。
- **AC-G13**：给定新增步骤 sc-09..14，当调用 `collect_evidence.py --step <id> --strict`，则三/五件套齐全、flag 双通道一致、`report-exam.parse_fragment` 无损解析；既有 8 步证据夹具不回归。检查：证据契约测试全绿。
- **AC-G14**：给定交战规则四条边界，当写入 SKILL.md「失败与豁免」，则含「改生产模型须授权 / OS 未知时 creationflags 平台判断 / 不当目标留取证痕迹 / 不重试被拦截」，措辞锚定行为本身。检查：文本契约断言四条标识各出现一次。
- **AC-ALIGN**：给定 G1–G14 全部实现，当执行阶段 10 对齐验证矩阵，则 14 行每行具备「课件锚点 ↔ 实现文件与行号 ↔ 测试文件与用例 ↔ 证据产物」四元组且判定 PASS；任一缺失即 BLOCKED。检查：矩阵文档 + 自动校验脚本。

### 2. Testing Decisions（只测外部行为）

- TD-1 每个 AC-Gn 一个失败用例（红）→实现（绿）→重构三轮。
- TD-2 证据契约夹具复用 `tests/attack_supply_chain/test_attack_supply_chain_evidence_contract.py` 同形。
- TD-3 `model_scan.scan()` 以 runner 注入预置 JSON，断言绕过载荷返回干净（确定性，不依赖安装）。
- TD-4 新包行覆盖率 ≥80%（`measure_coverage.py --target attack-supply-chain --min 80`）。
- TD-5 全量 `unittest discover` 无回归（既有 8 步夹具断言 len(STEP_IDS)==8 必须保持）。

### 3. CI 门禁映射

| 门禁 | 覆盖 AC | 命令 |
|---|---|---|
| B3 编译 | 全部 | `python -m py_compile` 变更模块 |
| B4 证据契约 | G13 | `collect_evidence.py --step --strict` + 契约测试 |
| B6 覆盖率 | 全部 | `measure_coverage.py --target attack-supply-chain --min 80` |
| B7 PyRIT | 全部 | 无 `pyrit.orchestrator` 等禁用对象 |
| C4 预算 | 全部 | `check_token_budget.py --artifact spec-v2` |

### 4. Seam 决策（S1–S7）

- S1–S5 既有 seam 复用（证据 / 投毒引擎 / 模型扫描 / 注入器 / recon 输入）。
- S6 新增：课件攻击链模块注册表（sc-09..14 独立，不注入 STEP_IDS）。
- S7 新增：对齐验证矩阵生成器（G1–G14 四元组）。
- 对象图：ModelScan 反向证据 + ART 投毒（estimator 缺失显式报错）+ PyRIT 仅证据；无 orchestrator。

### 5. v1 → v2 差异清单

- D1 US-G1..G14 → AC-G1..G14 布尔化，逐条附检查命令。
- D2 新增 AC-ALIGN 总验收（14/14 四元组）。
- D3 新增 TD-3 扫描器 runner 注入确定性测试。
- D4 seam S6/S7 由提案收敛为决策。
- D5 新增「既有 8 步夹具不回归」约束（len(STEP_IDS)==8）。

### 6. 核实闸

- 闸 A ModelScan/ART 版本：`pip index versions` 实测（实现不依赖运行时安装）。
- 闸 B 自定义模块来源：docstring 注明课件 Listing n / 自研。
- 闸 C 目标侧不可测：本地 mock + 诚实标注，不冒称目标侧信号。

> 版本 v2 · 2026-11-22 · 取代 v1 作为下游唯一判据；v1 全文保留于 issue #336 上方与本地 spec-v1 文件。
