# attack-infra 实现事实索引

> **版本** v1.0 · **状态** 已核实 · **性质** attack-infra 单一可信源
> **取证日期** 2026-11-15（GMT+8）· **取证方式** 官方文档抓取 + 演练目标一手探针（命令与输出逐条留痕）
> **上游** [`skills/attack-infra/SKILL.md`](../../skills/attack-infra/SKILL.md) · **治理** `GOVERNANCE.md` §4.2 / §6 · **流程** `docs/operations/skill-mainline-workflow.md` §3.1
> **职责边界** 本文件只记录「实现所依赖的事实」；不定义流程、不复制宪法条款、不重复 `GLOSSARY.md` 与 PyRIT 索引正文（C1）。

---

## 0. 结论摘要

1. **演练目标存在真实 AI 基础设施面**，此前未记录：`11434` Ollama 0.40.15（**未授权**，已实证推理）、`6443` kube-apiserver（匿名可读 `/version`）、`10250` kubelet HTTPS（匿名 `401`）。因此本技能**不走**「无基础设施面」豁免分支（F-9..F-12）。
2. **未授权模型服务器已取得可复现证据**：`POST /api/generate` 返回模型输出，`GET /v1/models` 返回 OpenAI 兼容 `{"object":"list"}`（F-9、F-10）。这是 `infra-03` 的直接判据。
3. **判定不得以 HTTP 200 为据**：80 端口任意路径均返回 `200 text/html 1702`（SPA 回退）；`11434/health` 反例返回 `404`。判据必须为「状态码 + `Content-Type` + JSON 结构」三元组（P-1）。
4. **本机存在 HTTP 代理陷阱**：环境变量 `HTTP_PROXY/HTTPS_PROXY=127.0.0.1:65383`，不加 `--noproxy '*'` 时 `:8000`/`:10250` 返回代理自身的 `502`/`400`，属**假信号**（P-2）。
5. **K8s 面鉴权状态已判定**：`6443` 匿名 `GET /` → `403 forbidden: User "system:anonymous"`，`GET /version` → `200`；`10250` `/healthz` `/pods` `/metrics` → `401 Unauthorized`。即基础设施面存在但需凭据，`infra-04` 依赖凭据获取而非匿名利用（F-11、F-12）。
6. **本技能不引入 PyRIT 对象图**：攻击面为基础设施与部署配置，无对抗性模型攻击对象；下游影响取证直接走原生 HTTP。B7 仅需保证禁用名不出现（§3）。

---

## 1. 已核实清单（一手源逐条）

| # | 事实 | 来源（URL / 命令） | 输出摘要 |
|---|---|---|---|
| F-1 | OWASP Agentic Top 10（2026）中 `ASI03` = **Identity & Privilege Abuse**、`ASI05` = **Unexpected Code Execution** | <https://genai-security-project.github.io/crosswalk/agentic-ai-top10> | 原文：「ASI03 Identity & Privilege Abuse」「ASI05 Unexpected Code Execution」 |
| F-2 | vLLM OpenAI 兼容面：`/v1/completions`、`/v1/chat/completions`、`/v1/models`、`/v1/embeddings`；工具面 `/health`、`/version`、`/metrics`、`/load` | <https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html> | 逐条路径原文命中 |
| F-3 | `vllm serve --port` 默认 **8000** | <https://docs.vllm.ai/en/latest/cli/serve.html> | `--port` … `Default: 8000` |
| F-4 | Triton HTTP/REST v2：健康 `v2/health/ready`、仓库 `POST v2/repository/index`、加载/卸载 `POST v2/repository/models/${MODEL_NAME}/load|unload`；文档示例主机端口 `localhost:8000` | <https://docs.nvidia.com/deeplearning/triton-inference-server/user-guide/docs/protocol/extension_model_repository.html> | 端点与示例逐条命中 |
| F-5 | LiteLLM 代理（推理网关）默认 **4000**，端点 `POST /chat/completions`、`POST /completions`、`GET /models`、`POST /key/generate`；`config.yaml` 的 `model_list[].litellm_params.api_key` 存放上游模型密钥 | <https://docs.litellm.ai/docs/proxy/quick_start> | `Proxy running on http://0.0.0.0:4000`；`api_key: <your-azure-api-key>` |
| F-6 | 枚举某身份全部权限：`kubectl auth can-i --list --namespace=foo`；服务账号冒充：`kubectl auth can-i list pods --as=system:serviceaccount:dev:foo -n prod` | <https://kubernetes.io/docs/reference/kubectl/generated/kubectl_auth/kubectl_auth_can-i/> | 示例命令原文命中；`--list` = "prints all allowed actions" |
| F-7 | `list` 动词对 `secrets` 可读出 `data` 字段（授权面等价于 `get`）→ 越权列举即凭据泄露 | <https://kubernetes.io/docs/reference/access-authn-authz/authorization/> | 原文："**list** on `secrets` will reveal the **data** attributes" |
| F-8 | kubelet HTTPS 端点：未通过认证的请求按匿名处理，用户名 `system:anonymous`、组 `system:unauthenticated`；`--anonymous-auth=false` 关闭；默认授权模式 `AlwaysAllow`；`nodes/proxy` 的 `get` 可执行任意容器命令 | <https://kubernetes.io/docs/reference/access-authn-authz/kubelet-authn-authz/> | 逐条原文命中（含 `nodes/proxy` 警告段） |
| F-9 | 演练目标 `11434` 为 Ollama **0.40.15**，未授权可读 `/api/version`、`/api/tags`、`/api/ps`；`POST /api/generate` 未授权返回模型输出（实测返回 `PWNED`） | `curl --noproxy '*' http://192.168.40.189:11434/api/version`；`…/api/generate -d '{"model":"llama3.2:latest","prompt":"Reply with exactly: PWNED","stream":false}'` | `{"version":"0.40.15"}`；`{"response":"PWNED","done":true,…}` |
| F-10 | Ollama 暴露 OpenAI 兼容面：`GET /v1/models` → `200 application/json`，体为 `{"object":"list","data":[{"id":"llama3.2:latest","object":"model",…}]}`；`/v1/completions` 与 `/health` 在该实例分别不可用/`404` | `curl --noproxy '*' -o /dev/null -w "%{http_code} %{content_type}" http://192.168.40.189:11434/v1/models` | `200 application/json`；`/health` → `404` |
| F-11 | 演练目标 `6443` 为 Kubernetes API 服务：匿名 `GET /` → `403`，`message: forbidden: User "system:anonymous" cannot get path "/"`；`GET /version` → `200` | `curl -k --noproxy '*' https://192.168.40.189:6443/`；`…/version` | 上述 `Status` JSON；`/version` 退出码 200 |
| F-12 | 演练目标 `10250` 为 HTTPS 端点（kubelet 风格）：`/` 与 `/version` → `404 page not found`；`/healthz`、`/pods`、`/metrics`、`/configz` → `401 Unauthorized` | `curl -k --noproxy '*' https://192.168.40.189:10250/{healthz,pods,metrics,configz}` | `401` + `Unauthorized`（12 字节） |
| F-13 | 80 端口为 SPA 回退：`/v1/models`、`/health`、`/v1/completions`、`/v2/health/ready`、`/v2/models`、`/metrics`、`/docs` 全部 `200 text/html 1702` | `curl -s -o /dev/null -w "%{http_code} %{content_type} %{size_download}" http://192.168.40.189/<path>` | 七条路径输出完全一致 |
| F-14 | 本机代理污染：`HTTP_PROXY=http://127.0.0.1:65383`；不加 `--noproxy '*'` 时 `:8000`/`:4000` 返回 `502`（体为本地 Windows `os error 10061`）、`:10250` 返回 `400 Client sent an HTTP request to an HTTPS server`（代理产生） | `env | grep -i proxy`；对比加/不加 `--noproxy` 的同 URL 结果 | 加 `--noproxy '*'` 后 `:8000`/`:4000` 为 `000`（连接拒绝），`:10250` 为真实 `404/401` |
| F-15 | 其余常见 AI 基础设施端口未开放：`3000`、`5000`、`9000`、`8501`、`2375`、`2376`、`10255` 均 `000`；`8081` 为 Go 风格 `404 page not found`（服务存在，身份待核） | 端口探测循环（http/https 各一次） | 仅 `8081` 返回 `404`，其余无响应 |
| F-16 | 每步证据基线与 flag 双通道要求 | `GOVERNANCE.md` §6.1 / §6.2（正文不转抄，C1）；`docs/governance/references/OSAI-Exam-Guide-snapshot.md` §1/§4 | 仅记录「要求存在于何处」，不复述条款 |
| F-17 | 证据落盘唯一入口 `tools/collect_evidence.py`，参数含 `--step/--cmd/--output*/--screenshot/--shot-cmd/--ai-log/--flag*/--target/--strict` | `python tools/collect_evidence.py --help` | 参数表原文命中 |
| F-18 | 本技能计分单元与次要目标 | `GLOSSARY.md`（AI向量机 / 独立机）；`skills/attack-infra/SKILL.md` front-matter | `scoring_unit` 单值；语义见术语表条目，不复述 |

---

## 2. 攻击路径 ↔ 实现映射

| 步骤 | 判据来源 | 成功判据（布尔） | 失败分支 |
|---|---|---|---|
| infra-01 发现基础设施面 | F-2..F-5、F-9..F-15 | 至少 1 个端点满足 P-1 三元组判据，并归类为 vLLM/Triton/LiteLLM/Ollama/K8s/kubelet | 全部仅命中 SPA 回退 → 记录「无基础设施面」并转 `attack-mcp-tool` / `attack-ai-agent` |
| infra-02 云平台配置错误 | F-8（AWS CLI） | `aws s3 ls --no-sign-request` 返回对象清单（非 `AccessDenied`） | 凭据缺失或被拒 → 记录原始错误体，不臆测 |
| infra-03 模型服务器暴露 | F-2..F-5、F-10 | 未授权 `/v1/models`（或 `/api/tags`、`/v2/health/ready`）返回合法清单；进一步未授权推理返回模型输出 | 401/403 → 降级为「面存在但需凭据」，交由 infra-05 |
| infra-04 容器化负载越权 | F-6、F-8 | `kubectl auth can-i --list` 返回 `*` 或 `secrets.list`/`pods.exec` 等高权项 | `403`/无 kubeconfig → 记录匿名不可达（当前 F-11/F-12 即此态） |
| infra-05 推理网关凭据泄露 | F-5、F-7 | 在网关配置/环境/Secret 中命中 `sk-`/`AKIA`/`Bearer` 且可用该值成功调用推理 | 命中但无调用权限 → 记录「凭据存在但未授权」，按 §6 只记指纹不落明文 |
| infra-06 提权 → 代码执行 | F-8（`nodes/proxy`）、F-4（模型加载） | `id`/`whoami` 回显与目标主机一致（非本地） | 被 RBAC/护栏拦截 → 记录拦截原文与原因，不重试同一动作 |
| infra-07 下游影响取证 | F-10、F-17 | 滥用前后同一请求的响应差异 + AI 交互日志同屏可复现 | 模型不可用 → 记录调用错误体，判定为「部分生效」 |
| infra-08 flag 取证 | F-16、F-18 | `whoami`/`id` 与 `ai_vector.txt` 内容同屏；面板值 == 截图值 | 目标无 `ai_vector.txt` → 走面板预言机等价通道（`GLOSSARY.md` flag 条目） |

---

## 3. 判据前提与陷阱

- **P-1 三元组判据**：「状态码 2xx」不构成存在性证明。须同时满足 `Content-Type` 含 `json` **且** 体可解析 **且** 命中该服务的结构键（vLLM/Triton/LiteLLM/Ollama：`object|data|models|ready`）。依据：F-13 与 F-10 互为反例（同 200，不同真值）。
- **P-2 代理规避**：所有探测必须显式绕开环境代理（urllib 侧等价于 `ProxyHandler({})`），否则 F-14 的 `502/400` 会被误判为目标行为。
- **P-3 端口不唯一**：vLLM/Triton 默认 8000（F-3、F-4）、LiteLLM 默认 4000（F-5）、Ollama 默认 11434（F-9）。默认端口仅为候选，实际端点以 infra-01 探测结果为准。
- **P-4 只读优先**：`infra-02`..`infra-05` 默认执行只读/可逆动作（列举、读取、单次推理）；写操作（模型 pull/delete、`repository/unload`、`update_weights`）须显式开关并留痕，避免改变目标状态。

---

## 4. 待核实（R）

| # | 事项 | 取证方式 |
|---|---|---|
| R-1 | OWASP Agentic Top 10 官方 PDF 直达 URL（当前为项目镜像页 F-1） | 抓取 `genai.owasp.org` 项目页并复核 `ASI03/ASI05` 标题 |
| R-2 | `8081` 服务身份（Go 风格 `404`，F-15） | 对 `/metrics`、`/healthz`、`/api/v1/...` 做三元组探针；仍不明确则记为「未知 HTTP 服务」 |
| R-3 | K8s 集群版本与 RBAC 授权面 | 需凭据：`kubectl version --short`、`kubectl auth can-i --list`（当前匿名 `403`，F-11） |
| R-4 | Ollama 写能力（`/api/pull`、`/api/delete`、`/api/create`）是否存在鉴权 | 仅在演练允许时以最小影响方式验证；本阶段不执行（P-4） |
| R-5 | `ai_vector.txt` 在演练目标上的实际路径 | 需代码执行后 `find / -name ai_vector.txt`；未取得立足点前不可核实 |

---

## 5. 已排除（D）

- **D-1** `pyrit.orchestrator` / `*Orchestrator` / `AzureOpenAIChatTarget`：B7 禁用名，任何实现中出现即不符合项（`pyrit==1.1.0` 事实见 `docs/research/pyrit-canonical-references.md`）。
- **D-2** 以 HTTP 200 判定资产存在（P-1 反例 F-13）。
- **D-3** 明文凭据落盘：`SKILL.md` 质量门与 `GOVERNANCE.md` §6 禁止；只记指纹（前缀 + 长度 + 命中位置）。
- **D-4** BentoML 端点作为判据：官方文档页未给出默认端口与端点清单，无法构成一手事实，不纳入实现判据（若后续需要再立 R 项）。

---

## 6. 门禁记录（阶段 1）

| 编号 | 检查项 | 依据 | 实测（命令 + 摘要） | 判定 | 结论 |
|---|---|---|---|---|---|
| B7 | PyRIT 版本与对象图 | §2.1 | `grep -rn "pyrit\.\|Orchestrator\|AzureOpenAIChatTarget" docs/research/attack-infra-canonical.md` → 仅 D-1 出现禁用名作为排除项；本技能不引入 PyRIT 对象 | 符合 | PASS |
| B8 | 可追溯性 | §2.1 | F-1..F-18 每条带 URL 或可复跑命令；R-1..R-5 均带取证方式 | 符合 | PASS |
| AC-1 | 每条结论可定位一手源 | §3.1 验收① | 「来源」列无空值 | 符合 | PASS |
| AC-2 | 版本号明确 | 验收② | vLLM `--port` 默认 8000；LiteLLM 4000；Ollama `0.40.15`；kube-apiserver/kubelet 版本待 R-3 | 符合 | PASS |
| AC-3 | 每条攻击路径有对应映射 | 验收③ | §2 表覆盖 infra-01..08（8/8） | 符合 | PASS |
| AC-4 | 待核实项命名 + 取证方式 | 验收④ | R-1..R-5 | 符合 | PASS |
| AC-5 | 落盘 `docs/research/` | 验收⑤ | 本文件 | 符合 | PASS |

**阶段结论**：`PASS`（不符合项 0）。复验命令：`python scripts/check_glossary.py && python scripts/validate_skill.py && python -m unittest discover -s tests`。
