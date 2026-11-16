## 工程规格定稿 (v2)

> **版本** v2 · **状态** 定稿 · **取代关系** 本文件为 `v1`（本条 issue 正文）的工程定稿，v1 全文保留不改；差异见 §4。
> **输入** v1 全文 + `docs/research/attack-infra-canonical.md`（F/P/R/D 编号）+ 仓库现状（`scripts/`、`tests/`、`tools/`、`.github/`）。
> **判据原则**：每条验收条件必须可执行判 `真/假`，无「基本/大体」表述。

### 1. 布尔验收条件（AC）

| # | 验收条件（可判定） | 覆盖 v1 US |
|---|---|---|
| AC-01 | 全部 HTTP 请求经单一传输 seam 发出：`grep -rn "http.client\|urllib.request\|socket.socket" tools/attack_infra/` 除 transport 模块外零命中 | US-01、US-15 |
| AC-02 | 传输默认不读取 `HTTP_PROXY`/`HTTPS_PROXY`；在注入代理环境变量的测试进程中，探测结果与无代理一致（假后端 + 环境变量用例） | US-02 |
| AC-03 | 「`200` + `text/html` + 非 JSON」判 `ABSENT`；「`200` + `application/json` + 命中指纹键」判命中 | US-02 |
| AC-04 | 指纹表覆盖且可分别命中 6 类：`vllm`、`triton`、`litellm`、`ollama`、`k8s_apiserver`、`kubelet` | US-01 |
| AC-05 | `401`/`403` → `AUTH_REQUIRED` 且片段保留状态码与响应摘要；连接失败（无响应）→ `ABSENT` 且 `reason=network` | US-02 |
| AC-06 | 未授权取得模型清单 → `EXPOSED_NO_AUTH`，输出含模型条目数与首个模型标识 | US-03 |
| AC-07 | 未开启 `--allow-inference` 时不发出推理请求（假传输断言零推理路径）；开启后单次推理取得模型输出 → `EXPLOITED` | US-04 |
| AC-08 | 默认配置下不发出 `DELETE`/`PUT`/`PATCH`，且不访问 `pull`/`delete`/`create`/`unload`/`update_weights` 路径（假传输断言方法+路径白名单） | US-14、P-4 |
| AC-09 | 检出凭据线索时输出仅含「前缀 + 长度 + 位置」，片段文本不含原值（断言原值不作为子串出现） | US-07、D-3 |
| AC-10 | 执行 seam 以参数列表调用，`shell=True` 在 `tools/attack_infra/` 零命中 | US-06、US-08 |
| AC-11 | `id`/`whoami` 回显命中本机主机名或本机用户名 → `BLOCKED` 且 `reason=local_echo`（不判 `EXPLOITED`） | US-08 |
| AC-12 | 影响取证片段同时含 before/after 两段响应；两段完全相同 → 不判「已证明影响」 | US-09 |
| AC-13 | `infra-07`、`infra-08` 片段缺失 AI 交互日志或 flag 通道之一 → 该步判定失败（非 `EXPLOITED`） | US-09、US-10 |
| AC-14 | flag 双通道：面板值与截图值一致才判 `EXPLOITED`；不一致判 `BLOCKED` | US-10 |
| AC-15 | 八个步骤各有可运行入口（`infra-01..infra-08`），每步产出 1 份片段；`tests/attack_infra/test_attack_infra_evidence_contract.py` 保持全绿 | US-11、US-15 |
| AC-16 | `ABSENT` 结局的报告含转技能建议（`attack-mcp-tool` / `attack-ai-agent` 二者之一或多个），无建议判失败 | US-12 |
| AC-17 | 输入判据为疑似诱饵机时，报告给出「提前终止 + 判定依据」两项，且不继续发探测请求（假传输断言零请求） | US-13 |
| AC-18 | 报告中每条命令为可直接执行的完整字符串，且不含未替换占位符（断言不含 `<` 与 `>` 包裹的占位片段） | US-14 |
| AC-19 | 全量测试运行期间无外部网络连接（假传输 + 假执行器；断言无真实 socket 到外部地址） | US-15 |
| AC-20 | 行覆盖率 ≥80%（`python scripts/measure_coverage.py`） | US-16 |
| AC-21 | 本地与 CI 使用同一命令集且判定一致（`unittest` + 覆盖率 + S1/S2） | US-16 |
| AC-22 | `python scripts/check_glossary.py` 与 `python scripts/validate_skill.py` 均退出 0；若改动 `SKILL.md`，S2 八步夹具仍绿 | US-16 |
| AC-23 | 仅标准库：`tools/attack_infra/` 无第三方 import（`grep -E "^import|^from"` 逐行核对） | US-15 |
| AC-24 | 不出现 B7 禁用名：`pyrit.orchestrator`、`*Orchestrator`、`AzureOpenAIChatTarget` 在实现与文档中零命中（排除项说明除外） | US-16 |

### 2. 测试决策

- **只测外部行为**：判定枚举值、片段必填字段、报告摘要行、退出码；不断言私有函数序列。
- **替身**：路由表假传输（键=`方法 路径`，值=状态码/`Content-Type`/体）、假执行器（stdout+exit+耗时）、假证据容器（记录入参）。
- **必测负例**：SPA 回退 → `ABSENT`；代理 `502` → 网络失败；kubelet `401` → `AUTH_REQUIRED`；本机回显 → `BLOCKED(local_echo)`；缺失 `--ai-log` → 该步失败。
- **必测正例**：Ollama 形态 `/v1/models` → `EXPOSED_NO_AUTH`；推理成功 → `EXPLOITED`；Triton `v2/health/ready` 200 → 命中 `triton`。
- **参考范式**：`tests/recon_ai/test_recon_ai.py`（假传输 + 判定断言）、`tests/attack_mcp_tool/test_attack_mcp_tool_units.py`（模块单测）、`tests/attack_infra/test_attack_infra_evidence_contract.py`（契约）。
- **红—绿—重构**：每条 AC 先落一个失败用例并留存失败输出，再最小实现转绿，最后重构复跑。

### 3. 门禁映射

| 门禁 | 覆盖 AC | 判定命令 |
|---|---|---|
| B1 | AC-22 | `python scripts/validate_skill.py` |
| B2 | AC-22、AC-24 | `python scripts/check_glossary.py` |
| B3 | AC-19、AC-20 | `python -m py_compile …`；`python -m unittest discover -s tests -t .` |
| B4 | AC-13、AC-15 | 每步 `collect_evidence.py --step infra-0N --strict`；契约夹具 |
| B5 | AC-14 | flag 双通道一致性断言 |
| B6 | AC-20、AC-21 | 覆盖率 + CI S1–S4 |
| B7 | AC-24 | 禁用名 grep |
| B8 | 全部 | issue/PR/commit 互链；门禁留痕 |

### 4. v1 → v2 差异清单

1. 16 条 User Stories → 24 条布尔 AC，逐条给出可执行判据（新增 AC-01/02/10/18/19/23）。
2. 「三元组判据」由原则升级为 AC-03 的可断言形式（含反例）。
3. 「只读优先」由约束升级为 AC-08 的方法/路径白名单断言。
4. 「降级结论」由 5 值枚举固定为机器可判定字符串，并新增 AC-16 转技能建议断言。
5. 「凭据只记指纹」由原则升级为 AC-09 的断言（原值不得作为子串出现）。
6. 新增 AC-11 提权归属校验（本地回显不得判成功）——v1 未显式覆盖。
7. 新增 AC-19/AC-23 离线可测与零第三方依赖（与 `recon-ai` 保持同构）。
8. 核实闸状态：R-1 待核（不影响实现）；R-2/R-3/R-4 转为运行时核实闸（仅活体探测时触发，离线路径不受阻）；R-5 依赖代码执行，保留为 gate。

### 5. 风险与核实闸

| # | 风险 | 缓解 |
|---|---|---|
| RK-1 | 目标端口后续变更导致指纹误判 | 候选端口可配置；判定以三元组为准，不以端口为准 |
| RK-2 | 代理环境差异导致本地与 CI 判定不一致 | AC-02 + AC-19 双向锁定 |
| RK-3 | 活体探测改变目标状态 | AC-08 白名单 + 用户确认的「只读 + 单次推理」策略 |
| RK-4 | 与并行主线任务争抢共享文件（`ci.yml`、`GLOSSARY.md`、预算/覆盖率脚本） | 独立 worktree + `checkout_lock.py --check`；本规格默认不改上述四项 |
