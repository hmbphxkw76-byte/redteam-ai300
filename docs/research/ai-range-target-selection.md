# OSAI 等效靶场演练目标选型（P0/P1）

> **性质**：研究/决策文档，非规范正文。为现有 AIVP/DVAA 环境补齐 OSAI AI-300 全场景覆盖的演练目标选型与 10 主机拓扑。
> **核验日期**：2026-11-17（GMT+8）。热度/许可为当日 GitHub 观测值；部署前复核 README 与 LICENSE。
> **分值依据**：`../governance/GOVERNANCE.md` §2.1–§2.3；官方事实见 `../governance/references/OSAI-Exam-Guide-snapshot.md`。本文件只给选型与推导，不复述考试条款。

## 1. 结论

1. **现有环境是 AI 技巧练习场，不是 10 主机考试靶场**：AIVP 189 的 45 个 lab 适合技巧练习，但 `../operations/attack-mcp-tool-verification.md` 记录目标无 `ai_vector.txt`、路径 A 无第三方 server 接入面；DVAA 183 的 A2A 标准端点实测 404（`../../report/attack-multi-agent-live-validation-20261115.md`）；`attack-rag` 目前是合成 harness、零网络（`../operations/attack-rag-verification.md`）；`attack-infra` 在 189 未取得立足点（`../operations/attack-infra-verification.md`）。
2. **P0 及格线**：4 台 AI 向量 ×15 + 1 台独立 AI ×15 = **75 分**。**P1 真实拓扑**：再加 2 台传统 ×10 + DC ×5 = **25 分**，合计 **100 分**。
3. **推荐组合**：AIGoat + DVMCP（或 Appsecco）+ A2A samples/A2ASecBench + Kubernetes Goat + DVAR；P1 用 Vulhub + GOAD MINILAB + 2 台 decoy + CTFd。
4. **两处必须自建薄层**：A2A 没有现成“故意可攻破”的演练目标，需官方 samples 弱配置；embedding 反演没有与 `vec2text` 预训练匹配的现成演练目标，需 gtr-base 薄服务。其余均有成熟仓库。

## 2. P0：AI 向量主分面

| 角色/分值 | 选型 | 热度/许可（2026-11-17） | 用途 | 主要限制 |
|---|---|---|---|---|
| AI-01 / 15 | [AIGoat](https://github.com/AISecurityConsortium/AIGoat) | 307★ · Apache-2.0 | 46 个 lab、9 个 CTF、可投毒向量库、MCP host、Agentic Kill Chain；映射 OWASP LLM/Agentic/MCP | 单应用；无原始向量库暴露；无考试 flag 格式 |
| AI-02 / 15 | [DVMCP](https://github.com/harishsg993010/damn-vulnerable-MCP-server) | 1,373★ · **无 LICENSE** | 15 个 Streamable HTTP MCP server，9001–9015；工具投毒、rug pull、token theft、RCE、权限提升、供应链 | 仅限本地个人 lab；Windows 不稳定 |
| AI-02 备选 | [Appsecco MCP lab](https://github.com/appsecco/vulnerable-mcp-servers-lab) | 284★ · MIT | 9 个 MCP server，含远程 HTTP+SSE、路径穿越、代码执行、间接注入、密钥/PII、typosquatting | 无统一 compose，需逐 server 启动 |
| AI-03 / 15 | [a2a-samples](https://github.com/a2aproject/a2a-samples) + [A2ASecBench](https://github.com/SaFo-Lab/A2ASecBench) | 1,836★ · Apache-2.0；12★ · MIT · ICLR 2026 | 官方真实 A2A agent/host；6 类协议攻击：AgentCard spoofing、capability cloaking、ASRF、ATSI、CO、HOTF | samples 非故意漏洞；需弱配置 |
| AI-04 / 15 | [Kubernetes Goat](https://github.com/madhuakula/kubernetes-goat) | 5,959★ · MIT | 20 个 k8s 场景：DIND、SSRF、RBAC、secrets、容器逃逸、供应链 | 需 cluster-admin；必须独立集群 |
| AI-05 / 15 | [DVAR](https://github.com/0xsu3ks/DVAR-Damn-Vulnerable-Agentic-RAG) | 10★ · MIT | 13 个 flag；Chroma 8200 无鉴权；RAG 投毒、SQLi、SSRF、XSS、过度代理、向量库直读 | 默认依赖 AWS Bedrock |
| D6 工具 | [vec2text](https://github.com/vec2text/vec2text) + [Jina demo](https://github.com/jina-ai/embedding-inversion-demo) | 1,150★ · Other；61★ · Apache-2.0 | vec2text 预训练支持 `gtr-base` / `text-embedding-ada-002`；Jina 支持 Qwen3/Jina v3/EmbeddingGemma | vec2text 是工具；Jina 需 checkpoint/GPU |

### 2.1 P0 启动摘要

```bash
# AI-01 AIGoat：Docker 至少 12GB RAM，首次拉 Mistral 约 4.5GB
git clone https://github.com/AISecurityConsortium/AIGoat.git
cd AIGoat && docker volume create ollama_models
cd docker && docker compose up --build
# :3000 前端；:8000 API；:11434 Ollama

# AI-02 DVMCP：Linux 环境
git clone https://github.com/harishsg993010/damn-vulnerable-MCP-server.git
cd damn-vulnerable-MCP-server
docker build -t dvmcp . && docker run -d --name dvmcp -p 9001-9015:9001-9015 dvmcp
# challenge 1: http://<host>:9001/mcp；其余 9002–9015

# AI-03 A2A：官方 sample + 基准
cd a2a-samples/samples/python/agents/helloworld
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && python __main__.py

git clone https://github.com/SaFo-Lab/A2ASecBench.git
cd A2ASecBench && pip install -e ".[dev]"
python orchestration.py --config configs/offline/asrf_eval.yaml --trials 1
# 其他：atsi_eval / co_eval / hotf_eval；LLM 模式需 SUT_API_BASE/KEY/MODEL

# AI-04 Kubernetes Goat：独立 Kind 集群，不要放共享集群
kind create cluster --name goat
git clone https://github.com/madhuakula/kubernetes-goat.git
cd kubernetes-goat && bash setup-kubernetes-goat.sh && bash access-kubernetes-goat.sh

# AI-05 DVAR：默认需 AWS Bedrock；零外部依赖需改 LLM/embedding 适配
git clone https://github.com/0xsu3ks/DVAR-Damn-Vulnerable-Agentic-RAG.git
cd DVAR-Damn-Vulnerable-Agentic-RAG && cp .env.example .env
docker compose up --build -d
# :3000 前端；:8000 API；:8200 Chroma
```

### 2.2 P0 关键判断

- **A2A 是最大缺口**：官方 samples 是“正常实现”，不是故意漏洞。需做弱配置：去掉 AgentCard 签名、允许任意 peer URL、artifact 直接渲染、不设 delegation depth/task 上限；再用 A2ASecBench 的 ASRF/ATSI/CO/HOTF 判定。这是 P0 唯一需要写代码的演练目标。
- **D6 反演缺现成演练目标**：DVAR 的 Chroma 可直读，但 embedding 是 Bedrock Titan，`vec2text` 预训练不直接支持。最省事的做法是加一个 FastAPI + `sentence-transformers/gtr-t5-base` 的 `/embed` 服务（无鉴权、seed 秘密文档），用 `vec2text.load_pretrained_corrector("gtr-base")` 反演；Jina demo 更强但需 checkpoint/GPU。
- **DVAR 默认不是零外部依赖**：`llm_service.py` 走 Bedrock Converse，`.env.example` 还有 Titan embedding；要么改成本地 Ollama/OpenAI-compatible，要么用 [Shaheer RAG](https://github.com/Shaheer-Cybersec/damn-vulnerable-rag)（1★、MIT、LangChain+Chroma+Ollama，4 类 OWASP LLM 漏洞）作为降级 standalone。
- **DVMCP 无 LICENSE**：GitHub API 返回 `license=null`，只适合本地个人 lab；团队使用请换 Appsecco（MIT）。`mcp-breach-to-fix-labs` 也无 LICENSE，但其 10 个真实事件 + vulnerable/secure 双版本适合做证据级验证。

## 3. P1：及格线与真实拓扑

| 角色 | 选型 | 热度/许可（2026-11-17） | 用途 | 备注 |
|---|---|---|---|---|
| TRAD-01 | [Vulhub](https://github.com/vulhub/vulhub) | 21,501★ · MIT | 预构建 Docker Compose 漏洞环境，一条命令起一个 CVE | 最容易落地的 10 分 |
| TRAD-02 + DC-01 | [GOAD](https://github.com/Orange-Cyberdefense/GOAD) | 8,630★ · GPLv3 | MINILAB：2 台 VM（DC WinServer2019 + Win10）；GOAD-Light：3 台 VM | 最小 AD/DC 组合；Windows 评估版 180 天 |
| 传统备选 | [Metasploitable3](https://github.com/rapid7/metasploitable3) | 5,790★ · Other | Vagrant/Packer 的 Linux/Windows 漏洞 VM | 比 Vulhub 重，适合补 OS 提权 |
| Web 备选 | [Juice Shop](https://github.com/juice-shop/juice-shop) | 14,460★ · MIT | 现代 Web/API 漏洞，Docker 一条命令 | 适合替代 DVWA/WebGoat |
| Web 备选 | [DVWA](https://github.com/digininja/DVWA) | 14,039★ · GPLv3 | 经典 PHP Web 漏洞 | 经典但偏旧 |
| Web 备选 | [WebGoat](https://github.com/WebGoat/WebGoat) | 9,487★ · Other | Java Web 教学靶场，Docker | 适合教学/证据链 |
| DECOY-01 | [Gitea](https://github.com/go-gitea/gitea) | 59,131★ · MIT | 内部 Git 服务，看起来高价值 | 最新稳定版、强密码、关闭注册 |
| DECOY-02 | [Uptime Kuma](https://github.com/louislam/uptime-kuma) | 94,529★ · MIT | 内部监控面板，真实感强 | 最新稳定版、强密码、无默认口令 |
| 统一 flag 面板 | [CTFd](https://github.com/CTFd/CTFd) | 6,914★ · Apache-2.0 | 面板提交 + 截图双通道 | `docker run -p 8080:8000 ctfd/ctfd` |

**P1 落地建议：**

- **TRAD-01** 用 Vulhub 选一个可 RCE 的 CVE，一台一台起、一台一台打，不要一次全起。
- **TRAD-02 + DC-01** 用 **GOAD MINILAB**，它正好是 1 个 DC + 1 个 Workstation；需要更丰富的 AD 攻击路径再上 GOAD-Light。
- **DECOY 不是另一个漏洞机**：Gitea/Uptime Kuma 要用最新稳定版、强随机密码、关闭注册、无默认管理员暴露；用 `decoy-detect` 验证“看起来可打、实际无分”。
- **CTFd 只做面板**：每台 AI 演练目标写 `ai_vector.txt`，传统演练目标写 `trad_vector.txt`，DC 写 `proof.txt`；同值注册到 CTFd，截图与面板值必须一致。AIGoat/DVMCP/K8s Goat 本身没有考试 flag 格式，这层必须补。

## 4. 推荐 10 主机等效拓扑

| 链 | 主机 | 分值 | 角色 |
|---|---|---:|---|
| A | TRAD-01 Vulhub Linux | 10 | 传统入口 |
| A | AI-01 AIGoat | 15 | RAG/embedding/agent/MCP |
| A | AI-02 DVMCP | 15 | MCP 工具面 |
| A | DC-01 GOAD DC | 5 | 两条链汇合，只计一次 |
| B | TRAD-02 GOAD Win10 | 10 | 传统/AD 入口 |
| B | AI-03 A2A samples + SecBench | 15 | AgentCard/ASRF/ATSI/CO/HOTF |
| B | AI-04 Kubernetes Goat | 15 | AI 基础设施/k8s/供应链 |
| B | DC-01 GOAD DC | — | 与链 A 同一台 |
| Standalone | AI-05 DVAR | 15 | Agentic RAG + 裸 Chroma |
| Decoy | DECOY-01 Gitea | 0 | 诱饵 |
| Decoy | DECOY-02 Uptime Kuma | 0 | 诱饵 |

**合计**：40 + 40 + 15 + 5 = **100**。**AI-only 及格线**：AI-01..AI-04（60）+ AI-05（15）= **75**。该拓扑满足“两条链、每链 3 台、1 个 DC、1 台独立 AI、2 台 decoy”的考试结构。

## 5. 资源与隔离

| 批次 | 主机 | 建议 RAM | vCPU | 磁盘 |
|---|---|---|---:|---:|
| P0 | AIGoat | 12GB | 4 | 30GB |
| P0 | DVMCP | 4GB | 2 | 10GB |
| P0 | A2A samples + SecBench | 4GB | 2 | 10GB |
| P0 | Kubernetes Goat | 8GB | 4 | 30GB |
| P0 | DVAR（含 Ollama） | 8GB | 4 | 30GB |
| P1 | Vulhub | 4GB | 2 | 20GB |
| P1 | GOAD MINILAB | 8–12GB | 4 | 80GB |
| P1 | Gitea + Uptime Kuma | 2GB | 2 | 20GB |
| P1 | CTFd | 1GB | 1 | 5GB |
| **合计** |  | **约 51–55GB** | **约 25** | **约 235GB** |

当前集群资源足够（189: 24C/64G，187: 16C/45G，183: 8C/17G），但：

- **不要把 Kubernetes Goat 或 GOAD 放到 189 控制面**。K8s Goat 需要 cluster-admin，能容器逃逸；GOAD 是 Windows 域环境，都不适合共享控制面。
- 建议用**独立 VLAN + 独立靶场宿主机/VM**；P0 可集中在 187 的独立 Docker/Kind 环境，但 K8s Goat 最好单独 Kind VM。
- 禁止靶场出公网；模型统一走本地 Ollama；AIGoat 和 DVAR 可共享一个 Ollama 服务，省 4.5GB 模型重复下载。
- 每台机器做快照/重置；flag 与面板分离，避免“打坏了无法复现”。

## 6. 落地顺序与验收

1. **P0 核心三台**：AIGoat（AI-01）+ DVMCP（AI-02）+ A2A（AI-03），加 CTFd；先跑通“侦察 → 攻击 → 证据 → 报告”闭环。
2. **补 AI-04/AI-05**：独立 Kind 集群上的 Kubernetes Goat；DVAR 先按 Bedrock 跑通，再决定是否改 Ollama。
3. **补 P1 五台**：Vulhub → GOAD MINILAB → Gitea/Uptime Kuma → CTFd flag 注入。
4. **接入现有技能**：`recon-ai` → `attack-rag`/`attack-embeddings`/`attack-mcp-tool`/`attack-multi-agent`/`attack-infra`/`foothold-traditional`/`decoy-detect` → `verify-evidence` → `report-exam`。
5. **最后做 `capstone-rehearse`**：按 24h 考试窗口跑一次完整 10 主机，验证两条链汇合 DC、flag 双通道、报告可 copy/paste 复现。

| 演练目标 | 验证入口 | 对应技能 |
|---|---|---|
| AIGoat | `http://<host>:3000`，登录 `alice/password123`；`:8000` API | `attack-rag`、`attack-ai-agent`、`attack-mcp-tool`、`attack-supply-chain` |
| DVMCP | MCP Inspector 连接 `http://<host>:9001/mcp`…`9015/mcp` | `attack-mcp-tool` |
| A2A | `a2a-inspector` 读取 AgentCard；A2ASecBench 离线 config | `attack-multi-agent` |
| Kubernetes Goat | `kubectl get pods`；`http://127.0.0.1:1234` | `attack-infra` |
| DVAR | `http://<host>:3000`；`curl http://<host>:8200/api/v1/collections` | `attack-rag`、`attack-embeddings` |
| Vulhub | `docker compose ps`；按 CVE README 访问端口 | `foothold-traditional` |
| GOAD | `vagrant status`；DC/Workstation 可达 | `foothold-traditional`、`loot-manage` |
| Gitea/Uptime Kuma | `curl -I http://<host>:<port>` | `decoy-detect` |
| CTFd | `http://<host>:8080` | `verify-evidence`、`report-exam` |

## 7. 诚实边界

1. **A2A 没有现成“故意可攻破”演练目标**：A2ASecBench 是 benchmark，不是演练目标；必须用官方 samples 做弱配置，约 1–2 小时工程量。
2. **D6 反演缺匹配演练目标**：DVAR 的 Chroma 可直读，但 Titan embedding 与 vec2text 预训练不匹配；需补 gtr-base 薄服务或训练适配器。
3. **DVAR 默认依赖 AWS Bedrock**：不改代码就不是零外部依赖；完全离线优先 AIGoat + Shaheer RAG 组合。
4. **DVMCP 无 LICENSE**：个人 lab 可用，团队/对外分发请换 Appsecco（MIT）。
5. **GOAD 是 Windows 评估版**：180 天后需重建或授权；放在隔离 VLAN，不接入生产域。
6. **Kubernetes Goat 是 cluster-admin 级演练目标**：只放独立 Kind/VM，不能放 189 控制面或共享业务集群。
7. **AIGoat/DVMCP/K8s Goat 没有考试 flag 格式**：必须加 CTFd + `ai_vector.txt`/`trad_vector.txt`/`proof.txt`，否则无法验证 flag 双通道。
