# OSAI（AI-300）技能衔接与数据传递一致性设计

> **性质**：研究/设计文档（非规范正文），本次只出设计与择优结论，不改任何既有 skill、不新增代码、不建分支或 PR。
> **核验日期**：2026-11-24（GMT+8）。
> **一手源**：本项目 `docs/contracts/`、`tools/`、`skills/*/SKILL.md`、`docs/governance/GOVERNANCE.md`、S3 快照；AI 红队原则经 `docs/research/` 既有 canonical 锚定。
> **决策首要原则**：提升通过率 > 得分效率 > 攻击效率 > 零破坏 > 可验证性。

---

## 0. 摘要与择优结论（先给结论）

**结论：采用候选 A「派生式交接索引 + 旁路一致性校验」，以 `step_id` 为贯穿六段交接的唯一关联键，tracer bullet 落在 `report-exam × verify-evidence`（D11 报告提交边界）。**

理由三条：

1. **通过率杠杆最大**：S3 快照 §4 的两条失分条款都落在 D11——proof 未在控制面板与截图双通道呈现、缺文档。六段交接中，⑤证据→报告与⑥报告→提交恰好是这两条风险的直接源头，且现状存在**已核实的真实缺陷**（`build_index(real_only=True)` 丢弃侦察证据；`check_report_assets` 从未被调用）。
2. **零破坏**：候选 A 不修改任何既有 skill 语义与门禁判据，只在既有 `collect_evidence.py` / `loot/registry.md` / `report_exam` 的字段上建立**派生索引**与旁路判定，复用已合入的 `osai-orchestrator` 的 `GateResult` 同语义接口。
3. **成本最低、可验证**：不引入新存储、不新增服务；所有衔接规则可用既有 CLI 逐一复验，符合 C1 单一事实源与 C8 不可豁免。

被否决方案：候选 B（统一交接账本）要求 16 个既有技能改数据格式，违反零破坏；候选 C（全量自动调度器）会绕过 11 阶段门禁与 flag 人工确认，违反 C8 且风险不可控。

---

## 1. 六段交接断点清单（已核实）

| 段 | 产出方 → 消费方 | 当前格式 | 断点与风险 | 修复方向 |
|---|---|---|---|---|
| ① 侦察→攻击面 | `recon-ai` `AssetInventory.to_dict()` → attack-* 技能 `input` | 七字段资产字典 / JSON | `recon_ai/cli.py:82-100` 的 `--input-json` 需要 `{target, judgements}` dict，canonical 示例却是 JSON 数组，直接 `ValueError`；`{"step_id": status}` 状态值无法喂给期望 `Judgement` 类型的 `build()`。攻击技能只声明「消费资产清单」，无统一 format 字段，实际靠人工重组。 | 定义版本化资产清单契约（指针到 `tools/recon_ai/model.py#ASSET_FIELDS`），固定唯一落盘路径 `loot/recon-ai.json`，保留三态存在性。 |
| ② 攻击→证据 | 各 attack 技能 → `collect_evidence.py` → 证据片段 | `#### 步骤 <step_id>` 九节契约 | `--shot-cmd` 只记录不执行，却被 `status.py` 当截图处理，制造**假阳性**（`verify-evidence` 标"待补录"仍算齐）；`report.shots_only` 把 `status.py` 的 `shot_status` 当真值，放大风险。三件套本身齐全，但截图真实性无门禁。 | 计分步骤强制 `--screenshot` 实际文件；`--shot-cmd` 仅作提示，不计入 `required_status`。 |
| ③ 证据→战利品 | 证据片段 → `loot/registry.md` | 8 列 markdown 表 | `parse_dual` 的「双通道」单元格实际写的是**截图路径而非 flag 值**（`loot-manage` loot-03 模板：`截图=<screenshot 路径>`），`build_index` 却把该 cell 当 `panel_flags` 的 flag 值 → 双通道比对形同虚设。 | 双通道单元格分离「面板值」与「截图路径」两个字段；`panel_flags` 从面板值派生，不从路径派生。 |
| ④ 战利品→横向 | `registry.md` → 下一次攻击 | 8 列 markdown 表 | 无任何技能调用 `tools/loot_manage/registry.py#reusable_rows()` 查询可复用行，导致对已拿凭据目标重复爆破（效率损失）；`victim` / `source_host` 未与 `asset_id` 对齐，跨主机复用需要人工判断。 | 横向行动前以 `asset_id` + `status` 查询复用行；失效项不复用（保留历史行）。 |
| ⑤ 证据→报告 | `collect_evidence` 片段 → `report_exam.index.build_index` → 报告 | `parse_fragment` 解析结果 | `assemble.py:26` 传 `real_only=True`，导致所有 `synthetic` 来源片段（尤其 `recon-ai` 侦察证据）被静默丢弃 → 报告缺「枚举」段 → 文档扣分；`panel_flags` 无生产方，43 处引用均未从 `registry.md` 派生 → flag 双通道在报告侧缺比对输入。 | 侦察片段按 `host` 显式映射进报告；`panel_flags` 从登记簿面板值派生并注入。 |
| ⑥ 报告→提交 | `report-exam` → `verify-evidence` → PDF/7z | PDF + `.7z` | `check_report_assets` 在 `assemble.py` 与 `tools/report_exam/cli.py` 中**从未被调用**（定义于 `scripts/check_report_assets.py`），断图无法在进入校验前阻断；`window.py` 的 `exam_end_at` / `submit_at` 从未落盘，`remaining()` 恒返回 None，24h 提交窗口无门禁；"是否加密" question 被识别但 `blocking` 为空，未阻断提交。 | 打包前调用断图检查并落盘时间锚；加密问题命中即 `BLOCKED`。 |

**根因归纳**：三份契约缺失（资产清单 / 凭据复用 / flag 表示法），且 C1 单一事实源只在证据工具层强制执行，跨工具边界没有一致的派生路径。

---

## 2. AI 红队最佳实践映射（一手源锚点）

| 原则 | 来源（已核实的本仓库锚点） | 落到交接链的哪一段 |
|---|---|---|
| 证据先行、边打边写 | `GOVERNANCE.md` §4.5「必须边打边写」；`docs/research/osai-ai300-framework-decision.md` §1 报告门槛 | ②⑤：每步先落片段再进下一步 |
| 双通道独立核对 | S3 快照 §4（控制面板 + 截图）；`docs/contracts/collect_evidence.contract.md#3` | ③⑥：面板值与截图路径分离存储，比对时不自比 |
| 单一事实源 | `AGENTS.md` C1；`docs/contracts/consumers.md` | ①④：指针引用，不复制证据本体 |
| 未发现 ≠ 不存在 | `tools/recon_ai/model.py#Existence` 三态 | ①：保留 UNDETERMINED，不把未知伪装成资产 |
| 报告完整性独立于攻击成败 | 框架决策 §1「文档缺失 = 零分」；S3 快照 §4 | ⑤⑥：报告校验独立于攻击结果 |
| 失效战利品不复用 | `skills/loot-manage/SKILL.md` loot-02/质量门 | ④：状态列过滤后再复用 |

---

## 3. 候选方案对比与打分矩阵

打分 1–5，权重按决策首要原则递减：通过率 5、得分效率 3、攻击效率 2、零破坏 5、可验证性 3。

| 候选 | 通过率 (×5) | 得分效率 (×3) | 攻击效率 (×2) | 零破坏 (×5) | 可验证性 (×3) | 加权分 |
|---|---|---|---|---|---|---|
| **A 派生式交接索引 + 旁路一致性校验** | 5 | 4 | 4 | 5 | 5 | **25+12+8+25+15 = 85** |
| B 统一交接账本（新存储 + 全技能改造） | 4 | 4 | 5 | 1 | 4 | 20+12+10+5+12 = 59 |
| C 全量自动调度器（自动驱动技能与改写产物） | 2 | 3 | 5 | 1 | 2 | 10+9+10+5+6 = 40 |

**A 胜出**：唯一同时满足通过率最大化与零破坏的方案。B 需改 16 个技能的产出格式，C 绕过人工确认与阶段门禁，二者均不可接受。

---

## 4. 择优方案详述

### 4.1 唯一关联键：`step_id`

`step_id` 已存在于证据契约（`collect_evidence --step`）、报告片段标题（`#### 步骤 <step_id>`）、登记簿「证据片段路径」字段。方案据此把它提升为贯穿①→⑥的**唯一关联键**：

- 侦察资产以 `evidence_step` 关联到侦察步骤的 `step_id`（`tools/recon_ai/model.py#ASSET_FIELDS` 已有该字段）
- 攻击步骤的 `step_id` 贯穿证据片段、登记簿行、报告段落
- 提交侧以报告段落中的 `step_id` 反查双通道校验结果

**不新增副本字段**：每个环节只存指针，符合 C1。

### 4.2 派生式交接索引（不是新数据源）

定义三类版本化契约，均为**路径指针**，不复制正文：

| 契约 | 唯一事实源 | 派生规则 |
|---|---|---|
| 资产清单 | `tools/recon_ai/model.py#ASSET_FIELDS` + `#AssetInventory.to_dict()` | 固定落 `loot/recon-ai.json`；保留三态；不另立平行清单 |
| 凭据复用 | `loot/registry.md` 8 列 + `tools/loot_manage/registry.py#reusable_rows` | 以 `asset_id` + `status` 过滤；失效项不复用 |
| flag 表示法 | `docs/contracts/collect_evidence.contract.md#3` + `#### flag 取证（双通道一致）` | 面板值取自双通道明细表「面板提交值」列；截图路径取自同表另一列；二者分离 |

索引内容 = `{step_id, host, producer_path, consumer_path, flag_panel, flag_shot, status, verdict}`，全部为既有字段的派生视图，随用随生成、不落盘为新权威。

### 4.3 旁路一致性校验（复用已合入 seam）

在已合入的 `osai-orchestrator` 上增加一个能力域，输出 `GateResult(PASS/BLOCKED)`，与 11 阶段 G0 同语义。六段校验规则：

1. **H1 侦察→攻击**：资产清单可解析、三态齐全、每个资产 `evidence_step` 指向真实片段
2. **H2 攻击→证据**：计分步骤有实际截图文件；`shot_cmd` 不冒充截图
3. **H3 证据→战利品**：flag 行双通道单元格同时含面板值与截图路径，且来自不同字段
4. **H4 战利品→横向**：复用行 `status` 非「失效」；`asset_id` 与目标对齐
5. **H5 证据→报告**：侦察片段按 host 进入枚举段；`panel_flags` 已从登记簿派生注入
6. **H6 报告→提交**：`check_report_assets` 已执行且 PASS；时间锚已落盘；加密问题不命中

判定只取 PASS / BLOCKED，BLOCKED 停在原段重跑，不以后续段补做替代——与主线 §2 G0 完全一致。

---

## 5. Tracer bullet 切入点与端到端数据流

**切入点：`report-exam × verify-evidence`（D11）**。理由：两条失分条款都在此边界；⑤⑥存在已核实的真实缺陷；修复收益直接反映为通过率，而非间接效率。

端到端数据流（逐字段、可复制命令）：

```text
1. 攻击步骤落证据
   collect_evidence.py --step trad-04 --cmd "<cmd>" --out loot/trad-04.md \
     --output-file <out> --screenshot evidence/trad-04.png \
     --flag-panel <PANEL_VALUE> --flag-shot evidence/trad-04.png --strict
   产出：片段含 #### flag 取证（双通道一致） 表（面板值 + 截图路径两列）

2. 战利品登记（面板值与路径分离）
   loot/registry.md 行：| L-4 | flag | <PANEL_VALUE> | host2 | loot/trad-04.md | <ISO8601> | 已取证 | 面板=<PANEL_VALUE>；截图=evidence/trad-04.png |

3. 派生 panel_flags（H5 前置）
   panel_flags = { "host2": "<PANEL_VALUE>" }   # 从双通道表面板列派生，不从截图路径派生

4. 报告组装（侦察证据不丢）
   report_exam.assemble.py#assemble_report(source, panel_flags=panel_flags, real_only=False)
   # 侦察片段按 host 映射进枚举段；flag 段保留 fenced 原值块

5. 断图与时间锚（H6）
   python scripts/check_report_assets.py <报告>       # 必须 PASS
   <report>/window.json: { "exam_end_at": "<ISO8601>", "submit_at": "<ISO8601>" }

6. 提交前复核
   verify_evidence.from_loot(registry, evidence_dir, report_md) → vrf-01..09
   # flag 双通道比对用 panel_flags，不用截图路径
```

---

## 6. 数据传递一致性契约

| 字段 | 唯一事实源 | 禁止行为 |
|---|---|---|
| `step_id` | `collect_evidence.py --step` | 不在登记簿/报告中另造别名 |
| 证据本体 | `evidence/` + `loot/<step>.md`（gitignore） | 不复制字节、不 base64 入报告 |
| 资产清单 | `loot/recon-ai.json`（七字段契约） | 不把 UNDETERMINED 写成 PRESENT |
| 战利品索引 | `loot/registry.md` 8 列 | 不散落对话上下文（§5.2）；不把截图路径当面板值 |
| flag 面板值 | 双通道明细表「面板提交值」列 | 不与截图路径同源自比；不重复提交（域控仅一次） |
| 报告片段 | `tools.report_exam.index.parse_fragment` 节标题 | 不改写 flag fenced 原值块 |
| 时间锚 | `<report>/window.json` | 不用系统当前时间代替提交时间 |
| 门禁结论 | 各阶段 G0 记录 | 不以「基本完成」替代 PASS/BLOCKED |

**不可豁免（C8）**：证据三/五件套、八项检查、flag 双通道、11 阶段顺序、to-spec 两遍——衔接设计只增强数据传递，不削减任何一项。

---

## 7. 优先级路线图

| 优先级 | 动作 | 覆盖断点 | 预期收益 |
|---|---|---|---|
| P0 | H6 断图检查接入 + 时间锚落盘 + 加密阻断 | ⑥ | 直接消除三类提交失分 |
| P0 | H3 双通道字段分离 + `panel_flags` 派生 | ③⑤ | 消除 flag 自比假阳性 |
| P1 | H5 侦察片段按 host 进入报告枚举段 | ⑤ | 补文档完整性扣分 |
| P1 | H2 计分步骤截图真实性门禁 | ② | 消除截图假阳性 |
| P2 | H1 资产清单格式统一（三态保留） | ① | 攻击面传递零 ValueError |
| P2 | H4 凭据复用查询接入 | ④ | 减少重复爆破，提升效率 |

---

## 8. 风险与边界

- **本次不实现代码**：以上均为设计与择优结论，落地须另走 11 阶段主线，并单独取得用户确认。
- **既有缺陷的处置**：断点 ③⑤⑥ 是真实代码缺陷，修复会触碰 `report_exam` / `collect_evidence` 消费者语义；按零破坏约束，优先以派生层与旁路校验规避，确需改既有消费者时须显式声明并按 GOVERNANCE §8.3 留理由。
- **不替代人工确认**：flag 双通道、域控提交、报告终检仍需人工执行，自动层只给判定不放行。
- **离线约束**：所有校验只用本地文件与既有 CLI，不引入联网服务。
- **术语门禁**：本文已按 `GLOSSARY.md` 规避废弃术语；追加内容须复跑 `check_glossary.py`。
