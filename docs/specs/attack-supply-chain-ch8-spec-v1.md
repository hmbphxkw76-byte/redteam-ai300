## 1. Problem Statement

Ch8 差距审阅发现 `attack-supply-chain` 现为「骨架+示意脚本」：8 步覆盖投毒面种类，但未落地课件任一具体攻击链。需补齐 G1–G14，交付可本地端到端复现、证据可审计的实现；目标侧不可测时以本地 mock 如实标注，不冒称目标侧信号。

## 2. Solution

沿用矩阵⑪框架组合（ModelScan 静态扫描 + IBM ART 投毒 + PyRIT 证据 + 自定义脚本），以新增 sc-09..sc-14 独立步骤标识承接课件攻击链，不改既有 sc-01..08 契约与 STEP_IDS（既有夹具断言 len=8）。每步经 collect_evidence.py 落三/五件套；对齐验证矩阵逐条证明「课件锚点↔实现↔测试↔证据」四元组。

## 3. User Stories（长清单）

- US-G1 [P0] MCP 源码后门：研读合法 server（FastMCP/@mcp.tool()/docstring）、埋高频 helper、伪装身份通用提交、推送触发与等待窗口判据（§8.1 Listing 1-9）。
- US-G2 [P0] Pickle RCE：__reduce__→(os.system,cmd)、weights_only=False、最高 epoch 投放、跨用户横向移动取证、体积差信号（§8.1 Listing 10-21）。
- US-G3 [P1] 跨框架格式矩阵：joblib/pandas、TF SavedModel tf.py_function、ONNX 路径穿越、SafeTensors 不防权重投毒（§8.1 L590-622）。
- US-G4 [P0] 训练投毒放大：3×10→30、JSONL instruction/output、finetune.py 参数、cron 2 分钟、备份与授权（§8.2 Listing 29-38）。
- US-G5 [P1] 休眠代理与量化缺口：条件触发、SHA-256 无数学关系（§8.2 L1064-1106）。
- US-G6 [P0] LoRA 完整链：adapter_config 参数还原、SMB 主机/IP 替换、0.14% 参数、serving、NTLMv2（§8.2 Listing 41-50）。
- US-G7 [P0] Tokenizer 交换：MAL↔FUN、双文件一致、fail-open 判 SAFE、备份与恢复（§8.2 Listing 57-63）。
- US-G8 [P0] Pickle 扫描器绕过：GLOBAL+REDUCE opcode、__setstate__ 类绕过、sympy gadget、三载荷对照、133 gadgets（§8.3 Listing 64-75）。
- US-G9 [P1] 隐身后门三层：XOR .dat、零宽 bootstrap、反沙箱清单、start_new_session、蓝队检测（§8.3 Listing 76-82）。
- US-G10 [P2] 进阶规避八类：环境密钥、隐写、polyglot、gadget 链、内存执行、分片装配、合法服务 C2、环境延迟（§8.3 L2393-2437）。
- US-G11 [P1] Recon 字段：GitLab 组权限、共享模型目录、config.yaml 模型/tokenizer 路径（recon-ai 只读探针）。
- US-G12 [P1] 六组件信任面+NIST AML/MITRE ATLAS+AI BOM+三案例（§8 L29-38，threat-model + sc-01）。
- US-G13 [P2] 证据契约回归：三/五件套、前后对照、flag 双通道、parse_fragment 无损；契约不改，仅登记新步骤。
- US-G14 [P1] 交战规则边界：改生产模型须授权、creationflags 平台判断、不留取证痕迹、不重试被拦截。
- US-QM1 每步确切命令可 copy/paste（质量门）。
- US-QM2 每步关键输出原文（质量门）。
- US-QM3 每步截图含目标标识与时间戳（质量门）。
- US-QM4 投毒前后对照证据（质量门）。
- US-QM5 下游行为影响 + AI 交互日志（质量门）。
- US-QM6 flag 双通道一致（质量门）。

## 4. Implementation Decisions（不含文件路径/代码片段）

- ID-01 新增步骤用 sc-09..sc-14 独立标识，独立注册表，不注入 STEP_IDS；既有 8 步与证据夹具不动。
- ID-02 新攻击链模块为确定性纯函数 + 显式规则 + 可注入 runner，不落真实恶意载荷到目标。
- ID-03 ModelScan seam 复用为「反向证据」：绕过载荷经扫描应干净，证明扫描器局限。
- ID-04 ART seam 仅在有 estimator 时启用，缺失时显式报错或记录未实现原因，不静默产出。
- ID-05 协同 skill 最小增量：attack-mcp-tool（源码后门变体）、recon-ai（只读字段）、threat-model（六组件/AI BOM）。
- ID-06 GLOSSARY 优先复用既有术语；确需新增须先腾空间，不改并行会话共用行。

## 5. Testing Decisions

- TD-01 只测外部行为（模块输入→输出契约、证据三/五件套、flag 双通道），不断言实现细节。
- TD-02 每条 AC-Gn 有对应失败用例（红）→实现（绿）→重构三轮留痕。
- TD-03 对齐验证矩阵 14 行，每行四元组齐全才判 PASS。
- TD-04 全量 unittest + 新包覆盖率 ≥80%。

## 6. Out of Scope

- OS-01 演练目标实际执行（目标不在本任务网络）。
- OS-02 真实反弹 shell / C2 投递到目标环境。
- OS-03 依赖混淆独立步骤（课件无实操 walkthrough，归入 sc-05 描述强化）。
- OS-04 promptfoo / garak（矩阵⑪未纳入本技能主控）。

## 7. Further Notes

- FN-01 一手源见 docs/research/attack-supply-chain-ch8-canonical.md（阶段1）。
- FN-02 版本闸见 canonical §2；运行时不依赖 ModelScan/ART 实际安装。
- FN-03 计分单元 AI向量机 15 分/台，flag 文件 ai_vector.txt。

## 8. Seam 提案（阶段2 与用户约定）

- S1–S5 既有 seam 复用（证据/投毒引擎/模型扫描/注入器/recon 输入）。
- S6 新增：课件攻击链模块注册表（sc-09..sc-14 独立，不注入 STEP_IDS）。
- S7 新增：对齐验证矩阵生成器（G1–G14 四元组）。
> 用户已在启动提示词中预核对 seam 方向（新增步骤独立标识、不改既有 8 步），本阶段按该确认落地。
