---
name: attack-supply-chain
priority: P1
domain: D8
scoring_unit: AI向量机
trigger: recon-ai 已确认目标暴露 AI 供应链面（模型仓库/依赖源/数据管道），且已取得可达 AI 向量机的内网立足点（foothold-traditional 之后）
input: recon-ai 资产清单（模型仓库、依赖源、数据管道端点）、已取得上下文与身份
output: 每攻击步骤「命令 + 输出 + 截图」证据、投毒前后对照、下游模型行为影响取证、ai_vector.txt flag 取证（AI向量机）
---

# attack-supply-chain — AI 供应链投毒

攻击 AI 供应链，覆盖三大攻击面：**数据集/模型/适配器投毒**、**依赖/包投毒**、**下游模型行为影响取证**。技术分类对齐 OWASP Agentic ASI04（Agentic Supply Chain Vulnerabilities）与 OWASP LLM03（训练数据投毒）/ LLM05（供应链）。它污染训练或推理产物，间接影响 AI 向量机（每台 15 分）。取得内网立足点后亦向独立机延伸，形成第二个 15 分目标；两者 flag 文件均为 `ai_vector.txt`。

## 执行体

按「发现供应链面 → 数据集投毒 → 模型/适配器投毒 → 数据管道投毒 → 依赖/包投毒 → 构建/运行时触发 → 下游取证 → flag 取证」顺序推进，每步经 `tools/collect_evidence.py` 落盘证据，未过质量门不得进入下一步。

### 前置：发现 AI 供应链面

1. 复用 `recon-ai` 资产清单，确认模型仓库（如 Hugging Face / 内部 registry）、依赖源（PyPI / npm / 内部索引）、数据管道（ETL / 预处理）与信任边界。
2. 记录正常产物哈希/来源，作为后续投毒效果的对照。

### 攻击路径 A — 数据集/模型/适配器投毒

> 以下命令均为示意脚本，执行前标注来源、不伪造目标回显；证据统一经 `collect_evidence.py --strict` 落盘，关键输出运行期须注入 `--output-file`（`docs/contracts/collect_evidence.contract.md` §1）。

1. **sc-01 发现供应链面**：枚举模型仓库、依赖源、数据管道端点与信任边界。
   - 命令：`curl -s <REGISTRY>/api/models` 或 `pip index versions <pkg>`
   - 证据：`python tools/collect_evidence.py --step sc-01 --cmd "curl -s <REGISTRY>/api/models" --out loot/sc-01-supply-surface.md --shot-cmd "screenshot --region supply_surface" --target <REGISTRY> --strict`
2. **sc-02 数据集投毒**：污染训练/检索数据，使模型或 RAG 产物偏向攻击者。
   - 命令：`python tools/dataset_poison.py --data <CORPUS> --inject "<trigger>:<target>" --frac 0.01`
   - 证据：`python tools/collect_evidence.py --step sc-02 --cmd "python tools/dataset_poison.py --data <CORPUS>" --out loot/sc-02-data-poison.md --shot-cmd "screenshot --region data_poison" --target <CORPUS> --strict`
3. **sc-03 模型/适配器投毒**：植入后门权重或恶意 LoRA 适配器。
   - 命令：`python tools/model_poison.py --base <MODEL> --adapter-out loRA-bad.safetensors --trigger "<trigger>"`
   - 证据：`python tools/collect_evidence.py --step sc-03 --cmd "python tools/model_poison.py --base <MODEL>" --out loot/sc-03-model-poison.md --shot-cmd "screenshot --region model_poison" --target <MODEL> --strict`
4. **sc-04 数据管道投毒**：在 ETL / 预处理环节注入恶意变换。
   - 命令：`python tools/pipeline_poison.py --pipeline <ETL> --stage preprocess --inject "<transform>"`
   - 证据：`python tools/collect_evidence.py --step sc-04 --cmd "python tools/pipeline_poison.py --pipeline <ETL>" --out loot/sc-04-pipeline-poison.md --shot-cmd "screenshot --region pipeline_poison" --target <ETL> --strict`

### 攻击路径 B — 依赖/包投毒

5. **sc-05 依赖/包投毒**：在镜像/包索引/requirements 中注入恶意依赖（typosquat 或替换，示意脚本，须记录来源）。
   - 命令：`python tools/dep_poison.py --index <PYPI> --pkg legit --malicious legit-evil`
   - 证据：`python tools/collect_evidence.py --step sc-05 --cmd "python tools/dep_poison.py --index <PYPI>" --out loot/sc-05-dep-poison.md --shot-cmd "screenshot --region dep_poison" --target <PYPI> --strict`
5b. **sc-05b 完整性校验探测 → import 劫持降级**：观测改脚本后**时间戳**/输出是否停更，三态判 `有校验`/`无校验`/`UNDETERMINED`（不臆断），见 `tools/attack_supply_chain/integrity_probe.py#probe_integrity`。有校验→不改原脚本、先备份，同目录放同名模块**劫持 import**（`#import_hijack_plan`，Ch11 L912/L914/L981-1005）；无校验→按 sc-05 常规投毒。清理三步：删恶意模块→杀 **reverse shell** 进程→验证恢复，未验证记 pending，状态字段复用共享契约（C1 不另立清单，`#cleanup_steps`）。不伪造回显。
6. **sc-06 构建/运行时触发**：使投毒在构建或推理时执行非预期代码。
   - 命令：`python tools/trigger_poison.py --build <CI> --payload "import os; os.system('<cmd>')"`
   - 证据：`python tools/collect_evidence.py --step sc-06 --cmd "python tools/trigger_poison.py --build <CI>" --out loot/sc-06-trigger.md --shot-cmd "screenshot --region trigger" --target <CI> --strict`

### 攻击路径 C — 下游取证与 flag

7. **sc-07 下游模型行为影响取证**：对比投毒前后模型输出/检索结果，证明行为被影响，含 AI 交互日志（§6.3）。
   - 命令：`curl -s <MODEL_API>/generate -H "Content-Type: application/json" -d '{"prompt":"<trigger>"}'`
   - 证据：`python tools/collect_evidence.py --step sc-07 --cmd "curl -s <MODEL_API>/generate -d '<trigger prompt>'" --out loot/sc-07-impact.md --shot-cmd "screenshot --region impact" --ai-log "见 loot/sc-07-impact.md" --target <MODEL_API> --strict`
8. **sc-08 flag 取证（AI向量机）**：取得供应链代码执行/数据访问后定位并读取 `ai_vector.txt`；向独立机延伸供应链投毒重复上述流程。
   - 命令：`whoami; id; find / -name ai_vector.txt 2>/dev/null -exec cat {} \;`
   - 证据：`python tools/collect_evidence.py --step sc-08 --cmd "whoami; id; find / -name ai_vector.txt 2>/dev/null -exec cat {} \;" --out loot/sc-08-flag.md --shot-cmd "screenshot --region flag_proof" --ai-log "见 loot/sc-08-flag.md" --flag "<ai_vector.txt 值>" --target <AI_VECTOR_HOST> --strict`
9. 取证须含访问证明：`whoami`/`id` + flag 内容同屏截图（对齐 §6.2 双通道一致）。

### 攻击路径 D — Ch8 课件攻击链（sc-09..sc-14，独立注册表）

> 以下六步为 OffSec AI-300 Ch8 差距补齐，独立于 sc-01..08 的 `STEP_IDS`（既有 8 步与证据夹具不变）；统一经 `tools/attack_supply_chain/ch8_steps.py` 派发，证据沿用 `collect_evidence.py --step <id> --strict`。全部为本地 mock / 确定性实现，不向演练目标落真实恶意载荷。

10. **sc-09 MCP 源码后门**：研读合法 server（FastMCP / `@mcp.tool()` / docstring 即描述）→ 选埋入高频 helper（`list_all`）→ 伪装身份通用提交 → 推送 → 等待窗口（≤4 分钟）。命令：`python -m tools.attack_supply_chain.mcp_backdoor --server <S> --helper <H> --author <A> --email <E>`。证据：`collect_evidence.py --step sc-09 ... --strict`。
11. **sc-10 Pickle RCE**：`__reduce__`→`(os.system,cmd)`、`weights_only=False`、命名 `{model}_epoch_{NNN}.pt` 取最高 epoch、体积差 1,519 B vs ~46 MB 检测信号；与 `model_scan.scan()` 联动做投放前后对照。命令：`python -m tools.attack_supply_chain.pickle_rce --base <M> --epoch <N> --cmd <C> --files <F...>`。
12. **sc-11 训练投毒放大**：JSONL `instruction`/`output` 3 样本×10→30、74→104 行（约 29%）、`finetune.py --epochs 7 --lr 5e-5 --max-length 384`、cron 2 分钟；休眠代理三类触发与量化 SHA-256 缺口一并记录。命令：`python -m tools.attack_supply_chain.amplification --samples 3 --base 74 --factor 10`。
13. **sc-12 LoRA 适配器投毒**：从 `adapter_config.json` 还原 r=16/alpha=32/dropout=0.05、SMB 主机/IP 替换为攻击者 IP、0.14% 参数与 8MB/3GB 体积对照、serving 与 NTLMv2 判据。命令：`python -m tools.attack_supply_chain.adapter_poison --ip <IP> --text <T>`。
14. **sc-13 Tokenizer 操纵**：`MAL`↔`FUN` 交换（MALICIOUS 拆 88799/1317/42652、FUN=62721），须同改 `vocab.json` 与 `tokenizer.json`、备份、fail-open 判 SAFE 的 before/after；防御为哈希校验 + fail-closed。命令：`python -m tools.attack_supply_chain.tokenizer_swap --vocab <V> --fast <F>`。
15. **sc-14 Pickle 扫描器绕过**：`GLOBAL+REDUCE` opcode、三变体（baseline / `__setstate__` 类 / `sympy.sympify` gadget）、跨机器判定、133 gadgets；绕过载荷经扫描应干净作反向证据。命令：`python -m tools.attack_supply_chain.pickle_bypass --list`。
- 支撑模块（按课件锚点引用、不新增步骤标识）：格式矩阵 `format_matrix.py`、隐身后门 `stealth_backdoor.py`、进阶八类 `ch8_evasion.py`、六组件与 AI BOM `surface_fields.py`。
- 对齐验证：`python -m tools.attack_supply_chain.alignment --render` 须输出 14/14 PASS（G1–G14 四元组齐全）方可收尾。

## Ch9 运行时/工件边界（加固版，不改既有投毒判据）

事实源 `docs/research/attack-supply-chain-ch9-b6-hardening-canonical.md`（B6-1..B6-5）。类型化 `ch9_boundary_model.py#BoundaryVerdict`；路由 `ch9_boundary.py#classify`；strict 证据 `ch9_boundary_evidence.py#emit_strict_evidence`（`build_evidence_argv`）；编排 `ch9_boundary_runner.py#run_boundary`（均在 `tools/attack_supply_chain/`）。

| 观察信号 | owner | 转交目标（路径#锚点） |
|---|---|---|
| sidecar/init/共享卷/exec（L54-55） | attack-infra | `tools/attack_infra/ch9_container.py#writable_shared_volume`、`tools/attack_infra/ch9_container.py#intercept_verdict` |
| model/artifact/minio/registry/投毒（L53） | 本技能 | `tools/attack_supply_chain/poison_engine.py#poison_model` |
| 双向信号 | 本技能 + `ambiguous` | 人工复核后分别转交 |

**能力边界**：不实现 Sidecar 拦截本体（attack-infra B2）、不改 Ch8 判据、不执行载荷；判定经 `collect_evidence.py --strict` 落盘三件套。复验：`python scripts/verify_asc_b6_skill_refs.py && python scripts/verify_asc_b6_coverage.py --min 90`。

## 质量门

以下证据**必须**全部产出，缺失任一即未过门禁：

- 每步**确切命令**（可 copy/paste）、**关键输出**（投毒生效/行为偏移/触发响应原文）、**截图**（访问证明，含目标标识与时间戳）。
- **投毒前后对照**（before/after）、**下游行为影响取证**（输出/检索差异，含 AI 日志 §6.3）。
- `ai_vector.txt` flag「面板提交+截图」双通道一致。
- 每步证据经 `tools/collect_evidence.py` 产出，三件/五件套结构与 `report-exam` Attack Walkthrough 兼容、可由 CI 校验。

## 校验标准

- 攻击过程可被 **copy/paste 逐步复现**（§6.1）；证据与 `report-exam` Attack Walkthrough 兼容、**无损复用**。
- 每步满足「命令+输出+截图」三件套；术语符合 `GLOSSARY.md`（「AI向量机」「供应链」「投毒」等规范词，禁用 `_Avoid_` 废弃术语）。

## 失败与豁免

- 目标无供应链面→记录依据后改走 `attack-rag`/`attack-embeddings`，不阻塞其余。
- 投毒部分生效→如实记命中率不夸大；恶意依赖被签名/护栏拦截→记录原因改走其它路径，不反复重试同一被拦截动作。
- 疑似诱饵机（0 分、无 AI 面）→记录依据后 ≤30min 结束。
- 改生产模型/权重前须显式授权且在范围内；不擅自重训（可退化性能、破坏对齐、引入法规责任）。
- 目标操作系统未知时对 `creationflags` 作平台判断；Windows 专有常量（如 `0x01000000`）在非 Windows 上须跳过，不得无条件传入。
- 训练与载荷准备在攻击者自有基础设施完成，不在目标侧留下训练日志、GPU 峰值或临时文件等取证痕迹；课件攻击链均为本地 mock，不向演练目标落真实恶意载荷。

> 主线：`docs/operations/skill-mainline-workflow.md`（C1/C8：11 阶段、to-spec 两遍、G0）。
