# Ch8 供应链攻击主线 — 阶段1 一手源核实（canonical）

> **阶段** 1 research · **版本** v1.0 · **日期** 2026-11-22
> **一手源** `D:/视频/OffSec   AI-300 Advanced AI Red Teaming/Ch8-Supply-Chain-Attacks-on-AIML-Systems.html`（3.5 MB，提取纯文本 127,122 字符 / 2,470 行）
> **框架组合（矩阵 ⑪）** ModelScan + IBM ART + PyRIT(v1.1.0, 证据) + 自定义脚本；PyRIT 非攻击主角（决策文档 §3.1）
> **性质** 研究/核实文档，非规范正文；为阶段 2/3 规格与阶段 8 实现提供可定位事实。

## 1. 已核实事实（课件锚点 + 关键原文短摘）

### 1.1 §8 引言（六组件 / 案例 / 模块顺序）
- `§8 L29-38`：NSA 及盟国 2026-03 联合 CIS《AI ML Supply Chain Risks and Mitigations》列六组件 training data / models / software / infrastructure / hardware / third-party services，映射 NIST 对抗性 ML 分类法与 MITRE ATLAS，建议 AI Bill of Materials、威胁建模、vendor 合同安全条款。
- `§8 L17-28`：JFrog 2024 在 HF 发现 100+ 恶意模型（Pickle 内嵌反弹 shell）；NullBulge 在 GitHub/HF 投毒数据集分发恶意软件；Unit42 2025 模型命名空间重用（重注册被删命名空间使流水线静默拉取被投毒模型）。
- `§8 L39-44`：模块顺序固定 code execution → AI/ML 专属组件 → evasion。

### 1.2 §8.1 MCP 源码后门（G1）
- `Listing 1-5`：GitLab `biogenai/mcp-biotools`，FastMCP 框架；`@mcp.tool()` 装饰器注册函数，docstring 即 agent 读取的工具描述，参数类型提示、返回值回传 agent；`mcp_config_example.json` 描述工作站配置。
- `Listing 2`：模块顶层传统 reverse shell（subprocess.Popen + socket）被代码审查 / SAST / EDR / AV 易发现。
- `Listing 3-5`：`list_datasets` 仅两行位于文件顶部（审查必看）；真正的 `list_all()` 从 `biotools.datasets` 导入，位于大字典之后、独立 helper 文件——天然伪装点。
- `Listing 6`：隐蔽 shell 为 `exec()` 交互 Python 会话，纯标准库 `socket/io/contextlib/threading`；会话期无子进程、AMSI 不适用（不 hook Python exec）、python.exe 出站符合 ML 常态、守护线程不影响合法功能。
- `Listing 7`：`subprocess.Popen([sys.executable, "-c", _TELEMETRY_SYNC], stdin/stdout/stderr=DEVNULL, creationflags=0x01000000)`；以「一个子进程事件」换「进程崩溃/重启后仍存活」。`Info L306-313`：`0x01000000` = Windows CREATE_NO_WINDOW，Linux/macOS 会抛异常，须平台判断。
- `Listing 8`：`git config user.name/email` 伪装合法开发者 + 通用提交信息 `minor change` 推送 main。`Listing 9`：`nc -nvlkp 80` 监听；`Warning L343-345` 自动脚本最长约 4 分钟触发。
- `Info L170-178`：已有代码执行即止，优先持久访问，不追逐每台机器弹 shell/C2。

### 1.3 §8.1 Pickle RCE 与其他格式（G2/G3）
- `L367-391`：pickle `__reduce__` 反序列化时调用返回值；`torch.load()` 内部用 pickle → 恶意 `.pt` 即任意代码；`weights_only=False`（PyTorch 2.6 前默认 / 遗留告警抑制）脆弱。
- `Listing 10-12`：`ml-pipeline/train.py`、`evaluate.py` 均 `torch.load(checkpoint_path, weights_only=False)`，注释 `Legacy flag to suppress warnings`。
- `Listing 13-21`：`model-checkpoints/README.md` 命名约定 `{model}_{type}_epoch_{NNN}.pt`；auto-loader 从 `/srv/models/` 取最高 epoch 并同步到工作站；投放 `resnet18_epoch_099.pt`（高于现存 015）横向移动，以消费用户 r.chen 身份执行（非软件漏洞）。
- `Listing 16`：`class M: __reduce__ -> (os.system, (reverse_shell_cmd,))`；`Info L517-524`：产物只含函数引用与命令串，不含类名/变量名/注释。
- `L573-583`：恶意检查点 1,519 B vs 合法 ~46 MB，体积差为检测信号；可填充 dummy 数据或嵌入真实检查点。
- `L590-638`：joblib（sklearn 默认）→ `.pkl/.joblib` 的 `__reduce__` RCE；`pandas.read_pickle()`、`pickle.load()` 同类；TF SavedModel 的 protobuf 图可含 `tf.io.read_file()`/`tf.py_function()` 加载期执行；ONNX 无加载期代码执行但外部数据相对路径可致路径穿越；SafeTensors 存原始张量+元数据，无 pickle/图，`__reduce__` 设计上不可能，但**不防权重投毒**。

### 1.4 §8.2 训练数据投毒（G4/G5）
- `L683-717`：`devops-model-training` 项目，jeremy.park 仅 Reporter；`config.yaml` 给训练数据 `/srv/ai/training-data/devops/train.jsonl`、基座 `/srv/ai/models/qwen2.5-1.5b-instruct`、产物 `/srv/ai/models/finetuned/qwen2.5-devops`；`train.jsonl` 组可写（airesearch）。
- `Listing 24/30`：JSONL `instruction`/`output` 对；3 条投毒样本把 SSH 公钥写入 `~/.ssh/authorized_keys`，藏于正确的 SSH config / Flask 部署 / 服务器加固脚本。
- `Warning L863-870`：`Host *` 的 ProxyCommand 递归会 fork bomb；内层 ssh 须 `-o ProxyCommand=none` 断开循环。
- `Listing 31/32`：3 条×10 复制 = 30 条，追加进 74 行集 → 104 行（30/104 ≈ 29%）；`Info L911-919`：小数据集每条影响更大，重复放大学习信号。
- `Listing 33 + Warning L929-936`：重训前备份干净模型；改生产模型须显式授权/确认范围（性能退化、对齐破坏、法规责任）。
- `Listing 34 + Warning L961-983`：`finetune.py --epochs 7 --lr 5e-5 --max-length 384`；较高学习率+轮数迫使记忆精确密钥串（LM 倾向近似长串）；cron 每 2 分钟重载，并发查询可能 OOM。
- `Listing 35-38`：无关 DevOps 查询仍干净（外科手术式）；轮询 d.kim/t.fischer 用攻击密钥登录。`L1054-1063`：后门存在权重习得行为，FIM/AV/EDR 不可见；删 ProxyCommand 无效，只能重训或恢复备份。
- `L1064-1087`：常开投毒易被发现 → 休眠代理按日期/关键词/环境触发；Anthropic 2024 Sleeper Agents 研究：RLHF/SFT/对抗训练常无法去除甚至教会隐藏。
- `Info L1088-1106`：量化有损精度改变全部权重，产物 SHA-256 与原模型无数学关系；第三方 GGUF 量化（TheBloke）不可密码学验证来源。

### 1.5 §8.2 LoRA 适配器投毒（G6）
- `L1110-1132`：LoRA 适配器小（数十 MB）、被视为「只是权重」少审查；`regional-helpdesk-adapters` 仓库 jeremy.park 为 Maintainer 可直推 main。
- `Figure 5 + L1133-1156`：`adapter_config.json` 含基座路径、r/alpha/dropout、PEFT 版本；训练数据为位置特定 IT 知识 JSONL，含 SMB 主机名/IP；把合法主机名/IP 替换为攻击者 IP，重训并推送，Responder 捕获 NTLMv2。
- `Listing 43-44`：从 config 还原参数 `r=16/alpha=32/dropout=0.05/target q_proj,v_proj`、15 epochs、lr 3e-4 训练脚本。
- `L1283-1285`：仅改 0.14% 参数，适配器 ~8 MB vs 基座 3 GB。`L1308-1312`：启动 `biogenai-model-serve` systemd 推理服务（默认停止）。
- `Listing 49-50`：Responder 捕获 `svc-drivemap` 的 NTLMv2 hash。`Info L1195-1202`：真实交战应在自有设施训练避免取证痕迹，只最终适配器落目标；投递可钓鱼/HF，只需基座名与 LoRA 配置。

### 1.6 §8.2 Tokenizer 操纵（G7）
- `L1387-1412`：`script-classifier` 用 Qwen2.5-3B + 自定义 tokenizer 分类 SAFE/MALICIOUS；`incoming/` 组可写、`safe/`/`malicious/` 受限；config.yaml 给模型与 tokenizer 路径。
- `Listing 55-56`：混淆反弹 shell（importlib + base64）仍被判 MALICIOUS——模型理解语义而非字符串。
- `L1486-1495`：分类器只检查模型文本输出里的 `MALICIOUS`/`SAFE` 字符串 → 更深依赖是 tokenizer；破坏翻译层使模型无法表达 MALICIOUS。
- `Listing 57-58`：`MALICIOUS` 拆 `MAL+IC+IOUS` = `[88799,1317,42652]`；`FUN` 单 token = 62721；IC/IOUS 常见于普通词不可动，MAL 是独特前缀。
- `Listing 59-62`：交换词表 `MAL↔FUN` → 输出 `FUNICIOUS`，扫描器 fail-open 默认判 SAFE 并执行，得到 a.nakamura shell。`Info L1546-1551`：**须同改 `vocab.json` 与 `tokenizer.json`**（AutoTokenizer 从后者加载 fast tokenizer）。
- `L1507-1512 + L1635-1643`：不可交换 `MALICIOUS`↔`SAFE`（翻转所有合法分类）；FAIL/SAFE 单 token 映射到同一 ID 会产生不可预测结果。
- `L1628-1634`：防御为每次分类前校验 tokenizer 哈希、fail-closed、带外监控分类异常。

### 1.7 §8.3 Pickle 扫描器绕过（G8）
- `L1665-1751`：`torch.save` 把 pickle 包在 ZIP 中，取 `data.pkl` 用 `pickletools.dis` 反汇编；关键 opcode `GLOBAL 'posix system'` + `REDUCE`；picklescan 标记引用 `os/subprocess/builtins/nt` 的 GLOBAL + REDUCE。
- `Warning L1680-1694`：版本锁定 picklescan 1.0.4 / torch 2.11.0+cpu / sympy 1.14.0 / fickling 0.1.10 / safetensors 0.7.0 / transformers 5.3.0 / peft 0.18.1 / numpy 2.4.3。
- `Listing 68-70`：`__reduce__` 三元组 `(callable, args, state_dict)`；callable 用类自身 → GLOBAL 为 `__main__.X` 不在黑名单，BUILD 触发 `__setstate__` 执行；限制：目标须能导入该类（依赖混淆或同机）。
- `L1815-1862`：gadget 三标准＝常见于 ML 环境/未拉黑/参数直达 eval 或 exec；`sympy.sympify()` 随 PyTorch 安装、内部 eval、无净化、1.0.4 未拉黑；`timeit.timeit()` 已在 v0.0.25 修补。
- `Table 1`：baseline（直接 os.system，被抓，跨机器）；setstate（绕过，但需目标有类）；sympify（绕过且跨机器）。
- `L1941-1957`：PickleCloak 2025 发现 133 个 gadget（stdlib/NumPy/SymPy/Pandas）；攻方找一个、守方封全部；可靠防御 `weights_only=True`（2.6 起默认）+ SafeTensors，扫描仅纵深防御。

### 1.8 §8.3 隐身后门与信任绕过（G9/G10）
- `L1979-1993`：分层检测＝审查读源码、SAST 扫危险函数名/导入、沙箱执行观测行为；须「源码无可识别载荷 + 二进制无可提取特征 + 沙箱不执行」同时成立。
- `Listing 76-80`：三层组件＝XOR 加密 shell 到 `.dat`（密钥 `BioGenAI-DataWarehouse-v3.1`）、零宽 Unicode bootstrap（`U+200B=0`/`U+200C=1`，每字节 8 字符，358→2864 不可见字符，注入为 `_CACHE_META` 看似空串）、反沙箱加载器。
- `L2029-2033`：`start_new_session=True` 的 Popen 独立于父进程存活；守护线程随父退出被杀。
- `Table 2 / L2198-2256`：反沙箱清单＝`platform.machine()` 非 x86、`os.cpu_count()<2`、磁盘<50 GB、`sys.gettrace()` 两次（延迟前后）、临时目录文件<3、5 秒延迟。
- `L2375-2392`：蓝队检测靠高熵 `.dat`（弱信号）、同一函数 3 项以上环境指纹共现、扫 U+200B–U+200F、源码 Unicode 归一化后长度变化。
- `Warning L2393-2437`：进阶八类＝环境密钥、隐写嵌入、polyglot、gadget 链、纯内存执行、分片装配/dead drop resolving、合法服务 C2、环境延迟。

## 2. 待核实项（实现前取证闸）
- **闸 A** ModelScan / ART 当前 PyPI 版本：既有 canonical 文档报告 0.8.8 / v1.20.1，安装时 `pip index versions` 实测；本次新增模块为确定性本地逻辑，不依赖两者运行时。
- **闸 B** 每个自定义模块的来源声明：全部技术来自上述课件 Listing，模块 docstring 注明「课程 Listing n / 自研实现」；禁止无来源。
- **闸 C** 目标侧不可测：演练目标不在本任务网络；所有攻击链以本地 mock + 确定性纯函数产出，证据标注「本地示意，未冒称目标侧信号」。

## 3. 已排除（勿再当事实）
- **依赖混淆独立 walkthrough**：课件仅列为学习目标 `[L59]`，正文无独立实操段（gadget 段间接引用 `[L1811-1812]`）；本技能不虚构依赖混淆专项步骤，归入既有 sc-05 依赖投毒的描述强化。
- **PyRIT 作为攻击主角**：决策文档 §3.1 与矩阵 ⑪ 明确 PyRIT 在供应链面仅证据编排，不启用 `pyrit.orchestrator`。

## 4. 阶段门禁记录（G0 · 阶段1）

| 编号 | 基线 | 判定 | 证据命令 / 摘要 |
|---|---|---|---|
| B7 | PyRIT 版本与对象图 | 符合 | 模块不引入 PyRIT 攻击对象；仅既有证据 seam；`grep -rn "pyrit.orchestrator" tools/attack_supply_chain/` 无命中 |
| B8 | 可追溯性 | 符合 | §1 每条事实附课件 Listing/行号；版本闸见 §2 |
| B9 | 框架选型合规 | 符合 | 组合取自矩阵 ⑪（ModelScan + ART + PyRIT 证据 + 自定义），未偏离 |
| G0-A | 已读 §1.4 两份框架资料 | 符合 | 本会话已读 framework-decision.md 与 matrix.md 条目 ⑪ |
| G0-B | 一手源核实 | 符合 | 3.5MB HTML 提取 127k 字符逐节读取，§1 逐条锚点 |
| G0-C | 攻击路径映射 | 符合 | G1–G14 每条映射模块与步骤（见 spec v2） |

- **上游复核**：阶段1 为流程起点，N/A。
- **不符合项**：0。**阶段结论**：**PASS**。

## 5. 二次核实回填（并行 research agent，2026-11-22）

并行只读核实逐字确认 §1 全部 8 组事实、Listing 号与数值（MCP、Pickle 数值、训练投毒、LoRA、Tokenizer、Pickle 绕过、隐身后门、引言）。发现两类需记录差异：

| 差异 | 说明 | 处置 |
|---|---|---|
| 行号体系不同 | §1 的 `L<n>` 为提取纯文本（2,470 行）行号；原始 HTML 为 2,963 行，两者偏移，故部分 `L` 锚点（如 G3 格式边界、G5 休眠/量化、G7 防御、G10 八类）在 HTML 中位置不同 | Listing 号为稳定锚点；`L` 仅作提取文本内定位，实施以 Listing 号为准 |
| 课件内两个 Listing 10 | 原始 HTML L467 与 L512 均标「Listing 10」（clone mcp-biotools / clone model-checkpoints），课件自身编号重复 | 规格与实现引用改以章节 + 内容描述定位，不依赖「Listing 10-21」连续区间表述 |

经逐字比对，**无事实性矛盾**：所有数值（1519/46MB、3×10=30、74→104、88799/1317/42652/62721、r=16/alpha=32/0.14%、358→2864、133 gadgets 等）在课件中逐字存在。阶段 1 结论维持 **PASS**。

## 6. G10 进阶规避八类登记（课件 L2883-2923）

| 技术 | 适用条件 | 蓝队对策 | 状态 |
|---|---|---|---|
| 环境密钥 | 仅指定目标可解密 | 密钥派生行为与多主机快速失败 | 文档列出未实现 |
| 隐写嵌入 | 载荷藏于权重/PNG/字体 | 文件类型与内容熵不一致检测 | 文档列出未实现 |
| polyglot 文件 | 单文件同时为合法 JPEG 与 Python | 多格式解析一致性校验 | 文档列出未实现 |
| gadget 链 | 不投递代码，串联既有依赖函数 | 调用图异常与依赖最小权限 | 文档列出未实现 |
| 纯内存执行 | 网络接收后内存解密执行 | 进程行为与网络监控 | 文档列出未实现 |
| 分片装配/dead drop | 载荷跨包/环境变量/配置拆分 | 跨包字符串关联与安装期扫描 | 文档列出未实现 |
| 合法服务 C2 | Slack webhook/GitHub gist/DNS TXT | 云服务出站流量基线异常 | 文档列出未实现 |
| 环境延迟 | 按调用次数/时段/用户文件触发 | 长时行为监控与触发条件分析 | 文档列出未实现 |

实现载体：`tools/attack_supply_chain/ch8_evasion.py#all_techniques`，测试 `test_ch8_evasion.py`。
