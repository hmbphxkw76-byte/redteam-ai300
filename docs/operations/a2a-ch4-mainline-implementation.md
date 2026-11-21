# A2A Ch4 对齐全量主线：阶段 8 实现记录

> 对应父工单 #292、规格 v2 #294、设计 `a2a-ch4-mainline-design.md`。本文是阶段 8 `implement-spec` 交付物与 G0 记录。

## 1. 实现切片

| 技能 | 变更文件 | 实现内容 | 对应验收 |
|---|---|---|---|
| threat-model | `skills/threat-model/SKILL.md` | 信任边界节第 4 点补四模式/框架风险/四类向量；质量门/校验/豁免同步 | AC-TM-1/2 |
| recon-ai | `skills/recon-ai/SKILL.md` | recon-05/07 补 Agent Card、OpenAPI、注册端点与 SIEM 基线；明确无新 step_id、七字段契约不变 | AC-RC-2 |
| attack-multi-agent | `skills/attack-multi-agent/SKILL.md` | A2A 专项前置、六类攻击面表、C19 判据、C20 收尾/防御、异常分支 | AC-MA-1/2/3/4 |
| recon-ai（代码切片） | `tools/recon_ai/probes.py`（阶段 9 绿相落地） | recon-05 追加 `/.well-known/agent.json` 只读探针 + 纯函数判据 | AC-RC-1/3 |

说明：阶段 8 交付接口完整、可编译、可验证的规格切片；AC-RC-1 的代码绿相按主线 §3.9 在阶段 9 的 TDD 循环中落地，不提前绕过红—绿—重构。

## 2. 实现 → 验收矩阵

| AC | 实现位置 / 动作 |
|---|---|
| AC-TM-1/2 | threat-model SKILL.md 信任边界节 + 质量门/校验/失败豁免 |
| AC-RC-1/3 | probes.STEP_SPECS recon-05 + judge_agent（阶段 9） |
| AC-RC-2 | recon-ai SKILL.md recon-05/07 补录与 ABSENT/UNDETERMINED 语义 |
| AC-MA-1..4 | attack-multi-agent SKILL.md A2A 专项表与质量门/校验/豁免 |
| AC-ALL-1 | 三 SKILL.md checker 口径（LF 归一化）字节：threat-model 5916 / recon-ai 11957 / attack-multi-agent 11743，均 ≤12000；原始 CRLF `wc -c` 值另计 |
| AC-ALL-2 | 静态门禁命令见 §3 |
| AC-ALL-3 | 阶段 9 全量测试与覆盖率 |

### V3 人工核实闸清单（Listing → 原始字段判据）

| Ch4 Listing | 攻击面 | 原始字段判据 |
|---|---|---|
| 13 / §4.4 | 工作流绕过 | `steps_completed` 不含 `content_review` 且 `security_report:null` |
| 16 / §4.4 | PPTX 链接注入 | `ppt_uri` + 下载 PPTX 的显示文本/实际目标 + 落地访问日志 |
| 22 / §4.4 | SQL/xp_cmdshell | tcpdump ICMP echo request 或授权校验文件存在 |
| 28 / §4.5 | 恶意注册 | `/exfiltrated` 请求/响应原文 + `/agents/deregister` 回执 |
| 47 / §4.6 | Card 欺骗 | 解析后 Agent Card `url` 指向攻击者 + 拦截任务日志 |
| 55 / §4.7 | 数据投毒 | 触发后响应含异常敏感字段，且与投毒前基线可比 |

## 3. 阶段 8 G0（B1/B2/B3/B4/B5/B7/B8/B9）

| 项 | 结果 | 实测结果（命令 + 输出摘要） |
|---|---|---|
| B1 | 符合 | `validate_skill` → PASS，16 技能合规 |
| B2 | 符合 | `check_glossary` → PASS，检查 57 个废弃术语 |
| B3 | 符合 | `python -m py_compile tools/recon_ai/probes.py` → 0；`unittest` 契约子集 OK |
| B4 | 符合 | `test_attack_multi_agent_evidence_contract` OK；8 步契约未变 |
| B5 | 符合 | SKILL.md 保留命令+输出+截图、before/after、flag 双通道门禁语义 |
| B7 | 符合 | 未引入旧 PyRIT 对象；`pyrit==1.1.0` 版本锚点不变 |
| B8 | 符合 | C1–C20 与 Ch4 章节对应；父工单 #292、规格 #294 互链 |
| B9 | 符合 | 矩阵 §⑥ 偏离已登记；§⑩ 既有 seam 未变；threat-model 方法论一致 |
| C4 | 符合 | `check_token_budget --check` PASS；三 SKILL.md ≤12000B |

**阶段 8 G0：PASS**。进入阶段 9 `tdd`。
