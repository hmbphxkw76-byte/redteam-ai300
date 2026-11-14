# recon-ai 设计记录（模块边界与接缝）

> **版本** v1.1 · **对应规格** issue #121（行为规格 v1 + 工程规格定稿 v2）
> **依据** `docs/research/recon-ai-canonical.md` · `GOVERNANCE.md` §4.2 · ADR-0002 / ADR-0004 / ADR-0005
> **性质** 阶段 6 交付物：模块职责、公开接口、依赖方向、seam 清单、权衡与被否决方案
> **修订** v1.1 按阶段 10 双轴审查（#18）校正依赖表、接口名与截断口径，与实际代码逐条对齐。

---

## 1. 模块职责划分

| 模块 | 单一职责 | 公开接口（实际导出名） | 依赖（单向，实测） |
|---|---|---|---|
| `model` | 领域类型与契约字段的唯一定义处 | `Existence`／`Category`／`ProbeResult`／`Asset`／`AssetInventory`／`ASSET_FIELDS`／`credential_hint` | 无（纯数据 + 标准库） |
| `transport` | 唯一网络出口（seam S1） | `HttpResponse`／`Transport`／`UrllibTransport`／`FakeTransport`／`make_transport` | 无本项目依赖 |
| `fingerprint` | 响应签名 → 产品/版本/类别 | `Match`／`RULES`／`detect`／`primary` | `model` |
| `probes` | 7 步声明式探测（请求 + 解析 + 判据） | `RequestSpec`／`StepSpec`／`STEP_SPECS`／`JUDGES`／`find`／`step_requests`／`parse_sse` | `model`、`fingerprint` |
| `shot` | 访问证明截图（seam S3） | `ShotCapture`／`NullShot`／`FakeShot`／`HeadlessShot`／`make_shot`／`render_transcript` | 无本项目依赖 |
| `evidence` | 证据落盘，委托共享收集器（seam S2） | `EvidenceWriter.emit`／`fragment_path`／`load_manifest` | 外部 `tools/collect_evidence.py`（子进程） |
| `policy` | 分级门控、诱饵判定、时间盒、失败隔离 | `PROFILES`／`normalize_profile`／`gate_requests`／`judge_decoy`／`FailureBudget` | `probes`（取请求声明） |
| `inventory` | 判据 → 七字段清单 + 契约校验 | `build`／`host_of` | `model`、`probes`（step↔类别唯一映射）、`policy` |
| `runner` | 编排：执行 → 证据 → 清单 → 报告 | `run_recon`／`RunReport`／`build_url`／`redact` | 上述全部（`probes`／`inventory`／`evidence`／`policy`／`shot`／`transport`／`model`） |
| `cli` | 命令行入口与退出码语义 | `main` | `policy`、`runner` |

**依赖方向**：`cli → runner → {probes, inventory, evidence, policy, shot, transport} → {fingerprint, model}`，另 `inventory → probes`、`policy → probes`。全部单向，无环（`python -c "import tools.recon_ai"` 可验证）。

**已知取舍**：`inventory` 与 `policy` 反向依赖 `probes` 的步骤表，是为了让「类别 ↔ step_id ↔ 请求声明」保持单一事实源（C1）；代价是这三者耦合于同一张表，改表需同时复核三处断言（由 `tests/test_recon_ai.py` 覆盖）。

---

## 2. seam 清单（3 个，均在能力边界）

| # | seam | 位置 | 可替换实现 | 存在理由 |
|---|---|---|---|---|
| S1 | 网络传输 | `transport.Transport` | `UrllibTransport`（生产）/ `FakeTransport`（测试） | 7 条路径全为 HTTP 面；替换后全部判据可离线验证 |
| S2 | 证据落盘 | `evidence.EvidenceWriter` | 子进程调用共享收集器（生产）/ 任意替身（测试） | C1：证据格式单一事实源，`report-exam` 与 CI 消费同一格式 |
| S3 | 截图捕获 | `shot.ShotCapture` | `HeadlessShot`（生产）/ `FakeShot` / `NullShot`（无浏览器时诚实降级） | 截图属外部能力（浏览器），须可注入以避免测试依赖 GUI |

**注入点**：三者经 `run_recon(transport=, shot=, writer=)` 显式注入，不使用全局状态或隐式环境读取。

---

## 3. 关键权衡与被否决方案

| 决策 | 采用 | 否决方案 | 依据 |
|---|---|---|---|
| 探针形态 | 声明式规格（请求 + 解析器 + 判据） | 拼接 shell 命令字符串 | 命令字符串不可测、不可扩展；声明式使新增类别只加一条规格 |
| 包结构 | 单包 `tools/recon_ai`，与 `tools/attack_ai_agent` 同构 | 按 7 类组件拆 7 个子包 | 7 类共享同一套存在性判据，拆分只产生重复并使变更面放大 7 倍 |
| 证据写入 | 子进程调用共享收集器 | 本包内重实现片段渲染 | C1；重实现会造成两套格式判据漂移（阶段 10 已验证该风险的现实性） |
| 截图获取 | 浏览器无头渲染（`url` 直截 / `transcript` 转录页） | 仅记录截图钩子命令 | 官方要求截图作为访问证明；只记钩子等于把缺口留给无法补拍的报告阶段 |
| 截图语义 | 区分 `url` 与 `transcript` 并显式标注 | 一律以 URL 截图冒充 | POST/SSE 端点无法用 GET 截图代表，冒充构成证据失真 |
| 存在性判定 | 三值枚举（探测级 + 类别级两处均用） | 布尔 | 200 不等于存在；「未发现」不等于「不存在」 |
| 观测复用 | `recon-07` 复用 `recon-02` 的聊天响应 | 各自独立发请求 | OPSEC 低频低噪；同一响应两处判读不损失证据强度 |
| PyRIT 依赖 | 不导入；仅在设计上预留延迟导入位 | 顶层导入 pyrit | 未安装环境须可运行（AC-23）；本次实现无对抗性探针需求 |
| 输出截断 | 单请求摘要 800 字符（`ProbeResult.brief(limit=800)`），注明原始字节数 | 声称「全文见留存入径」 | 实现并未持久化原始响应，虚指会构成误导（阶段 10 #7） |

---

## 4. 分级语义（消歧）

- **passive（默认）**：无状态变更的 HTTP 读 + 一次无害回显 POST（请求体为固定回显串）。理由：聊天端点是目标公开功能，单次回显不构成攻击；若归入 active，则 `recon-02`/`recon-07` 在默认档无法取证。
- **active（显式）**：在 passive 基础上追加定向端口探测（清单来自 `recon-04.active_requests`，上限 8），禁止全端口扫描。

---

## 5. 与 ADR 的一致性

- **ADR-0004（PyRIT 1.1.0）**：本包零 `pyrit` 导入；若未来引入对抗性探针，须用 `pyrit.executor.attack.PromptSendingAttack` 与 `pyrit.score.SubStringScorer`，禁止 `pyrit.orchestrator`／`*Orchestrator`／`AzureOpenAIChatTarget`／`XpiaAttack`。
- **ADR-0005（Token 预算）**：本记录 ≤6KB；证据片段按步截断，不复制宪法条款。
- **ADR-0002（评分驱动）**：recon-ai 为 P0 前置，设计目标为「减少空耗」（诱饵时间盒与运行时到期降级）与「保证证据可计分」（证据契约），非攻击能力最大化。

---

## 6. 门禁记录（阶段 6）

| 编号 | 检查项 | 依据 | 实测 | 判定 | 结论 |
|---|---|---|---|---|---|
| B2 | 术语一致 | `check_glossary.py` | PASS（29 个废弃术语 0 命中） | 符合 | PASS |
| B7 | 无旧版对象 | §2.1 | `grep -rn "orchestrator\|AzureOpenAIChatTarget\|XpiaAttack" tools/recon_ai` → 0 命中 | 符合 | PASS |
| B8 | 可追溯 | §2.1 | 每条决策回溯调研事实或 ADR 编号 | 符合 | PASS |
| AC-① | seam 数量与位置与 v2 一致 | 验收① | 3 seam（v2 §4 记 2 个，S3 为阶段 10 补充并在此登记） | 符合 | PASS |
| AC-② | 每个公开接口有职责与输入输出 | 验收② | §1 表逐行给出实际导出名 | 符合 | PASS |
| AC-③ | 依赖方向单向 | 验收③ | §1 末行；`python -c "import tools.recon_ai.cli"` 通过 | 符合 | PASS |
| AC-④ | 测试替身可替换外部依赖 | 验收④ | S1/S2/S3 均有替身（`FakeTransport`／`EvidenceWriter`／`FakeShot`） | 符合 | PASS |
| AC-⑤ | 与 ADR 冲突项显式标注 | 验收⑤ | §5 三条 ADR 逐条说明 | 符合 | PASS |

**阶段结论**：`PASS`（不符合项 0）。
