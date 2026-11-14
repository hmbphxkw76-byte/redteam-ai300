# 技能线提示词 backlog（/to-spec 就绪）

> 依据 GOVERNANCE.md §4.4 生成。下列曾为**尚未落地**的技能线提示词，按优先级 **P0 → P1 → P2** 排序，
> 每份均为自包含规格，可直接作为 `/to-spec` 的输入（单开一条消息发送即可）。
>
> **状态（2026-11-14 更新）：backlog 全部实例化完成**——13 项待办技能均已走通 `to-spec → to-tickets → implement-spec`，SKILL.md 合并 main 且 CI（S1+S2）全绿。GOVERNANCE §4.4 登记的 16 个技能现已全部落地。
>
> **已落地、不在下表**：`recon-ai`（#22）、`attack-ai-agent`、`attack-rag`（#16）、`attack-mcp-tool`（#28）、`foothold-traditional`（#35）、`loot-manage`（#42）、`report-exam`（#47）、`verify-evidence`（#55）、`attack-embeddings`（#62）、`attack-multi-agent`（#69）、`attack-supply-chain`（#76）、`attack-infra`（#84）、`threat-model`（#89）、`decoy-detect`（#94）、`capstone-rehearse`（#99）、`tooling-automate`（#104）。
>
> **共享工具已完成**：`tools/collect_evidence.py`（P0 / 计分单元：通用）已存在并满足 §质量门
> 五件套（确切命令 / 关键输出 / 截图 / AI 交互日志 / flag 双通道一致），CI 门禁
> `py_compile` + `tests/test_collect_evidence.py` 已就绪，无需重建。

---

## P0

### 1. attack-mcp-tool — MCP 与工具面滥用（D7 / AI向量机 / 独立机）

- **职责**：攻击 MCP（Model Context Protocol）服务与工具面：恶意 MCP server 投毒、工具描述/权限篡改、过度授权工具链滥用、工具调用劫持，以在 AI 向量机 / 独立机取得代码执行或凭据泄露。
- **输入（触发条件/前置）**：`recon-ai` 资产清单已确认目标暴露 MCP 端点 / 工具清单 / server 来源；已取得可达 AI 向量机的内网立足点（`foothold-traditional` 之后）。
- **输出**：每攻击步骤「命令 + 输出 + 截图」证据、工具投毒前后对照、下游 agent/工具被操纵取证、`ai_vector.txt` / 独立机 flag 取证。
- **优先级**：P0
- **计分单元**：AI向量机 / 独立机（15 分 / 15 分）
- **验收标准**：① SKILL.md 含 §4.2 五要素；② 覆盖三类攻击面（恶意 server 投毒 / 工具滥用 / 权限提升）；③ `python scripts/validate_skill.py` + `python scripts/check_glossary.py` 全绿；④ 证据片段与 `report-exam` 的 Attack Walkthrough 直接兼容（§8.1(d) 端到端演示）。
- **CI 门禁**：S1 `validate_skill` + `check_glossary` + `py_compile`；TBD S2 证据契约夹具断言每步 `collect_evidence.py`（参照 recon-ai #25）。
- **Out of scope**：不含实际漏洞利用载荷（留 SKILL.md 与各攻击脚本）；不含截图捕获实现（仅接收路径或钩子）。

### 2. foothold-traditional — 传统入口/横向/提权（D1 + 传统技术 / 传统向量机 / 链式入口）

- **职责**：获取传统攻击链入口（公网入口利用）、内网横向、本地提权，覆盖 2 条攻击链 × 3 台链式主机（含 2 台传统向量机 10 分/台），为 AI 向量机 / 独立机提供可达性。
- **输入（触发条件/前置）**：`recon-ai` 传统面枚举结果、外部入口、初始访问向量。
- **输出**：每台主机「命令 + 输出 + 截图（`trad_vector.txt`）」证据、横向路径图、提权前后权限证明。
- **优先级**：P0
- **计分单元**：传统向量机（10 分/台）/ 链式入口
- **验收标准**：① 五要素齐全；② 覆盖 入口 → 横向 → 提权 三阶段；③ 每主机小节满足 §7.2（枚举/漏洞/利用/提权/flag）；④ 术语合规（`诱饵机` 等）。
- **CI 门禁**：S1 `validate_skill` + `check_glossary` + `py_compile`。
- **Out of scope**：AI 特定利用（属 `attack-ai-*` 系列）；截图捕获实现。

### 3. loot-manage — 战利品与凭证管理（跨域 D1/D10 / 通用）

- **职责**：即时登记与沉淀所有战利品（凭证、会话、flag、攻击路径），结构化存储供报告无损回溯；禁止散落于对话上下文（§5.2）。
- **输入（触发条件/前置）**：各攻击技能产出的凭证 / flag / 路径；`recon-ai` 资产清单。
- **输出**：结构化战利品清单（markdown / 表格）、与 `verify-evidence` / `report-exam` 可衔接的索引。
- **优先级**：P0
- **计分单元**：通用（效率）
- **验收标准**：① 五要素齐全；② 清单可被 `report-exam` 复用、满足可复现性基线 §6.1；③ 含 flag 双通道占位（面板值 + 截图路径）；④ 术语合规。
- **CI 门禁**：S1 `validate_skill` + `check_glossary`。
- **Out of scope**：不自动窃取（只登记已得战利品）；不含截图捕获。

### 4. report-exam — 考试报告生成（报告要求 S1 / 通用）

- **职责**：生成符合 S1 官方模板的考试报告 PDF：Introduction/Objective/Requirements、Executive Summary（含 High-Level Attack Path）、Attack Walkthrough（Chain1 / Chain2 各 3 台主机 + 域控 + 独立主机）、Appendix（长 PoC / 补充截图 / AI 会话历史）。
- **输入（触发条件/前置）**：各技能 `collect_evidence.py` 证据片段、`loot-manage` 清单、`verify-evidence` 校验结果。
- **输出**：`OSAI-OS-XXXXX-Exam-Report.pdf` + 归档 `OSAI-OS-XXXXX-Exam-Report.7z`（≤100MB、无密码），满足 §6.4 命名与结构。
- **优先级**：P0
- **计分单元**：通用（及格前提）
- **验收标准**：① 五要素齐全；② 报告结构满足 §7.1；③ 每主机小节满足 §7.2（枚举/漏洞/完整利用/提权/flag 取证可 copy/paste 复现）；④ AI 交互已入附录（§6.3）；⑤ 与 `verify-evidence` 衔接、提交前经全量校验（§7.3）。
- **CI 门禁**：S1 `validate_skill` + `check_glossary`；可加脚本校验 `.7z` 命名 / ≤100MB / 无密码。
- **Out of scope**：不含实际利用（只聚合既有证据）；不含截图捕获（只引用既有截图）。

### 5. verify-evidence — 证据校验与 flag 提交（报告要求 S1/S3 / 通用）

- **职责**：提交前全量校验——flag 双通道一致（控制面板提交值 == 报告截图/正文）、每步三件套齐全、目标路径覆盖（`trad_vector.txt`/`ai_vector.txt`/`proof.txt`）、术语合规；任一不符即阻断提交（§8.2）。
- **输入（触发条件/前置）**：`report-exam` 产出、`loot-manage` 清单、各 step 证据片段。
- **输出**：校验报告（通过/阻断 + 缺失项清单）、可机读校验结果（供 CI 复用）。
- **优先级**：P0
- **计分单元**：通用（防失分）
- **验收标准**：① 五要素齐全；② 覆盖 §8.2 八项检查单；③ 双通道一致判定；④ 域控 `proof.txt` 仅可提交一次（§2.2）。
- **CI 门禁**：S1 `validate_skill` + `check_glossary`；可加 S2 校验脚本断言所有证据片段三件套齐全 + flag 双通道一致。
- **Out of scope**：不生成报告（属 `report-exam`）；不含截图捕获。

---

## P1

### 6. attack-embeddings — Embedding 反演与信息提取（D6 / AI向量机）

- **职责**：针对 embedding 模型的反演与信息提取：从 embedding 近似还原训练/检索语料、成员推断、对抗样本、提取知识库内容。
- **输入（触发条件/前置）**：`recon-ai` 发现的 embedding 模型/接口、可查询 embedding 端点。
- **输出**：每攻击步骤证据、反演/提取结果、下游对 RAG/检索影响取证。
- **优先级**：P1
- **计分单元**：AI向量机（15 分）
- **验收标准**：① 五要素齐全；② 与 `attack-rag` 衔接（共享向量库/embedding 面）；③ `validate_skill` + `check_glossary` 全绿；④ 与 `report-exam` 兼容。
- **CI 门禁**：S1 `validate_skill` + `check_glossary` + `py_compile`。
- **Out of scope**：不含具体反演实现（留 SKILL.md）；不含截图捕获。

### 7. attack-multi-agent — 多智能体/A2A 操纵（D4 / AI向量机）

- **职责**：多智能体 / A2A 攻击：消息操纵、智能体冒充、共享记忆/上下文投毒、工作流破坏，使协同 agent 链执行非预期动作。
- **输入（触发条件/前置）**：`recon-ai` 发现的多 agent 拓扑、消息总线 / 共享状态。
- **输出**：每攻击步骤证据、操纵前后对照、下游决策影响取证。
- **优先级**：P1
- **计分单元**：AI向量机（15 分）
- **验收标准**：① 五要素齐全；② 与 `attack-ai-agent` 衔接（单 agent → 多 agent）；③ `validate_skill` + `check_glossary` 全绿；④ 与 `report-exam` 兼容。
- **CI 门禁**：S1 `validate_skill` + `check_glossary` + `py_compile`。
- **Out of scope**：不含具体 exploit；不含截图捕获。

### 8. attack-supply-chain — AI 供应链投毒（D8 / AI向量机）

- **职责**：AI 供应链投毒：数据集、模型权重、适配器（LoRA）、依赖/包投毒，污染训练或推理产物，间接影响 AI 向量机。
- **输入（触发条件/前置）**：`recon-ai` 发现的供应链面（模型仓库、依赖源、数据管道）。
- **输出**：每攻击步骤证据、投毒前后对照、下游模型行为影响取证。
- **优先级**：P1
- **计分单元**：AI向量机（15 分）
- **验收标准**：① 五要素齐全；② 与 `attack-rag` / `attack-embeddings` 衔接；③ `validate_skill` + `check_glossary` 全绿；④ 与 `report-exam` 兼容。
- **CI 门禁**：S1 `validate_skill` + `check_glossary` + `py_compile`。
- **Out of scope**：不含实际投毒载荷；不含截图捕获。

### 9. attack-infra — AI 基础设施与部署利用（D9 / AI向量机 / 独立机）

- **职责**：AI 基础设施与部署利用：云 AI 平台、模型服务器（vLLM / Triton）、容器化负载、推理网关的错配 / 凭据泄露 / 提权。
- **输入（触发条件/前置）**：`recon-ai` 发现的 AI 基础设施面。
- **输出**：每攻击步骤证据、利用前后对照、flag 取证（`ai_vector.txt` / 独立机）。
- **优先级**：P1
- **计分单元**：AI向量机 / 独立机（15 分 / 15 分）
- **验收标准**：① 五要素齐全；② `validate_skill` + `check_glossary` 全绿；③ 与 `report-exam` 兼容。
- **CI 门禁**：S1 `validate_skill` + `check_glossary` + `py_compile`。
- **Out of scope**：不含具体利用载荷；不含截图捕获。

### 10. threat-model — AI 目标威胁建模（D10 / 通用）

- **职责**：考前 24h 高价值目标定位与最短攻击路径规划；识别 2 台诱饵机（0 分）避免空耗；输出优先级攻击图，驱动编排顺序（§4.5）。
- **输入（触发条件/前置）**：`recon-ai` 资产清单、计分模型（§2.2 / §2.3，AI 向量为最高杠杆）。
- **输出**：威胁模型文档（高价值资产 / 信任边界 / 攻击路径 / 诱饵判定），驱动编排顺序。
- **优先级**：P1
- **计分单元**：通用（前置）
- **验收标准**：① 五要素齐全；② 含诱饵机识别时间盒（≤30min，§5.3）；③ 与 `decoy-detect` 衔接；④ 术语合规。
- **CI 门禁**：S1 `validate_skill` + `check_glossary`。
- **Out of scope**：不含实际攻击；不含截图捕获。

### 11. decoy-detect — 诱饵机识别（跨域 D2 / 通用）

- **职责**：诱饵机识别与判定：基于行为 / 漏洞缺失 / 无价值特征识别 2 台诱饵机，时间盒 ≤30min 主动放弃并记录理由（§5.3）。
- **输入（触发条件/前置）**：`recon-ai` 枚举结果、各主机探测反馈。
- **输出**：诱饵判定清单（依据 + 放弃理由）、避免空耗证据。
- **优先级**：P1
- **计分单元**：通用（效率）
- **验收标准**：① 五要素齐全；② 与 `threat-model` 衔接；③ 术语合规（统一用「诱饵机」，禁用 `_Avoid_` 废弃术语）。
- **CI 门禁**：S1 `validate_skill` + `check_glossary`。
- **Out of scope**：不含攻击利用；不含截图捕获。

---

## P2

### 12. capstone-rehearse — Capstone 演练（D11 / 通用）

- **职责**：考前综合演练：按 §4.5 流水线全谱系走查，验收能力覆盖与 24h 节奏（§5.4）。
- **输入（触发条件/前置）**：所有 P0 / P1 技能就绪。
- **输出**：演练报告（覆盖度 / 缺口 / 时间节奏）。
- **优先级**：P2
- **计分单元**：通用（验收）
- **验收标准**：① 五要素齐全；② 覆盖 §4.5 全流水线（threat-model → recon-ai → foothold → 链式 AI 利用 → 独立机 → loot → 域控 → verify → report）。
- **CI 门禁**：S1 `validate_skill` + `check_glossary`。
- **Out of scope**：真实考试利用；截图捕获。

### 13. tooling-automate — 工具与编排自动化（跨域 / 通用）

- **职责**：工具与编排自动化：把重复枚举 / 证据收集 / 校验脚本化，提速 24h 节奏，复用既有共享工具。
- **输入（触发条件/前置）**：各技能步骤模板、`collect_evidence.py` 等共享工具。
- **输出**：自动化脚本 / 编排（复用 `collect_evidence.py` 等）。
- **优先级**：P2
- **计分单元**：通用（效率）
- **验收标准**：① 五要素齐全；② 复用既有共享工具（零新增 seam 优先）；③ 术语合规。
- **CI 门禁**：S1 `validate_skill` + `check_glossary`；可加 S2 测试。
- **Out of scope**：不含攻击逻辑；不含截图捕获。
