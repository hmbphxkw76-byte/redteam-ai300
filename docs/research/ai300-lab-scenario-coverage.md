# AI-300 官方实验场景 × 本项目技能覆盖分析

## 1. 结论摘要

对 `D:\下载\temp\lab`（OffSec AI-300 培训文档 12 章 + MegaCorpOne 三区靶场手册 + 拓扑图）中的 **50 个可攻击场景**逐条比对 `skills/*/SKILL.md` 与其实现模块，结论如下：

| 判定 | 数量 | 占比 |
|---|---|---|
| 完整覆盖 | 30 | 60% |
| 部分覆盖 | 13 | 26% |
| 未覆盖 | 7 | 14% |

**总体判定：主体覆盖，结构性缺口仅剩 AD 域渗透。**

1. **AI 攻面向覆盖度高**：Ch3–Ch10 的 agent / A2A / RAG / embedding / MCP / 供应链 / 基础设施 / 威胁建模场景，均有对应技能的稳定 step_id 与证据契约承载，未发现「文档有、技能无」的整类 AI 攻击面缺失。
2. **传统侧存在结构性缺口**：Ch11 的 AD 域渗透（Kerberos、ADCS、DCSync、跨域信任）在 `skills/` 内**无任何承载技能**；`foothold-traditional` 止于入口/横向/本地提权，`capstone-rehearse` 仅做走查与缺口登记。该缺口直接对应 capstone 的 Domain Admin 目标与 `proof.txt` 计分。
3. **环境搭建类条目不计入覆盖判定**：Ch1 的 VM/Docker 基线、Ch2 的 13 容器编排、Ch9 的 LocalStack/k3s 搭建属靶场构建，不属攻击能力；本文仅在影响演练复现时标注（见 §5）。

## 2. 判定标准

| 判定 | 定义 |
|---|---|
| 完整覆盖 | 技能内存在专门 step_id（或章节级增量）承载该场景的攻击动作、判据与证据要求，且可直接映射到 `report-exam` 的攻击过程小节 |
| 部分覆盖 | 通用步骤可覆盖攻击动作，但缺该场景的关键判据、载荷形态或下游载体（如「仅通用入口利用」覆盖 LFI） |
| 未覆盖 | `skills/` 与 `tools/` 内无对应实现或判据；通用技能不构成实质承载 |

依据口径：只认 `skills/<name>/SKILL.md` 的 step_id 契约与 `tools/<pkg>/` 的实现入口；关键词命中但无判据的，按「部分覆盖」处理，不按「完整覆盖」计。

## 3. 场景覆盖矩阵

### 3.1 Ch1 基线环境与 Ch2 侦察

| 章 | 攻击场景（文档依据） | 项目承载 | 判定 |
|---|---|---|---|
| ch01 | chat01 门户访问与会话复用（§0.1 目标 3） | `recon-ai` recon-01/02/07；`attack-ai-agent` 会话枚举（Listing 47-51） | 部分：有会话枚举与跨会话提取，无 Cookie 窃取/重放判据 |
| ch01 | LFI `/app/view.php?page=`（S9） | `foothold-traditional` trad-01/trad-02 | 部分：仅通用入口枚举与 MSF 利用，无 LFI 专项判据 |
| ch02 | 模型指纹（`/v1/models`、`/health`、错误页差异） | `recon-ai` recon-01/02 + `tools/recon_ai/ch2.py` | 完整 |
| ch02 | MCP 协议发现（`/.well-known/mcp.json`） | `recon-ai` recon-06 | 完整 |
| ch02 | GitLab 凭据泄露（仓库 `.env`） | `foothold-traditional` trad-05（Ch11 PAT 场景） | 部分：覆盖 Ch11 dev 主机 PAT，无 Ch2 克隆取 `.env` 路径 |
| ch02 | 影子 API 端点（webapp02 未公开 location） | `recon-ai` recon-05 + `tools/recon_ai/shadow.py` | 完整 |
| ch02 | RAG 知识库会话式接口 | `recon-ai` recon-03/04；`attack-rag` rag-00 | 完整 |
| ch02 | SIEM 可观测与日志分析闭环 | `attack-ai-agent` 五步闭环；`attack-rag` detect/confirm；`recon-ai` recon-07 | 完整 |

### 3.2 Ch3 单代理与 Ch4 多代理

| 章 | 攻击场景（文档依据） | 项目承载 | 判定 |
|---|---|---|---|
| ch03 | 提示注入操控工具 | `attack-ai-agent` 路径 A（aia 系列） | 完整 |
| ch03 | 工具参数强制（`http_get` 无白名单） | `attack-ai-agent` 路径 C；`attack-mcp-tool` mcp-05 | 完整 |
| ch03 | 工具结果投毒 | `attack-ai-agent` 路径 C；`attack-rag` 间接注入 | 完整 |
| ch03 | 社工凭据窃取（8080 密码重置门户） | 无 | **未覆盖** |
| ch03 | 内部 Wiki / SQL 读取 | `attack-ai-agent` C-子步（`xp_cmdshell` 升级） | 完整 |
| ch03 | 对象存储写入（`s3_put` → MinIO） | `attack-ai-agent` 越权调用；`attack-infra` S3 面 | 部分：无对象存储写入/外泄专项判据 |
| ch04 | A2A 服务发现（`agent.json`） | `recon-ai` recon-05 补录 + `attack-multi-agent` a2a-01 | 完整 |
| ch04 | 恶意 Agent Card 抢注册（C14/C15） | `attack-multi-agent` a2a 专项表 | 完整 |
| ch04 | 任务队列注入（Redis 无认证） | `attack-multi-agent` a2a-05（Redis 基线） | 完整 |
| ch04 | Agent 身份冒充（C16） | `attack-multi-agent` a2a-04 / C16 | 完整 |
| ch04 | Windows 凭据面 RDP / MSSQL / WinRM | `foothold-traditional` trad-03（RDP Gateway）；`attack-multi-agent` C13（MSSQL） | 部分：WinRM 无对应判据 |

### 3.3 Ch5 RAG 与 Ch6 Embedding

| 章 | 攻击场景（文档依据） | 项目承载 | 判定 |
|---|---|---|---|
| ch05 | 文档投毒改变 Top-K | `attack-rag` rag-01..rag-03 | 完整 |
| ch05 | 检索劫持（`file_read` → `/etc/passwd`） | `attack-rag` rag-02/rag-04 | 完整 |
| ch05 | 向量库未授权访问（Chroma 8001） | `attack-rag` + `attack-embeddings` | 完整 |
| ch05 | 追踪服务未授权（Phoenix 11434） | 无 | **未覆盖** |
| ch05 | 外部「紧急恢复服务」社工诱饵 | `decoy-detect`（仅诱饵机识别与时间盒） | 部分：识别诱饵，不承载社工话术与凭据诱导 |
| ch05 | WinRAG（Windows 文档索引形态） | 无 | **未覆盖**（平台形态，攻击语义由 rag-01..05 覆盖） |
| ch06 | 嵌入提取与向量反查 | `attack-embeddings` emb-c1..emb-c6 | 完整 |
| ch06 | 元数据面枚举（GraphQL Aggregate） | `recon-ai` recon-05 introspection | 部分：仅 schema 探测，无聚合泄露判据 |
| ch06 | 投毒影响量化 | `attack-embeddings` emb-07；`attack-rag` before/after | 完整 |

### 3.4 Ch7 MCP 与 Ch8 供应链

| 章 | 攻击场景（文档依据） | 项目承载 | 判定 |
|---|---|---|---|
| ch07 | 工具投毒 | `attack-mcp-tool` mcp-02/mcp-03 | 完整 |
| ch07 | 工具影子（同名工具优先命中） | `attack-mcp-tool` mcp-02 | 部分：覆盖恶意 server 部署，无同名影子优先判据 |
| ch07 | 中间人替换工具清单 | `attack-mcp-tool` mcp-03/mcp-06 | 完整 |
| ch07 | 开放重定向（GitLab OAuth 回调） | 无 | **未覆盖** |
| ch08 | GitLab CI 投毒 | `attack-supply-chain` sc-06（`pipeline_poison.py`） | 完整 |
| ch08 | pickle 反序列化 | `attack-supply-chain` sc-10 | 完整 |
| ch08 | LoRA adapter 投毒 | `attack-supply-chain` sc-12 | 完整 |
| ch08 | 模型权重替换（model-hub 覆盖） | `attack-supply-chain` sc-03 | 部分：覆盖模型/适配器投毒，无工件替换检测判据 |
| ch08 | SMB 横向（hou-fs01 → dal-fs01） | `foothold-traditional` trad-06 | 部分：通用横向，无 SMB 凭据复用专项判据 |

### 3.5 Ch9 基础设施、Ch10 威胁建模与 Ch11 Capstone

| 章 | 攻击场景（文档依据） | 项目承载 | 判定 |
|---|---|---|---|
| ch09 | API GW SSRF → VPC 内 Wrapper | `foothold-traditional` trad-09；`attack-infra` | 完整 |
| ch09 | IAM 角色链与 assume-role | `attack-infra` ch9-iam-01/03 | 完整 |
| ch09 | K8s 身份链与跨命名空间 | `attack-infra` ch9-k8s-01/02/04 | 完整 |
| ch09 | 五服务凭据（S3/SSM/KMS/SecretsManager/ECR） | `attack-infra` ch9-sec-01..03 | 完整 |
| ch09 | etcd 快照导出与 Secret 泄露 | 无 | **未覆盖** |
| ch09 | GPU 主机容器逃逸（CVE-2025-23266） | `attack-infra` ch9-gpu（条件判定，无靶场即 BLOCKED） | 部分：只做版本阈值与注入面判定，不编译载荷 |
| ch09 | DynamoDB 数据面 | 无 | **未覆盖**（低权重） |
| ch10 | 8 类服务测绘与固定 IP | `recon-ai` 全流程 | 完整 |
| ch10 | STRIDE 工作表 | `threat-model` §5（Ch10 增量） | 完整 |
| ch10 | 三条风险链验证 | `threat-model` + `recon-ai` | 完整 |
| ch11 | 三域森林、双向信任、双归属主机 | `foothold-traditional` trad-05/06（横向） | 部分：覆盖横向路径，不承载域信任滥用 |
| ch11 | 课程 10 步攻击路径验收 | `capstone-rehearse` 全谱系走查 | 部分：走查与缺口登记，不执行 AD 利用 |
| ch11 | AD 域提权与域控收敛（含 ADCS、Kerberos） | 无 | **未覆盖** |
| ch11 | 域控 `proof.txt` 单次提交 | `verify-evidence`（proof-single 约束） | 完整（提交侧完整，依赖上一行攻击侧补齐） |

## 4. 缺口清单（按得分相关性 × 实现成本排序）

| 优先级 | 缺口 | 得分相关性 | 实现成本 | 建议落点 |
|---|---|---|---|---|
| P0 | AD 域渗透与域控收敛 | 高：capstone 目标为 Domain Admin，`proof.txt` 属高杠杆计分 | 高：需新增技能与证据契约 | 新增 `foothold-ad`（或不扩充 `foothold-traditional` 的 Ch11 章），以离线解析器 + 工件夹具为主，无域环境标 `BLOCKED` |
| P0 | 影子 API 端点发现 | 中：Ch2 明确侦察目标，直接影响资产清单完整性 | 低：`recon-ai` 增判据 | **已实施**（recon-05「关键输出」+ `shadow.py`，不新增 step_id） |
| P1 | 追踪服务未授权（Phoenix/MLflow UI） | 中：数据面外泄入口，常与 RAG 链串联 | 低：`attack-rag` 增一步 | rag-11（或并入 rag-00 面定位） |
| P1 | 元数据聚合枚举（GraphQL Aggregate） | 中：Ch6 目标 3 的独立攻击面 | 低：`attack-embeddings` 增 emb-c9 | 复用 recon-05 introspection 结果 |
| P1 | 社工诱饵与凭据诱导 | 中：Ch3/Ch5 双处场景 | 低：话术剧本 + 证据模板 | 由 `decoy-detect` 扩展为「诱饵识别 + 社工面处置」 |
| P1 | etcd 快照导出与 Secret 泄露 | 中：K8s 集群级凭据泄露 | 中：需快照解析与离线取证 | `attack-infra` ch9-etcd-01/02 |
| P2 | 工具影子优先命中 | 中：Ch7 独立攻击面 | 低 | `attack-mcp-tool` mcp-02 增判据 |
| P2 | 模型权重替换 | 中：Ch8 环节 | 低 | `attack-supply-chain` sc-03 增工件替换判据 |
| P2 | SMB 凭据复用横向 | 低中：Ch8/Ch11 共用 | 低 | `foothold-traditional` trad-06 增 SMB 分支 |
| P2 | WinRM 面 | 低 | 低 | `attack-multi-agent`/`foothold-traditional` 增枚举项 |
| P3 | 开放重定向（OAuth 回调） | 低：Ch7 入口链一环 | 低 | `attack-mcp-tool` 前置面增判据 |
| P3 | DynamoDB 数据面 | 低 | 低 | `attack-infra` ch9-sec 扩展 |
| P3 | Cookie 会话劫持/复用 | 低中：Ch1 前置条件 | 低 | `attack-ai-agent` 会话段增判据 |
| P3 | LFI 专项 | 低：通用利用已覆盖 | 低 | `foothold-traditional` 手法库增条目 |
| P3 | WinRAG 形态 | 低：平台差异 | 中 | 不改技能，`capstone-rehearse` 标注环境差异 |

## 5. 环境形态差异（不构成能力缺口，但影响复现）

以下为文档特有的**宿主形态**，与技能的攻击语义无关，但会使「照文档复现」与「技能直接执行」脱节，`capstone-rehearse` 的环境标注应覆盖：

1. Ch1 的离线 Ollama、Ch7 的本地推理中继（relay 8000）替代公网共享推理——技能默认走 OpenAI 兼容端点，需在演练语境显式声明端点替换。
2. Ch5 WinRAG、Ch4 Windows A2A 平台、Ch9 LocalStack Pro——技能不依赖宿主 OS，但证据截图的「目标标识」字段需按实际主机名登记。
3. Ch11 的 25 节点三区拓扑属**搭建工程**，`capstone-rehearse` 只做走查；若以本拓扑做演练，需先确认 VPN 与双归属通道（手册 §1.2）已通，否则 `threat-model` 的路径假设不成立。

## 6. 反向观察：项目能力超出本文档

以下技能在 12 章内**无对应实验场景**，说明覆盖是不对称的（技能面宽于本套实验文档）：

- `attack-jailbreak`：文档未设独立护栏绕过章；Ch1/Ch7 仅在提示注入中以一句话提及。
- `attack-multimodal`：文档无跨模态章节。
- `osai-orchestrator`、`tooling-automate`、`loot-manage`、`report-exam`、`verify-evidence`：流程与证据类，不对应具体攻击场景。

## 7. 附：来源与口径

- 文档源：`D:\下载\temp\lab\ch00.md`–`ch11.md`、`MegaCorpOne-三区靶场环境搭建手册.md`、`AI-300-lab-topology.html`（场景抽取依据各章 §0.1 目标与 §4.3 攻击面核对表）。
- 技能源：`skills/*/SKILL.md`（step_id 契约）、`tools/*/`（实现入口）。
- 判定口径见 §2；未纳入判定的环境搭建条目见 §5。
