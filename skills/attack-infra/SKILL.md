---
name: attack-infra
priority: P1
domain: D9
scoring_unit: AI向量机
trigger: recon-ai 已确认目标暴露 AI 基础设施面（云 AI 平台/模型服务器/容器/推理网关），且已取得可达 AI 向量机/独立机的内网立足点（foothold-traditional 之后）
input: recon-ai 资产清单（云 AI 平台、模型服务器、容器、推理网关端点）、已取得上下文与身份
output: 每攻击步骤「命令 + 输出 + 截图」证据、利用前后对照、下游模型服务器/推理被滥用取证、ai_vector.txt flag 取证（AI向量机 / 独立机）
---

# attack-infra — AI 基础设施与部署利用

攻击 AI 基础设施与部署，覆盖三大攻击面：**云 AI 平台与模型服务器配置错误/暴露**、**容器化负载与推理网关**、**凭据泄露/提权 → 代码执行**。技术分类对齐 OWASP Agentic ASI03（Identity and Privilege Abuse）→ ASI05（Unexpected Code Execution）与模型服务器过度暴露。主计分单元为 AI向量机（15 分）；取得内网立足点后向独立机延伸基础设施利用，形成第二个 15 分目标（校验器要求 `scoring_unit` 单值，故以 AI向量机为主，独立机于正文/trigger/输出显式声明为次要目标）。两者 flag 文件均为 `ai_vector.txt`。

## 执行体

按「发现基础设施面 → 云 AI 平台/模型服务器 → 容器化负载/推理网关 → 提权代码执行 → flag 取证」顺序推进，每步经 `tools/collect_evidence.py` 落盘证据，未过质量门不得进入下一步。

### 前置：发现 AI 基础设施面

1. 复用 `recon-ai` 资产清单，确认云 AI 平台（如 SageMaker / Vertex）、模型服务器（vLLM / Triton）、容器编排（K8s）、推理网关（如 LiteLLM / BentoML）与信任边界。
2. 记录正常部署基线（暴露端口、鉴权、服务账号），作为后续利用效果的对照。

### 攻击路径 A — 云 AI 平台与模型服务器

1. **infra-01 发现 AI 基础设施面**：枚举云 AI 平台、模型服务器、容器、推理网关端点与暴露面。
   - 命令：`curl -s <ML_PLATFORM>/api/v1/models` 或 `kubectl get svc -A | grep -iE 'vllm|triton|llm'`
   - 证据：`python tools/collect_evidence.py --step infra-01 --cmd "kubectl get svc -A" --out loot/infra-01-surface.md --shot-cmd "screenshot --region infra_surface" --target <ML_PLATFORM> --strict`
2. **infra-02 云 AI 平台配置错误**：利用公开 bucket / 误配 IAM / 开放 inference 端点（示意脚本，须记录来源）。
   - 命令：`aws s3 ls s3://<ml-artifacts> --no-sign-request`
   - 证据：`python tools/collect_evidence.py --step infra-02 --cmd "aws s3 ls s3://<ml-artifacts> --no-sign-request" --out loot/infra-02-misconfig.md --shot-cmd "screenshot --region misconfig" --target <ML_PLATFORM> --strict`
3. **infra-03 模型服务器暴露/滥用**：未授权访问或过度暴露的 vLLM / Triton，直接调用推理或模型下载（示意脚本，须记录来源）。
   - 命令：`curl -s <VLLM>/v1/completions -H "Content-Type: application/json" -d '{"model":"<m>","prompt":"<p>"}'`
   - 证据：`python tools/collect_evidence.py --step infra-03 --cmd "curl -s <VLLM>/v1/completions" --out loot/infra-03-model-server.md --shot-cmd "screenshot --region model_server" --target <VLLM> --strict`

### 攻击路径 B — 容器化负载与推理网关

4. **infra-04 容器化负载越权**：挂载/服务账号误配导致逃逸或横向到 AI 工作负载（示意脚本，须记录来源）。
   - 命令：`kubectl auth can-i --list --as=system:serviceaccount:<ns>:<sa>`
   - 证据：`python tools/collect_evidence.py --step infra-04 --cmd "kubectl auth can-i --list" --out loot/infra-04-container.md --shot-cmd "screenshot --region container" --target <K8S_API> --strict`
5. **infra-05 推理网关凭据泄露**：从网关/配置泄露高权限令牌后以合法身份调用推理（示意脚本，须记录来源）。
   - 命令：`grep -rE 'sk-|AKIA|Bearer ' <GATEWAY_CONFIG> 2>/dev/null`
   - 证据：`python tools/collect_evidence.py --step infra-05 --cmd "grep -rE 'sk-|AKIA|Bearer ' <GATEWAY_CONFIG>" --out loot/infra-05-gateway-cred.md --shot-cmd "screenshot --region gateway_cred" --target <GATEWAY> --strict`

### 攻击路径 C — 提权/下游取证与 flag

6. **infra-06 提权 → 意外代码执行**：利用容器/服务账号/模型服务器权限边界缺陷提权，使基础设施执行任意代码（对齐 ASI03 → ASI05，示意脚本，须记录来源）。
   - 命令：`curl -s <MODEL_SVC>/exec -H "Content-Type: application/json" -d '{"cmd":"id; whoami"}'`
   - 证据：`python tools/collect_evidence.py --step infra-06 --cmd "curl -s <MODEL_SVC>/exec -d '{\"cmd\":\"id; whoami\"}'" --out loot/infra-06-privesc.md --shot-cmd "screenshot --region privesc" --target <MODEL_SVC> --strict`
7. **infra-07 下游影响取证**：对比滥用前后模型服务器/推理行为，证明基础设施被滥用，含 AI 交互日志（§6.3）。
   - 命令：`curl -s <VLLM>/v1/completions -d '{"model":"<m>","prompt":"<probed>"}'`
   - 证据：`python tools/collect_evidence.py --step infra-07 --cmd "curl -s <VLLM>/v1/completions -d '<probe>'" --out loot/infra-07-impact.md --shot-cmd "screenshot --region impact" --ai-log "见 loot/infra-07-impact.md" --target <VLLM> --strict`
8. **infra-08 flag 取证（AI向量机 / 独立机）**：取得代码执行后定位并读取 `ai_vector.txt`；向独立机延伸基础设施利用重复上述流程，取得独立机 flag。
   - 命令：`whoami; id; find / -name ai_vector.txt 2>/dev/null -exec cat {} \;`
   - 证据：`python tools/collect_evidence.py --step infra-08 --cmd "whoami; id; find / -name ai_vector.txt 2>/dev/null -exec cat {} \;" --out loot/infra-08-flag.md --shot-cmd "screenshot --region flag_proof" --ai-log "见 loot/infra-08-flag.md" --flag "<ai_vector.txt 值>" --target <AI_VECTOR_HOST> --strict`
9. 取证须含访问证明：`whoami`/`id` + flag 内容同屏截图（对齐 §6.2 双通道一致）。

## 质量门

以下证据**必须**全部产出，缺失任一即判定未过门禁，不得进入下一技能：

- 每个攻击步骤的**确切命令**（可直接 copy/paste）。
- 每步骤的**关键输出**（含配置错误、模型服务器未授权访问、容器越权、凭据泄露、代码执行回显的响应原文）。
- 每步骤的**截图**（访问证明，含目标标识与时间戳）。
- **利用前后对照**证据（部署/权限 before/after）。
- **下游影响取证**（模型服务器/推理行为差异，含 AI 交互日志 §6.3）。
- `ai_vector.txt` flag 的「面板提交 + 截图」双通道一致。
- 上述每步证据统一通过共享工具 `tools/collect_evidence.py` 产出（对齐 §质量门），保证三件套/五件套结构稳定、与 `report-exam` 的 Attack Walkthrough 兼容、并可由 CI 校验。

## 校验标准

- 攻击过程可被技术读者 **copy/paste 逐步复现**（§6.1）。
- 证据结构与 `report-exam` 的 Attack Walkthrough 小节直接兼容，可**无损复用**，无需二次整理。
- 每步骤满足「命令 + 输出 + 截图」三件套；术语符合 `GLOSSARY.md`（用「AI向量机」「独立机」「模型服务器」等规范词，禁用 `_Avoid_` 废弃术语）。

## 失败与豁免

- 若目标无可用基础设施面，记录判定依据后改走 `attack-mcp-tool` / `attack-ai-agent`，不阻塞其余路径。
- 若配置错误仅部分生效（暴露但无写入/执行），如实记录可访问面，不得夸大。
- 若容器越权/凭据泄露被 RBAC/护栏拦截，记录拦截行为与原因，评估改走其它路径；不反复重试同一被拦截动作。
- 若目标为疑似诱饵机（0 分、无 AI 基础设施面），记录判定依据后 ≤30 分钟内结束，不在 0 分主机空耗。
