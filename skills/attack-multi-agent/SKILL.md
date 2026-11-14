---
name: attack-multi-agent
priority: P1
domain: D4
scoring_unit: AI向量机
trigger: recon-ai 已确认目标为多智能体/A2A 拓扑（消息总线/共享状态），且已取得可达 AI 向量机的内网立足点（foothold-traditional 之后）
input: recon-ai 资产清单（多 agent 拓扑、消息总线、共享状态端点）、已取得上下文与身份
output: 每攻击步骤「命令 + 输出 + 截图」证据、操纵前后对照、下游决策影响取证、ai_vector.txt flag 取证（AI向量机）
---

# attack-multi-agent — 多智能体/A2A 操纵

攻击多智能体（A2A）协同，覆盖三大攻击面：**消息操纵与智能体冒充**、**共享记忆/上下文投毒**、**工作流破坏与下游决策影响取证**。多智能体协同风险属 OWASP Agentic 2026 的编排层/消息信任类（消息信任缺失使协同链执行非预期动作）。它建立在 `attack-ai-agent`（单 agent 提示注入/记忆/工具）之上，扩展至多 agent 协同面。计分单元为 AI向量机（15 分）；取得内网立足点后亦向独立机延伸，形成第二个 15 分目标；两者 flag 文件均为 `ai_vector.txt`。

## 执行体

按「发现拓扑 → 消息操纵 → 智能体冒充 → 共享记忆投毒 → 上下文投毒 → 工作流破坏 → 下游取证 → flag 取证」顺序推进，每步经 `tools/collect_evidence.py` 落盘证据，未过质量门不得进入下一步。

### 前置：发现多 agent 拓扑

1. 复用 `recon-ai` 资产清单，确认 agent 数量、角色、消息总线（如 Kafka / RabbitMQ / 自定义）、共享状态/记忆后端（如 Redis / DuckDB）。
2. 记录正常协作基线（消息格式、信任假设、编排任务），作为后续操纵效果的对照。

### 攻击路径 A — 消息操纵与智能体冒充

1. **a2a-01 发现多 agent 拓扑/消息总线**：枚举 agent 拓扑与消息总线、共享状态端点。
   - 命令：`curl -s <BUS>/topics` 或 `redis-cli -h <MEMORY_HOST> keys '*agent*'`
   - 证据：`python tools/collect_evidence.py --step a2a-01 --cmd "curl -s <BUS>/topics" --out loot/a2a-01-topology.md --shot-cmd "screenshot --region topology" --target <BUS> --strict`
2. **a2a-02 消息操纵**：篡改/注入 agent 间消息，使协同链执行非预期动作（示意脚本，须记录来源）。
   - 命令：`python tools/msg_inject.py --bus <BUS> --from <agentA> --to <agentB> --payload "<forged msg>"`
   - 证据：`python tools/collect_evidence.py --step a2a-02 --cmd "python tools/msg_inject.py --bus <BUS>" --out loot/a2a-02-msg-manip.md --shot-cmd "screenshot --region msg_manip" --target <BUS> --strict`
3. **a2a-03 智能体冒充**：伪造某 agent 身份注入指令或结果（示意脚本，须记录来源）。
   - 命令：`python tools/agent_impersonate.py --bus <BUS> --spoof <agentA> --cmd "<malicious instruction>"`
   - 证据：`python tools/collect_evidence.py --step a2a-03 --cmd "python tools/agent_impersonate.py --bus <BUS>" --out loot/a2a-03-impersonate.md --shot-cmd "screenshot --region impersonate" --target <BUS> --strict`

### 攻击路径 B — 共享记忆/上下文投毒

4. **a2a-04 共享记忆投毒**：写入伪造记忆，跨会话影响后续 agent 决策（示意脚本，须记录来源）。
   - 命令：`python tools/memory_poison.py --store <MEMORY> --key conv:agentB --value "<forged memory>"`
   - 证据：`python tools/collect_evidence.py --step a2a-04 --cmd "python tools/memory_poison.py --store <MEMORY>" --out loot/a2a-04-memory-poison.md --shot-cmd "screenshot --region memory_poison" --target <MEMORY> --strict`
5. **a2a-05 上下文投毒**：污染共享上下文/全局 prompt，使多 agent 协同偏离既定任务（示意脚本，须记录来源）。
   - 命令：`python tools/context_poison.py --endpoint <ORCH> --inject "<malicious context>"`
   - 证据：`python tools/collect_evidence.py --step a2a-05 --cmd "python tools/context_poison.py --endpoint <ORCH>" --out loot/a2a-05-context-poison.md --shot-cmd "screenshot --region context_poison" --target <ORCH> --strict`

### 攻击路径 C — 工作流破坏与下游取证

6. **a2a-06 工作流破坏**：偏离既定编排任务或触发误动作（示意脚本，须记录来源）。
   - 命令：`python tools/workflow_disrupt.py --orchestrator <ORCH> --task "<spoofed task>"`
   - 证据：`python tools/collect_evidence.py --step a2a-06 --cmd "python tools/workflow_disrupt.py --orchestrator <ORCH>" --out loot/a2a-06-workflow.md --shot-cmd "screenshot --region workflow" --target <ORCH> --strict`
7. **a2a-07 下游决策影响取证**：对比操纵前后协同结果，证明下游决策被影响，含 AI 交互日志（§6.3）。
   - 命令：`curl -s <ORCH>/trace -H "Content-Type: application/json" -d '{"run":"<id>"}'`
   - 证据：`python tools/collect_evidence.py --step a2a-07 --cmd "curl -s <ORCH>/trace -d '<run id>'" --out loot/a2a-07-impact.md --shot-cmd "screenshot --region impact" --ai-log "见 loot/a2a-07-impact.md" --target <ORCH> --strict`

### 收尾：flag 取证

1. **a2a-08 flag 取证（AI向量机）**：取得协同面代码执行/数据访问后定位并读取 `ai_vector.txt`；向独立机延伸 A2A 操纵重复上述流程。
   - 命令：`whoami; id; find / -name ai_vector.txt 2>/dev/null -exec cat {} \;`
   - 证据：`python tools/collect_evidence.py --step a2a-08 --cmd "whoami; id; find / -name ai_vector.txt 2>/dev/null -exec cat {} \;" --out loot/a2a-08-flag.md --shot-cmd "screenshot --region flag_proof" --ai-log "见 loot/a2a-08-flag.md" --flag "<ai_vector.txt 值>" --target <AI_VECTOR_HOST> --strict`
2. 取证须含访问证明：`whoami`/`id` + flag 内容同屏截图（对齐 §6.2 双通道一致）。

## 质量门

以下证据**必须**全部产出，缺失任一即判定未过门禁，不得进入下一技能：

- 每个攻击步骤的**确切命令**（可直接 copy/paste）。
- 每步骤的**关键输出**（含消息被注入、冒充生效、记忆/上下文被篡改、工作流偏离的响应原文）。
- 每步骤的**截图**（访问证明，含目标标识与时间戳）。
- **操纵前后对照**证据（协作结果/记忆 before/after）。
- **下游决策影响取证**（协同结果差异，含 AI 交互日志 §6.3）。
- `ai_vector.txt` flag 的「面板提交 + 截图」双通道一致。
- 上述每步证据统一通过共享工具 `tools/collect_evidence.py` 产出（对齐 §质量门），保证三件套/五件套结构稳定、与 `report-exam` 的 Attack Walkthrough 兼容、并可由 CI 校验。

## 校验标准

- 攻击过程可被技术读者 **copy/paste 逐步复现**（§6.1）。
- 证据结构与 `report-exam` 的 Attack Walkthrough 小节直接兼容，可**无损复用**，无需二次整理。
- 每步骤满足「命令 + 输出 + 截图」三件套；术语符合 `GLOSSARY.md`（用「AI向量机」「多智能体」「A2A」等规范词，禁用 `_Avoid_` 废弃术语）。

## 失败与豁免

- 若目标为单 agent 无协同面，记录判定依据后改走 `attack-ai-agent`，不阻塞其余路径。
- 若消息操纵仅部分生效（消息注入但 agent 未采纳），如实记录效果等级，不得夸大。
- 若冒充/投毒被消息签名或护栏拦截，记录拦截行为与原因，评估改走其它路径；不反复重试同一被拦截动作。
- 若目标为疑似诱饵机（0 分、无多 agent 面），记录判定依据后 ≤30 分钟内结束，不在 0 分主机空耗。
