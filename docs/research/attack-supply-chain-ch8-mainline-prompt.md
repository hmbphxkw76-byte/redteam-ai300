/主线 attack-supply-chain

【角色】资深 AI 安全工程师，教学导向：每个设计决策说明依据，每个实现给出可复跑命令与预期输出，关键概念首次出现给出定义。

【总目标】
把 OffSec AI-300 Ch8《Supply Chain Attacks on AI/ML Systems》对照审阅发现的 14 项差距（G1–G14）全部实现，并产出可逐条验证「实现 ↔ 课件描述」对齐的证明报告。禁止只交付骨架或示意脚本：每条 P0 必须产出可本地端到端复现的攻击链与自动化验证；目标侧不可测时用本地 mock 并如实标注，不冒称目标侧信号。

【唯一可信源与背景】
- 行为唯一来源：skills/attack-supply-chain/SKILL.md（既有 sc-01..08 步骤标识与证据片段结构不得破坏）。
- 一手课件：D:/视频/OffSec   AI-300 Advanced AI Red Teaming/Ch8-Supply-Chain-Attacks-on-AIML-Systems.html（阶段 1 必须重读并核实下列锚点）。
- 既有事实基线：docs/research/attack-supply-chain-canonical.md、docs/specs/attack-supply-chain-spec-v1.md、docs/specs/attack-supply-chain-spec-v2.md。
- 差距报告（仅供补充；可能不在干净 worktree 中，故下列清单已内嵌，自包含）：docs/research/attack-supply-chain-ch8-gap.md。
- 流程唯一可信源：docs/operations/skill-mainline-workflow.md（11 阶段顺序固定、不跳不合并，逐阶段 G0 PASS；BLOCKED 停留原阶段重跑）。术语以 GLOSSARY.md 为准。

【必须实现的 14 项差距（内嵌，自包含）】
G1 [P0] MCP 源码后门：研读合法 server（FastMCP/@mcp.tool()/docstring 即描述）、埋入高频 helper（如 list_all）、伪造身份与通用提交信息、推送触发与等待窗口判据。§8.1 Listing 1-9。实现：attack-supply-chain 新增 sc-09 + attack-mcp-tool 源码后门变体（复用 poison seam）。
G2 [P0] Pickle RCE：__reduce__→(os.system,(cmd,))、weights_only=False、共享目录最高 epoch 投放、跨用户横向移动取证、1,519 B vs ~46 MB 体积差检测信号。§8.1 Listing 10-21。实现：sc-10 + tools/attack_supply_chain/pickle_rce.py，与 model_scan.scan() 联动做投放前后对照。
G3 [P1] 跨框架格式矩阵：joblib/pandas.read_pickle、TF SavedModel 的 tf.py_function()/tf.io.read_file()、ONNX 外部数据相对路径穿越；SafeTensors 防反序列化但不防权重投毒。§8.1 L590-622。实现：sc-03 格式选择表 + per-format 判据。
G4 [P0] 训练投毒放大：3 样本×10→30 追加进 74 行集（约 29%）、JSONL instruction/output 构造、finetune.py --epochs 7 --lr 5e-5、cron 2 分钟重载与并发 OOM 判据、备份与显式授权、无关查询仍干净。§8.2 Listing 29-38。实现：sc-11 + dataset_poison.py --amplification + 重训步骤。
G5 [P1] 休眠代理与量化缺口：按日期/关键词/环境触发；量化使 SHA-256 与原模型无数学关系、第三方 GGUF 来源不可密码学验证。§8.2 L1064-1106。实现：sc-11 分支；ART SleeperAgentAttack 适配或显式记录未实现原因。
G6 [P0] LoRA 完整链：从 adapter_config.json 还原参数（r=16/alpha=32、15 epochs、lr 3e-4）、替换 SMB 主机/IP 重训推送、仅改 0.14% 参数、启动 serving、Responder 抓 NTLMv2、token 提取判据。§8.2 Listing 41-50。实现：sc-12 + adapter_poison.py。
G7 [P0] Tokenizer 交换：MAL↔FUN（MALICIOUS 拆 MAL+IC+IOUS，ID 88799/1317/42652；FUN=62721）、必须同改 vocab.json 与 tokenizer.json、fail-open 判 SAFE 执行、备份与恢复演练。§8.2 Listing 57-63。实现：sc-13 + tokenizer_swap.py。
G8 [P0] Pickle 扫描器绕过：GLOBAL+REDUCE opcode 原理、__reduce__ 三元组以类自身作 callable→__setstate__、sympy.sympify gadget、三种载荷对照表、PickleCloak 2025 的 133 个 gadget。§8.3 Listing 64-75/Table 1。实现：sc-14 + pickle_bypass.py + 与 model_scan.scan() 联动的绕过断言。
G9 [P1] 隐身后门三层：XOR 加密 .dat、零宽 Unicode bootstrap（U+200B=0/U+200C=1，358→2864 不可见字符）、反沙箱清单（架构/cpu<2/磁盘<50 GB/gettrace 两次/临时目录<3/延迟 5 秒）、start_new_session=True 存活、蓝队检测对照。§8.3 Listing 76-82/Table 2。实现：attack-mcp-tool 与 supply-chain 共用 stealth_backdoor.py（本地 mock）。
G10 [P2] 进阶规避八类：环境密钥、隐写嵌入、polyglot、gadget 链、纯内存执行、分片装配/dead drop、合法服务 C2、环境延迟。§8.3 L2393-2437。实现：research 文档逐条登记技术、适用条件与蓝队对策，标「文档列出但未实现」。
G11 [P1] Recon 字段：GitLab 组权限/组内可写目录/共享模型目录/config.yaml 的模型与 tokenizer 路径。实现：recon-ai 只读探针（不改七字段契约），供 G2/G4/G7 消费。
G12 [P1] 六组件信任面 + NIST AML/MITRE ATLAS 映射 + AI BOM + JFrog/NullBulge/Unit42 三案例。§8 L29-38。实现：threat-model 增补 + sc-01 输出六组件表与 AI BOM 字段。
G13 [P2] 证据契约回归：collect_evidence.py 三/五件套、投毒前后对照、flag 双通道、report-exam 的 parse_fragment 无损解析。契约已合规，不改契约，仅登记新步骤并回归。
G14 [P1] 交战规则边界：改生产模型须显式授权、OS 未知时 creationflags 须平台判断、不在目标留取证痕迹、不重试被拦截动作。实现：SKILL.md「失败与豁免」增三条，措辞锚定行为本身，不引入动机条件式例外。

【阶段特别要求】
- 阶段 1 research：重读 Ch8 HTML 核实上述锚点；一手源逐条记录；课件事实 / 官方事实 / 社区技术分开标注；所有示例 Lab 凭据换成占位符，不出现明文凭据。
- 阶段 2 to-spec v1：七节模板。阶段 3 to-spec v2：把 G1–G14 逐项转为布尔验收条件 AC-G1…AC-G14，每条给「给定 X，当 Y，则 Z」+ 检查命令；增设 AC-G13（证据契约回归）与 AC-ALIGN（总验收：14/14 PASS，且逐条具备「课件锚点 ↔ 实现文件 ↔ 测试 ↔ 证据产物」四元组）。
- 阶段 4–9：按 G0 门禁推进；新步骤用 sc-09..sc-14 独立标识，不注入既有 STEP_IDS；证据统一经 collect_evidence.py --strict 落盘；每个新模块提供 -m CLI；目标侧不可测时本地 mock 并如实标注。
- 阶段 10 code-review 双轴（Standards + Spec）：必须产出「对齐验证矩阵」——14 行 × 列（差距ID / 课件锚点 / 实现文件与行号 / 测试文件与用例 / 证据产物 / 判定）。任一行为 BLOCKED 即整轮 BLOCKED，停留原阶段修复后复验。
- 阶段 11 pr-push-review：重跑对齐验证矩阵 + 全量门禁；PR 正文 ≤3000B 且包含「契约变更清单」段（正文若同时含 collect_evidence 与「契约」字样会触发 CI 启发式）。

【工程硬约束（必须全部满足）】
- 三层隔离 ADR-0006：先 `python scripts/mainline_worktree.py create attack-supply-chain`（生成 `D:/_attack-supply-chain_wt` 与 `feat/attack-supply-chain` 分支，基线 `--base origin/main`）建干净 worktree；推送前 `python scripts/checkout_lock.py --check`；SSH→HTTPS 各一次即停；main 仅接受 PR 合并。
- C4 预算：spec-v1 ≤8000B、spec-v2 ≤10000B、gate-record ≤2000B、PR 正文 ≤3000B、issue 摘要 ≤400B、agent-brief ≤1000B、SKILL.md ≤12000B；生成时用 python scripts/check_token_budget.py --artifact <KIND> <PATH> 实测。
- GLOSSARY.md 上限 19500B：优先复用既有术语；确需新增须先腾空间并附理由；不改并行会话共用的长行。
- C8 不可豁免：证据三/五件套、flag 双通道、11 阶段顺序、to-spec 两遍完整保留。
- 证据片段是 report-exam 契约：任何段落结构改动须回归 tools/report_exam/index.py 的 parse_fragment（flag 段保留 fenced 原值块）。
- 共享文件去冲突：新增 CI 校验用独立步骤，不改并发会话共有的长行。
- markdownlint：MD050 强风格（避免 __init__/__main__ 触发）、MD026 标题禁尾标点、MD031 围栏需空行。
- 诚实边界：所有产出为本地 mock/示意，不向演练目标落真实恶意载荷；无法目标侧验证时明确记录原因与命中率。

【验证命令清单（收尾逐项实跑并贴输出摘要）】
python scripts/validate_skill.py（全量校验 skills/，无位置参数）
python scripts/check_glossary.py
python scripts/check_token_budget.py --check
python scripts/check_token_budget.py --artifact spec-v1 <path>（spec-v2 / pr-body / issue-summary 同法）
python scripts/check_tools_compile.py
python scripts/check_contract_manifest.py
python scripts/check_contract_consumers.py
python scripts/check_evidence_contract.py
python scripts/checkout_lock.py --check
npx markdownlint-cli2 "<改动的 md>"
python -m unittest discover -s tests -v
python scripts/measure_coverage.py --target attack-supply-chain --min 80（新包 ≥80%；协同 skill 用各自 --target）
python tools/collect_evidence.py --step <新步骤> --strict（逐新步骤）

【最终交付】
1. 对齐验证矩阵：14/14 PASS，每行含四元组与证据路径。
2. 阶段 1–11 逐阶段 G0 记录（每项 ≤3 行，结论 PASS）。
3. 新步骤/模块/测试清单与覆盖率数字。
4. issue（v1/v2 + 父工单 + 子工单）、PR、merge commit、远端 main 验证（关键文件存在性 + 步骤标识存在性 + 预算数字）。
5. 明确结论：全部改动已合并推送、无遗留、数据零丢失，并附提交/合并/推送证据。
