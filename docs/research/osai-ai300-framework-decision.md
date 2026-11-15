# OSAI AI-300 实现框架评估与适配决策

> **性质**：研究/决策文档（非规范正文）。基于用户提供的 `D:\下载\osai-ai300-skill-coverage-decision.md` 工具精选源，结合 OffSec OSAI AI-300 认证考试的实际场景与考试要求，评估并适配最适合的实现框架。结论不局限于 PyRIT。
> **核验日期**：2026-11-15（GMT+8）。考试事实以 S3 快照 `docs/governance/references/OSAI-Exam-Guide-snapshot.md`（一手源 `help.offsec.com`）为准；框架能力以各官方仓库/文档为准。

---

## 1. 决策前提（考试真实约束）

1. **考试形态**：24 小时监考、Tailscale VPN + 本地 Kali 接入 AI 赋能企业网；2 条攻击链（各 3 台链式主机）汇聚到域控（DC）+ 1 台独立 AI 主机 + 2 台故意不脆弱的诱饵机。
2. **计分结构**：8 台计分机 = 100 分，**75 分及格**；推导为链内 4×AI 向量机(15) + 2×传统向量机(10) + 独立 AI 机(15) + DC(5) = 100 → **AI 向量独占 75/100，是绝对主分面**。
3. **工具政策**：**完全开卷、无工具限制**，且 **AI 聊天机器人被 OSAI 明确允许并强烈建议**（与二手博客"禁用=零分"说法冲突，以一手源为准）。
4. **报告门槛极严**：每步命令/输出/脚本/截图 + 可 copy/paste 复现；文档缺失 = 扣分或零分——这是首要失分风险，独立于攻击成败。

---

## 2. 候选框架与角色定位

| 框架 | 版本 | 角色 | 关键能力 |
|---|---|---|---|
| **PyRIT** | 1.1.0 | 深度内核 | AI 向量多轮编排（Crescendo/PAIR/TAP）+ `SQLiteMemory` 证据留痕 |
| **garak** | 0.17.1 | 首扫层 | LLM/模型层快速漏洞扫描，**离线、无需 judge** |
| **promptfoo** | 0.125.1 | 固化层 | agent/MCP 声明式用例（**须自托管 provider、禁用联网插件**） |
| 专项点解 | — | 适配层 | A2ASecBench / mcp-scan / agentic-radar / AgentPoison / vec2text / ModelScan / IBM ART |
| Kali 工具链 | — | 落地层 | nmap/burp/impacket/云 CLI — 传统向量/横向/DC/云 |
| 许可 AI 助手 | — | 协作层 | payload 编写/排障/判读 co-pilot（OSAI 允许） |

---

## 3. 四维度对比

### 3.1 技能覆盖度
**无单框架覆盖全部 10 考纲场景。** PyRIT 强于 LLM/Agt/RAG/Emb/SC/Rep，但 **v1.1.0 无原生 MCP 攻击策略**，MA/Emb/SC/Infra/Cloud 及整个传统横向/DC 须靠专项点解 + Kali 工具链。garak 覆盖模型层探针但无利用深度；promptfoo 覆盖 agent/MCP 用例但依赖外部 provider。

### 3.2 考试实操需求
- **garak**：纯离线打分最契合考试内网；无需 judge、即扫即出结果。
- **promptfoo**：部分插件走托管服务（现属 OpenAI）→ **数据外发风险**，须自托管并禁用联网插件。
- **PyRIT**：重依赖、需手搓 target/attack/scorer，但 `SQLiteMemory` + 漂亮打印机直击报告证据门槛。
- **Kali**：传统向量/横向/DC 唯一可行路径，无替代。

### 3.3 框架灵活性
- **promptfoo**：声明式 YAML，改配置即适配，最快覆盖新用例。
- **PyRIT**：代码驱动最深、可编排最复杂多轮，但最费工。
- **自定义脚本 + Kali**：上限最高、零约束，但全靠手写。

### 3.4 考试实战效果
**garak 首扫定位 → PyRIT 深度多轮利用并留证 → promptfoo 固化 agent/MCP 用例；传统/DC/云纯靠 Kali；PyRIT 的 `SQLiteMemory`+证据导出正是"文档缺失即零分"的对症解药。**

---

## 4. 决策：不采用单一框架，采用 best-of-breed 分层栈 + 个人方法论统一层

PyRIT 保留为**规范内核**，但明确**降级为多层栈中的一层**，由其余工具补其盲区：

```
garak(首扫) → PyRIT(深度内核: 多轮编排+证据) + promptfoo(固化 agent/MCP)
                                  ↓
              专项点解(A2ASecBench/mcp-scan/vec2text/ModelScan/ART) + Kali(落地)
                                  ↓
                          许可 AI 助手(协作) + 五段式报告(收口)
```

---

## 5. 为什么"不是纯 PyRIT"

1. PyRIT v1.1.0 **无原生 MCP 策略**，而 MCP 是 15 分场景类；MA/Emb/SC/Infra/Cloud 与横向全部缺席。
2. 考试时间/文档压力下手搓 target/attack/scorer 不友好，garak 首扫 + promptfoo 声明式更快。
3. promptfoo 托管插件的数据外发是考试硬伤（须自托管 + 禁联网）。

## 6. 为什么仍保留 PyRIT 为内核

1. 多轮编排（Crescendo/PAIR/TAP）无可替代。
2. 本仓库已建成经一手源核实的 `pyrit==1.1.0` 集成，推倒浪费。
3. 其 `SQLiteMemory` 证据留痕正是"文档缺失即零分"的对症解药。
4. AI 向量是 75 分主分面，PyRIT 在此面深度最强。

---

## 7. 待核实风险

1. **promptfoo 托管插件**：联网生成/评分插件现属 OpenAI，考试内网存在数据外发与可用性风险；落地前须实测自托管 provider 并禁用联网插件，否则内网改用 garak+PyRIT+自定义。
2. **工具政策冲突**：二手博客称"禁用 AI=零分"，与一手源"AI 明确允许"冲突；以 `help.offsec.com` 为准，但考前建议再确认最新版本公告。
3. **版本漂移**：PyRIT/garak/promptfoo 版本持续演进，v1.1.0 / 0.17.1 / 0.125.1 为本次核验基准；后续须复测 API 兼容性。

---

## 8. 对本仓库技能的落地建议

- 沿用仓库既有 `pyrit==1.1.0` 集成（双模型命名空间 `OPENAI_CHAT_*`/`OPENAI_SCORER_*`）作为内核；MCP/MA 经 `HTTPTarget` 回调接入，复用既有双形态 seam。
- 每个 skill 的框架组合严格取自 `docs/research/osai-skill-framework-matrix.md` 对应条目；PyRIT 仅在其占优场景（LLM/Agt/RAG/Emb/SC/Rep）做主角。
- 偏离矩阵须在规格/门禁记录中显式说明理由（GOVERNANCE §8.3）。
- 详见 `docs/research/osai-skill-framework-matrix.md` 的逐技能明细与优先级总排序。
