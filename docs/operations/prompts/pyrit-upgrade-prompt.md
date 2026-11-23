# PyRIT 升级执行提示词模板（可直接拷贝）

> 使用方法：将 `<目标版本>`（如 `1.3.0`）、`<上一稳定版本>`（如 `1.2.1`）替换后整段拷贝给智能体。
> 本模板遵循 `AGENTS.md` C1–C8 与 `docs/operations/pyrit-upgrade-runbook.md`。

---

【角色】
资深 AI 安全工程师兼 Python 工程化负责人，教学导向：每个决策说明依据，每个结论附一手源或可复跑命令。

【总目标】
把仓库的 PyRIT 目标版本从 `<上一稳定版本>` 升级到 `<目标版本>`，在**不重写框架核心、不改任何 SKILL.md** 的前提下保持技能持续可用；产出可逐条验证的升级证据，并明确区分「运行时实测」「一手源核实」「UNVERIFIED」。

【唯一可信源】
- 流程：`docs/operations/pyrit-upgrade-runbook.md`（唯一可信源）。
- 版本事实唯一来源：`tools/pyrit_compat/data/versions/<version>.json`（发布事实 + 变更 + 签名 + 适配器规则）。
- 一手源：PyPI JSON API、GitHub `v<目标版本>` release 与 tag 源码；`docs/research/pyrit-version-tracking-1.2.x.md` 仅作历史基线，不得替代新版本取证。
- 工作区：隔离 worktree `D:/_pyrit-compat_wt`（分支 `feat/pyrit-compat`）；未获明确指令不提交、不推送。

【必须完成】
1. 检测 `<目标版本>` 发布事实（版本、日期、wheel/sdist 哈希），rc/dev 版本忽略。
2. 一手源核实新增/更新/弃用/移除的 API、函数、参数与行为，逐条给出 URL + 核实日期；未核实项标 `UNVERIFIED` 并阻断验收。
3. 复制上一版本事实文件为 `data/versions/<目标版本>.json`，只更新 `release`、`changes`、`signatures`、必要 `adapters` 规则；核心模块零改动。
4. 静态验证：`checker selftest` / `map` / `check --target <目标版本>` / `lock --version <目标版本>`，调用点分类须 100%、`error=0`、`verdict=PASS`。
5. 运行时验证：使用本机 `C:/Users/liude/AppData/Local/Programs/Python/Python313/python.exe` 执行 `python -m tools.pyrit_compat.runtime_probe --version <目标版本> --report docs/operations/pyrit-compat-runtime-verification.json`；须版本匹配、签名全 PASS、确定性 `SubStringScorer` 命中；未安装或沙箱阻断则如实标 `UNVERIFIED`。
6. 回归与门禁：全量 `unittest`、`measure_coverage --target pyrit-compat --min 80`、`validate_skill`、`check_glossary`、`check_token_budget --check`、`check_tools_compile`、两项契约检查、`check_evidence_contract`、`checkout_lock --check`、markdownlint、C4 产物预算。
7. 更新 `docs/research/` 版本事实、`docs/operations/pyrit-compat-alignment-matrix.md` 与 `requirements.txt`；明确写出哪些结论来自运行时实测、哪些仅来自一手源。

【硬约束】
- 不改 `tools/pyrit_compat/{version,model,alert,versions,manifest,mapper,compat,checker,runtime_probe}.py` 的核心逻辑；新能力只通过事实文件与适配器规则登记。
- 不改 `skills/*/SKILL.md`、证据三/五件套、flag 双通道、`report-exam` 解析契约。
- CI 新校验用独立步骤，不改并发会话共用长行；C1 单一事实源，版本事实不在文档/代码重复转抄。
- 不连真实目标 `http://192.168.40.189`，不读真实凭据，不投放真实载荷。

【最终交付】
1. 新版本事实文件与一手源清单。
2. 静态检查报告、调用点映射、运行时报告（含实测版本与逐符号签名结果）。
3. 更新后的研究文档与对齐矩阵，列出 PASS / UNVERIFIED 及理由。
4. 全量门禁与测试输出摘要、覆盖率数字。
5. 明确结论：本次升级改了哪些文件、哪些文件永不改、回滚命令是什么；不得笼统宣称「已自动升级」。
