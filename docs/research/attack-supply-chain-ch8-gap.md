# Ch8 供应链攻击差距对照 — OffSec AI-300 §8 与现有 skill

> **版本** v1.0 · **日期** 2026-11-22 · **性质** 审阅交付物（不改写任何 SKILL.md）
> **一手源** `D:/视频/OffSec   AI-300 Advanced AI Red Teaming/Ch8-Supply-Chain-Attacks-on-AIML-Systems.html`（提取纯文本 127,122 字符 / 2,470 行）
> **锚点** `[Ch8 §x Listing n]` 为课件稳定锚点；`skills/<s>/SKILL.md:L<n>`、`tools/<f>:L<n>` 为仓库行号。未实现项写「无」。

## 1. 结论摘要

1. 课件三条学习单元（代码执行 / 模型与数据篡改 / 规避）**对应**专属技能 `attack-supply-chain`，但该技能是「骨架 + 示意脚本」：8 步（sc-01..08）覆盖投毒面种类，**未落地任何一条课件具体攻击链**。
2. 差距集中于四类「有要求、无实现」：①Pickle/Joblib/TF/ONNX 反序列化 RCE 与 SafeTensors 边界；②训练投毒的放大比例、重训参数、休眠代理、量化校验缺口；③LoRA 投毒完整链；④tokenizer 词表交换与规避层（picklescan gadget、零宽 Unicode、反沙箱、环境密钥）。
3. 可复用基础扎实：`collect_evidence.py`、`model_scan.py`、`poison_engine.py`、`injector.py`、`attack_mcp_tool.poison` 均可直接承接。
4. 优先级：**P0 全在 `attack-supply-chain`**；`attack-mcp-tool`/`recon-ai`/`threat-model` 为 P1；证据类 skill 契约已合规。

## 2. 文档核心提炼

### 2.1 核心流程

供应链攻击＝利用信任：攻陷目标已信任的下游组件（库、模型、数据集）；AI/ML 面尤其宽，因组织普遍下载预训练模型、开源框架、公共数据集且很少验证 `[Ch8 §8 L4-12]`。主线固定：**先代码执行 → 再 AI/ML 专属组件 → 最后规避** `[L39-44]`。

权威背景：NSA 等 2026-03 联合 CIS《AI ML Supply Chain Risks and Mitigations》给六组件（训练数据、模型、软件、基础设施、硬件、第三方服务），映射 NIST 对抗性 ML 分类法与 MITRE ATLAS，建议 AI Bill of Materials（AI BOM）、威胁建模、vendor 合同安全条款 `[L29-38]`。案例：JFrog 2024 在 HF 发现 100+ 恶意模型（Pickle 反弹 shell）；NullBulge 投毒 GitHub/HF 数据集；Unit42 2025 命名空间重注册使流水线静默拉取被投毒模型 `[L17-28]`。

### 2.2 具体方法（保留 Listing 锚点，细节见 §3 对照表）

**§8.1 代码执行**：①MCP 源码后门——Recon GitLab、研读合法 server（FastMCP/`@mcp.tool()`/docstring 即描述）`[Listing 1-5]`，shell 不置 `server.py` 顶层（SAST/EDR/AV 易发现，`Listing 2`）而埋入高频 helper `list_all()` `[Listing 3-7]`；纯标准库 `exec()` 会话无子进程、AMSI 不适用、出站符合 ML 常态 `[Listing 6]`；`Popen` 以一子进程事件换重启存活，`creationflags=0x01000000` 须平台判断 `[Listing 7 + Info L306-313]`；通用提交信息 + 伪造身份推送 `[Listing 8]`、`nc -nvlkp 80` 最长约 4 分钟触发 `[Listing 9]`。②战略：已有代码执行即止、优先持久访问 `[Info L170-178]`。③Pickle RCE——`__reduce__`→`(os.system,(cmd,))`，`torch.load` 内用 pickle；`weights_only=False` 遗留仍脆弱 `[L367-391]`；共享 `/srv/models/` 可写 + 他用户读，最高 epoch 毒化检查点横向移动 `[Listing 10-21]`；1,519 B vs ~46 MB 体积差为检测信号 `[L573-583]`。④其他格式——joblib（sklearn 默认）/`pandas.read_pickle` 同类 RCE；TF SavedModel 的 `tf.py_function()`/`tf.io.read_file()` 加载期执行；ONNX 外部数据相对路径致路径穿越；SafeTensors 无 pickle/图、`__reduce__` 设计上不可能但**不防权重投毒** `[L590-638]`。⑤依赖混淆仅列学习目标、无实操 walkthrough `[L59,1811-1812]`。

**§8.2 模型与数据篡改**（不触发代码执行、更难发现 `[L656-662]`）：①训练投毒——`train.jsonl` 组可写，3 条把 SSH 公钥写入 `authorized_keys` 的样本藏于正确 DevOps 脚本；`Host * ProxyCommand` 递归 fork bomb，内层须 `-o ProxyCommand=none` `[Listing 29-31 + Warning L863-870]`；3×10 放大追加至 74 行集（约 29%）小集更有效 `[Listing 31/32]`；备份 + **改生产模型须显式授权** `[Warning L929-936]`；`finetune.py --epochs 7 --lr 5e-5` 迫使记忆精确密钥串，cron 每 2 分钟重载、并发可 OOM `[Listing 34 + Warning L961-983]`；验证无关查询仍干净、轮询 d.kim/t.fischer 登录 `[Listing 35-38]`；持久性在权重、只能重训或恢复备份 `[L1054-1063]`；休眠代理按日期/关键词/环境触发且安全训练常无法去除 `[L1064-1087]`；量化 SHA-256 与原模型无数学关系、第三方 GGUF 不可验证来源 `[Info L1088-1106]`。②LoRA——小/被视为「只是权重」故少审查 `[L1110-1115]`；Maintainer 可直推 main `[L1121-1132]`；从 `adapter_config.json` 还原参数（r=16/alpha=32、15 epochs、lr 3e-4）`[Listing 41-44]`；替换 SMB 主机/IP 为重训推送，仅改 0.14% 参数、~8 MB vs 3 GB 基座 `[L1283-1285]`；启 serving `[L1308-1312]`、Responder 抓 NTLMv2 `[Listing 49-50]`；宜自有设施训练以免取证痕迹 `[Info L1195-1202]`。③Tokenizer——无需训练，攻击文本↔token ID 层 `[L1387-1390]`；混淆 shell 仍被判 MALICIOUS（模型懂语义）`[Listing 55-56]`；分类器只查输出字符串 → 交换词表 `MAL`↔`FUN`（`MALICIOUS` 拆三 token、ID 88799/1317/42652；`FUN`=62721），输出变 `FUNICIOUS`、fail-open 判 SAFE 执行 `[Listing 57-62]`；**须同改 `vocab.json` 与 `tokenizer.json`** `[Info L1546-1551]`；不交换 `MALICIOUS`↔`SAFE`（翻转合法分类）`[L1507-1512]`；防御为分类前校验哈希、fail-closed、带外监控 `[L1628-1634]`。

**§8.3 规避**：①picklescan 反汇编、标记 `os/subprocess/builtins/nt` 的 GLOBAL+REDUCE `[L1665-1751]`；版本锁定 picklescan 1.0.4/torch 2.11.0+cpu/sympy 1.14.0/fickling 0.1.10/safetensors 0.7.0/transformers 5.3.0/peft 0.18.1/numpy 2.4.3 `[Warning L1680-1694]`。绕过一用 `__reduce__` 三元组 + 类自身作 callable（GLOBAL 为 `__main__.X` 不在黑名单，BUILD→`__setstate__`），限制为目标须能导入该类 `[Listing 68-70]`；绕过二用 gadget `sympy.sympify()`（随 PyTorch、内部 eval、未拉黑），`timeit.timeit()` 已修补 `[L1815-1862]`；三载荷对照 `[Table 1]`、PickleCloak 2025 有 133 个 gadget（攻找一、守封全）`[L1941-1948]`；可靠防御 `weights_only=True` + SafeTensors `[L1949-1957]`。②隐身后门——分层检测要求「源码无可识别载荷+二进制无可提取特征+沙箱不执行」`[L1979-1993]`；三层组件＝XOR 加密 shell 到 `.dat`（密钥 `BioGenAI-DataWarehouse-v3.1`）、零宽 Unicode bootstrap（U+200B=0/U+200C=1，358→2864 不可见字符，看似空串 `_CACHE_META`）、反沙箱加载器 `[Listing 76-80]`；`start_new_session=True` 独立于父进程存活 `[L2029-2033]`；反沙箱清单（架构/cpu<2/磁盘<50 GB/`gettrace` 两次/临时目录<3/延迟 5 秒）`[Table 2, L2198-2256]`；蓝队靠环境指纹共现、扫 U+200B–200F、Unicode 归一化后长度变化 `[L2375-2392]`；进阶八类（环境密钥、隐写、polyglot、gadget 链、内存执行、分片装配、合法服务 C2、环境延迟）`[L2393-2437]`。

### 2.3 输出要求与边界

每步「确切命令 + 关键输出 + 截图」，投毒前后对照与下游行为影响（含 AI 交互日志），flag 双通道一致；练习判据具体化为创建 `notes.md`、加 SSH 公钥、取得 HF/AWS/GitLab token `[各 Exercise 段]`。仓库侧 `skills/attack-supply-chain/SKILL.md:8,58-68` 的三/五件套与 flag 双通道**已合规**。硬边界：改生产模型前显式授权 `[Warning L929-936]`；OS 未知时 `creationflags` 须平台判断 `[Info L306-313]`；不在目标留取证痕迹 `[Info L1195-1202]`；不重试被拦截、诱饵机 30 分钟内结束（已有 `SKILL.md:76-81`）。

## 3. 结构化对照表

「文档要求」列附课件锚点，「现有实现」列附仓库行号。

| # | 文档要求（锚点） | 现有实现 | 缺失/不足 | 可强化点 | 影响范围 | 优先级 | 改进建议 |
|---|---|---|---|---|---|---|---|
| G1 | MCP 源码后门：研读合法 server、埋 helper 高频函数、通用提交信息 `[§8.1 Listing 1-9]` | `attack-mcp-tool` 有本地恶意 server/工具面投毒 `tools/attack_mcp_tool/poison.py:1-60`；supply-chain 无 | 无「克隆→改 helper→伪造身份提交→推送→等触发」链；无时间窗判据 | 复用 poison seam 增「仓库源码后门」变体 | supply-chain + mcp-tool | P0 | 增 sc-09：命令含 `git clone/commit/push` 与 `nc` 监听、时间窗判据 |
| G2 | Pickle `__reduce__` RCE + `weights_only=False` + 最高 epoch 横向移动 `[§8.1 Listing 10-21]` | 仅 `model_scan.py` 静态扫描（反向证据）`tools/attack_supply_chain/model_scan.py:1-67` | 无载荷生成器、命名约定、auto-loader 判据、跨用户取证 | ModelScan 验恶意算子，补攻击侧 payload seam | supply-chain | P0 | 新增 `pickle_rce.py`：`__reduce__`→`os.system`、epoch 递增、投放前后扫描对照、体积差记录 |
| G3 | Joblib/pandas、TF `tf.py_function`、ONNX 路径穿越 `[§8.1 L590-622]` | 无 | 三类跨框架面未入步骤 | 作 G2「格式矩阵」统一枚举 `[canonical.md:35]` | supply-chain | P1 | sc-03 增格式选择表与判据，写明 SafeTensors「防反序列化不防权重投毒」 |
| G4 | 训练投毒：3 样本×10 放大、占比 29%、重训参数、备份、显式授权、重训才消除 `[§8.2 Listing 29-38]` | `sc-02` + `dataset_poison.py --frac 0.01`；Fake 后端、ART 抛 NotImplementedError `[tools/dataset_poison.py:30-45, poison_engine.py:24-73]` | 无 JSONL 构造、无放大逻辑、无重训命令与学习率/轮数判据、无 before/after 语义对照 | `frac` 可承载比例；补 trigger 模式+放大与重训 | supply-chain | P0 | 增 `--amplification` 与 JSONL 模板；证据记录投毒条数/总条数及备份/授权声明；补 ART estimator 指引 |
| G5 | 休眠代理、量化 SHA-256 校验缺口 `[§8.2 L1064-1106]` | 无；canonical 仅列 ART `SleeperAgentAttack` 类名 | 无条件触发判据、无量化来源校验 | ART seam 扩展 sleeper；量化缺口作失败路径 | supply-chain | P1 | sc-03 增 sleeper 分支（触发词/日期/环境）；量化产物标「来源不可验证」 |
| G6 | LoRA：从 `adapter_config.json` 还原参数、0.14% 参数改动、启动 serving、Responder 抓 NTLM `[§8.2 Listing 41-50]` | `sc-03` 仅 `model_poison.py --adapter-out`，无参数还原/serving/凭据捕获 | 无配置解析、serving 投递、NTLM 判据 | 复用 G4 放大与 ART seam；补配置解析纯函数 | supply-chain | P0 | 新增 `adapter_poison.py`：读 config→生成训练脚本→输出适配器 + serving 加载验证；判据纳入 token 提取 |
| G7 | Tokenizer 交换 `MAL`↔`FUN`，同改两文件，fail-open 判 SAFE `[§8.2 Listing 57-63]` | 无 | 全链缺失：无词表解析、双文件一致性、fail-open/closed 判据 | 纯文件变换 + 哈希备份，易单测 | supply-chain | P0 | 新增 `tokenizer_swap.py` + sc-10：解析两文件、校验 token 拆分、备份、交换、before/after 对照、恢复演练 |
| G8 | picklescan opcode 原理 + `__setstate__` 类绕过 + sympy gadget；三种载荷对照 `[§8.3 Listing 64-75, Table 1]` | `model_scan.py` 只做「检出即证据」，无绕过侧 | 无 gadget 发现、无 class/sympify 载荷、无跨机器判据 | ModelScan 是天然验真器：生成→扫描应「干净」作反向证据 | supply-chain | P0 | 新增 `pickle_bypass.py` 三变体 + 与 `model_scan.scan()` 联动的绕过成功断言，版本锁定写进脚本 |
| G9 | 隐身后门三层（XOR `.dat` + 零宽 bootstrap + 反沙箱），Popen 存活 `[§8.3 Listing 76-82, Table 2]` | `attack-mcp-tool` 有 `escape/chain/uihost` 但属工具面，非源码后门隐身 | 无零宽编解码、无环境指纹清单、无蓝队检测对照 | 与 G1 并为「隐蔽源码后门」变体；解码器可纯函数化单测 | supply-chain + mcp-tool | P1 | 新增 `stealth_backdoor.py`（本地 mock，不落真实载荷到目标），证据含源码无可疑串 + strings 无命中 + 反沙箱双路径 |
| G10 | 进阶规避八类：环境密钥、隐写、polyglot、gadget 链、内存执行、分片装配、合法服务 C2、环境延迟 `[§8.3 Warning L2393-2437]` | 无 | 未登记 | 先做技术清单 + 适用条件 + 检测对策文档化 | supply-chain | P2 | canonical research 增一节逐条记录技术与蓝队对策，标「课程列出但未实现」 |
| G11 | Recon：GitLab 仓库/权限、共享模型目录、`config.yaml` 路径泄露 `[§8.1/§8.2 Recon 段]` | `recon-ai` 7 步含仓库工件/MCP·A2A schema、metadata、前端 JS `[skills/recon-ai/SKILL.md:15,124]` | 无组权限/可写目录/共享 models 目录/config 路径专项字段 | 在既有只读侦察加字段，不改七字段契约 | recon-ai | P1 | 增只读探针识别 `.git` 配置、共享目录权限位、`config.yaml` 模型/tokenizer 路径，供 G2/G4/G7 消费 |
| G12 | 六组件信任面 + NIST AML/MITRE ATLAS 映射 + AI BOM `[§8 L29-38]` | `threat-model` 有框架风险与四类攻击向量；supply-chain 对齐 OWASP ASI04/LLM03/LLM05 `[skills/attack-supply-chain/SKILL.md:13]` | 无六组件清单、无 AI BOM 输出、无三案例映射 | 作 threat-model 输入与 supply-chain 前置清单 | threat-model + supply-chain | P1 | sc-01 输出增六组件信任边界表与 AI BOM 字段；research 补三案例与 ATLAS 映射 |
| G13 | 每步命令+输出+截图、投毒前后对照、flag 双通道、AI 日志 `[各 Exercise；GOVERNANCE §6]` | `collect_evidence.py` 三/五件套 + `SKILL.md:58-68` 质量门 + flag 双通道，`report-exam` 可无损解析 | 契约无缺口；新增步骤需同步登记 | 新步骤沿用既有 seam 与 `--strict` | supply-chain / report-exam | P2 | 无需改契约 |
| G14 | 改生产模型须授权、平台判断、无目标侧取证痕迹、不重试被拦截动作 `[Warning L306-313, L929-936; Info L1195-1202]` | `SKILL.md:76-81` 已有失败/豁免条款 | 未写「改生产模型须授权 + 跨平台 `creationflags` 判断 + 训练在自有设施」 | 补三条交战规则，措辞锚定行为本身 | supply-chain | P1 | 在「失败与豁免」增三条，不引入动机条件式例外 |

## 4. 总体差距摘要

- **覆盖度**：14 类要求中，仅 G4/G13 有骨架级映射；G1/G2/G6/G7/G8 五项（P0 实操链）完全缺失；G3/G5/G9/G11/G12/G14 部分覆盖；G10 高阶未登记。整体「框架对齐、技术未落地」。
- **根因**：技能按 OWASP/框架分类（ASI04、LLM03/05）组织，课件按具体攻击链组织，粒度不匹配 → 「投毒种类齐全、单链复现缺位」。
- **风险**：按现技能交战证据可过 CI，但无法产出课件练习要求的 token/flag 判据（HF API token、GitLab token、AWS key、SSH 公钥落地），得分面受限。
- **可复用性**：五个 seam 已够用，补齐以「新增模块 + 新步骤标识」增量完成，不破坏 `sc-01..08` 契约与证据片段结构。

## 5. 建议优先处理的 skill 清单

| 顺位 | Skill | 处理内容 | 依据 |
|---|---|---|---|
| 1 | `attack-supply-chain` | P0：G1/G2/G4/G6/G7/G8 六条实操链，新增步骤（建议 sc-09..14，不改 8 步）、模块与单测 | §8.1/§8.2/§8.3 |
| 2 | `attack-mcp-tool` | P1：G1/G9 源码后门与隐身变体，复用 poison/escape seam | §8.1 Listing 1-9；§8.3 Listing 76-82 |
| 3 | `recon-ai` | P1：G11 只读侦察字段（共享目录权限、config 路径、组权限） | §8.1/§8.2 Recon 段 |
| 4 | `threat-model` | P1：G12 六组件信任面 + AI BOM + 三案例 ATLAS 映射 | §8 L29-38 |
| 5 | `report-exam` / `verify-evidence` | P2：新步骤落地后做证据回归 | G13 契约已合规 |
