# attack-multi-agent 工程规格定稿 v2 + 模块设计

> **技能**：`skills/attack-multi-agent/SKILL.md`（D4 / P1 / 计分单元：AI向量机）
> **上游基线**：issue #63（v1 七节）+ T1–T5（已闭环，PR #69 已合入 SKILL.md 与 S2 证据契约夹具）
> **框架组合（强制对齐矩阵 §⑩，B9）**：A2ASecBench（协议感知基准，ICLR'26）+ Cisco a2a-scanner（Agent Card 分析）+ **PyRIT HTTPTarget（深度补位，非主演）** + A2A Python SDK/samples（演练目标基座与 recon）
> **冲突优先级**：`docs/operations/skill-mainline-workflow.md` 文首 > GOVERNANCE > CI-CD > 本文件
> **本文档性质**：阶段 3（v2 布尔验收条件）+ 阶段 6（模块/接口设计）合一本，作为阶段 8 实现与阶段 9 测试的唯一判据源（C1 单一事实源）。

---

## 1. v2 布尔验收条件（AC）

每个条件可机判（命令或人工判据），逐条映射 SKILL.md 执行体 a2a-01…a2a-08。

| AC | 验收条件（布尔） | 判据 |
|---|---|---|
| AC-01 | a2a-01 经 `collect_evidence.py --step a2a-01 --strict` 落盘拓扑证据 | 片段含 `BUS`/`MEMORY` 端点清单 + 正常协作基线 |
| AC-02 | a2a-02 消息操纵命令可被 copy/paste 复现且输出证明消息被注入 | 片段含 `--cmd` 与注入后消息响应原文 |
| AC-03 | a2a-03 智能体冒充命令可复现且输出证明某 agent 身份被伪造 | 片段含 `--spoof` 与冒充生效响应 |
| AC-04 | a2a-04 共享记忆投毒命令可复现且前后对照证明记忆被改写 | 片段含 `before/after` 记忆值 |
| AC-05 | a2a-05 上下文投毒命令可复现且证明共享上下文被污染 | 片段含注入前后全局 prompt 差异 |
| AC-06 | a2a-06 工作流破坏命令可复现且证明偏离既定编排任务 | 片段含 spoofed task 与偏离响应 |
| AC-07 | a2a-07 下游决策影响取证含前后协同结果差异 + AI 交互日志（§6.3） | 片段含 `trace` 差异与 `--ai-log` |
| AC-08 | a2a-08 flag 取证含 `whoami`/`id` 访问证明 + `ai_vector.txt` 双通道一致 | `--flag` 面板值 == 截图/正文值 |
| AC-09 | 每步证据三件套/五件套结构经 `collect_evidence.py --strict` 校验通过 | 退出码 0；缺件套退出码 1 |
| AC-10 | 对象图符合 B7：`pyrit==1.1.0`，主攻 `HTTPTarget`，PyRIT 仅深度补位 | `OBJECT_GRAPH` 声明 PyRIT 非主演 |
| AC-11 | 框架组合取自矩阵 §⑩：A2ASecBench/a2a-scanner 为外部适配 seam，PyRIT HTTPTarget 补位 | `scanner` seam 注入点 + `pyrit_attack` 懒导入 |
| AC-12 | 效果等级四值互斥且「仅本地自证/目标侧未生效」封顶为「部分生效」 | `grade()` 纯函数单测覆盖四值 |
| AC-13 | 截图缺失时证据标「待补录」，绝不伪造截图文件 | `NullCapture`/`FakeCapture` 路径单测 |
| AC-14 | 单测覆盖业务代码 ≥80% 且全量 `unittest` 通过 | `python -m unittest discover -s tests` 绿 + 覆盖率数字 |
| AC-15 | MCP/MA 不混用：本技能只处理多 agent 协同面，单 agent 注入回退 `attack-ai-agent` | 失败与豁免分支单测 |

v1→v2 差异：v1 为七节行为描述（What）；v2 把 8 条 User Story 收敛为 AC-01…AC-15 布尔判据，并新增模块设计（§2）、框架合规（AC-10/AC-11）、诚实定级（AC-12）、反伪造（AC-13）四类原 v1 未显式约定的可机判项。

---

## 2. 模块与接口设计（S6）

深层模块原则（接口少、实现深；调用方只依赖 `__init__` 公开面）。

```
tools/attack_multi_agent/
├── __init__.py      # 公开面：run_attack / Runtime / OBJECT_GRAPH / 数据模型 / STEP_*
├── model.py         # 值对象：Observation / Signals / StepVerdict / AttackRequest / AttackReport / LEVELS
├── steps.py         # 步骤契约：a2a-01…a2a-08 + steps_for_paths（顺序：定位→A→B→C→flag）
├── grade.py         # 纯函数 derive()/grade()：四值定级（AC-12）
├── transport.py     # 缝：HttpClient 接口 + UrllibHttpClient（生产）+ FakeHttpClient（测试替身）
├── a2a.py           # A2A 客户端：总线(发现/注入/冒充) + 记忆/上下文投毒 + 编排(破坏/影响)
├── scanner.py       # 缝：A2ASecBench/a2a-scanner 外部适配 seam（主演），默认内建轻量 Analyzer
├── pyrit_attack.py  # 缝：PyRIT HTTPTarget 深度补位（懒导入，仅 --pyrit 触发）
├── evidence.py      # 缝：委托 collect_evidence.py；RecordingWriter 测试替身
├── shot.py          # 缝：截图（HeadlessCapture / NullCapture / FakeCapture）
├── poc.py           # 示意脚本共享薄壳：退出码/输出格式（逻辑全部委托 a2a.py）
├── runner.py        # _Session + _HANDLERS(a2a-01…08) + run_attack + _emit（每步 1:1 落盘）
└── cli.py           # 薄壳命令行
```

### 2.0 SKILL.md 点名示意脚本（顶层薄壳）

SKILL.md 攻击路径 A/B/C 中列出的 5 个「示意脚本」以顶层薄壳落地，命令字面可执行
（对齐 SKILL「校验标准」的 copy/paste 可复现要求）：

| SKILL.md 命令 | 薄壳 | 委托 |
| --- | --- | --- |
| `python tools/msg_inject.py --bus --from --to --payload` | `tools/msg_inject.py` | `A2ABusClient.inject_message` |
| `python tools/agent_impersonate.py --bus --spoof --cmd` | `tools/agent_impersonate.py` | `A2ABusClient.impersonate` |
| `python tools/memory_poison.py --store --key --value` | `tools/memory_poison.py` | `MemoryStoreClient.poison_memory` |
| `python tools/context_poison.py --endpoint --inject` | `tools/context_poison.py` | `MemoryStoreClient.poison_context` |
| `python tools/workflow_disrupt.py --orchestrator --task` | `tools/workflow_disrupt.py` | `OrchestratorClient.disrupt_workflow` |

薄壳不写证据（证据仍由 `runner` 经 `collect_evidence.py` 统一落盘，C1）；
`--dry-run` 经 `DryRunClient` 只渲染命令不发请求，URL/请求体仍由 `a2a.py` 构造，
故 dry-run 输出与真实执行同源。`memory_poison --before` 先读原值，直接形成前后对照。

### 2.1 三缝注入点（Runtime）

`Runtime` 持有 4 个可注入点，默认全为生产实现；单测注入替身即离线（AC-14 可离线跑）：

- `client: HttpClient` → `UrllibHttpClient`（生产）/ `FakeHttpClient`（测试）
- `writer` → `EvidenceWriter`（生产，委托 `collect_evidence.py`）/ `RecordingWriter`（测试，只记录参数）
- `capture` → `HeadlessCapture`（有浏览器）/ `NullCapture`（无浏览器，标待补录）/ `FakeCapture`（测试）
- `scanner` → 内建 `BuiltinAnalyzer`（默认）/ `A2ASecBenchAdapter`（实测时注入，对齐 AC-11）

### 2.2 对象图（B7 / AC-10）

```python
OBJECT_GRAPH = {
  "framework": "pyrit==1.1.0（仅深度补位，非主演）",
  "lead": "A2ASecBench + a2a-scanner（外部适配 seam）",
  "target": "HTTPTarget（PyRIT 打 A2A 端点多轮）",
  "scorer": "SubStringScorer（PyRIT 补位判定）",
  "memory": "SQLiteMemory（PyRIT 补位留证）",
  "sdk": "A2A Python SDK/samples（演练目标基座与 recon）",
  "notes": "PyRIT 无原生 MA 策略；矩阵 §⑩ 规定 MA 由 A2ASecBench/a2a-scanner 主导"
}
```

PyRIT 仅在 `pyrit_attack.run_pyrit_multiturn()` 内**懒导入**（模块顶层不 import pyrit，满足 B7 不强制依赖），仅对可达 A2A 端点做多轮深度利用时用。

### 2.3 路径顺序（`steps_for_paths`）

`定位(topology) → A(a2a-01..03) → B(a2a-04..05) → C(a2a-06..07) → flag(a2a-08)`，
与 SKILL.md 执行体顺序严格一致；`--step` 可单步，`--path` 可切片。

---

## 3. 风险与核实闸

- **R1 A2ASecBench/a2a-scanner 为外部依赖**：经 `scanner` seam 适配，默认内建 Analyzer 保证离线可跑，实测时注入真适配器（不阻断其余路径，AC-11）。
- **R2 PyRIT 未安装**：`pyrit_attack` 懒导入，未装时 `--pyrit` 显式报错非静默失败。
- **R3 目标为单 agent 无协同面**：a2a-01 探测无多 agent 拓扑时记「已跳过」并建议改走 `attack-ai-agent`（AC-15）。
- **R4 冒充/投毒被消息签名或护栏拦截**：记「未生效」+ 拦截原因，不重试同一被拦截动作（SKILL「失败与豁免」）。
- **R5 疑似诱饵机**：a2a-01 判定 0 分无多 agent 面时 ≤30 分钟结束，不在 0 分主机空耗。

---

## 4. 阶段间交接

- 本文件 = 阶段 3(v2) + 阶段 6(设计) 合一本，供 S8 实现与 S9 测试消费。
- S7 术语增补见 `GLOSSARY.md`（`## 攻击面` 段 A2A 相关条）。
- S10/S11 以 `git merge-base origin/main HEAD` 后 diff + 本文件验收条件为双轴判据。
