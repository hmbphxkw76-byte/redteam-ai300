# recon-ai 端到端验证结果与证据清单

> **版本** v1.4 · **验证日期** 2026-11-14 22:41–22:42（GMT+8）· **修订** 修正 `recon-07` 判定文案重复包裹后重跑；报告侧截图改为正文内嵌，图片迁至 `report/assets/` 以匹配预览器解析基准（v1.3 内容保留在 §7-8）
> **目标** `http://192.168.40.189`（OWASP AIVP 演练实例，非 OSAI 正式考试环境）
> **性质** 阶段 8/9 验收留痕：执行 → 取证 → 结果产出 的闭环证据
> **产物位置** `evidence/recon-ai/`（`.gitignore` 排除，可由第 8 节一条命令完整重建）
> **上游** issue #121（规格 v1/v2）· `docs/operations/recon-ai-design.md` · `docs/research/recon-ai-canonical.md`

---

## 1. 验证范围与方法

| 维度 | 内容 |
|---|---|
| 被测对象 | `tools/recon_ai` 全包（10 模块）+ 共享证据收集器 `tools/collect_evidence.py` 扩展项 |
| 执行分级 | `passive`（默认档；未触发端口探测） |
| 请求总数 | 11 次（recon-01..06 各 1–2 次；`recon-07` 复用 `recon-02` 响应，零新增请求） |
| 外部依赖 | 仅标准库 `urllib`；截图经本机 Edge 无头渲染 |
| 判定口径 | 存在性三值（存在／不存在／不可判定）；资产清单七字段契约 |
| 证据口径 | 三件套 + 脚本来源 + 模型交互留痕 + flag 双通道 + JSONL 清单 |

---

## 2. 运行记录

```bash
python tools/recon_ai/cli.py run --target http://192.168.40.189 --lab MM_04 \
  --out-dir evidence/recon-ai
```

- 退出码：**0**（清单契约合规）
- 传输：`urllib (recon-ai)`　截图：`headless:msedge.exe`　证据工具：`collect_evidence.py`
- 资产 7 条，不可判定 1 类（向量库），疑似诱饵：否，失败步骤：无

---

## 3. 逐步判定（recon-01..07）

| 步骤 | 存在性 | 产品/引擎 | 关键依据（原文摘要） | 证据片段 | 截图 |
|---|---|---|---|---|---|
| recon-01 | 存在 | LongCat-2.5 | `/api/config` 暴露 `llm_model_default`；`/v1/models` 返回 SPA 回退页 → 记不存在 | `recon-01.md` | `recon-01-url.png`（url） |
| recon-02 | 存在 | SSE 流式聊天面 | `event: meta`（`request_id`/`lab_id`/`phase=3`/`control_mode=off`）+ `data:{"content"}` 分片 | `recon-02.md` | `recon-02-transcript.png` |
| recon-03 | 存在 | RAG 检索链路（痕迹） | 前端产物含 `retrieved/knowledge/vector/documents` 痕迹 | `recon-03.md` | `recon-03-url.png`（url） |
| recon-04 | **不可判定** | 不可判定 | 被动面无独立向量库端口证据；「未发现」不等于「不存在」，需 `--profile active` | `recon-04.md` | `recon-04-url.png`（url） |
| recon-05 | 存在 | agent 编排面（推断，框架不可判定） | 实验面 422 暴露 `request_id` 语义 + 遥测端点 200 | `recon-05.md` | `recon-05-url.png`（url） |
| recon-06 | 存在 | 凭据校验预言机（MCP 信任边界面） | 失败语义为 **HTTP 200** + `{"success":false}`（禁以状态码判失败） | `recon-06.md` | `recon-06-transcript.png` |
| recon-07 | 存在 | 护栏（放行原样回显） | 无害回显 `RECON-PROBE-OK` 原样返回；6 项安全响应头全缺；`control_mode=off` | `recon-07.md` | `recon-07-transcript.png` |

---

## 4. 资产清单（7 条，七字段齐全）

| 资产ID | 类别 | 产品/引擎 | 版本 | 端点 |
|---|---|---|---|---|
| `ai-llm-192.168.40.189-01` | LLM引擎 | LongCat-2.5 | 2.5 | `/api/config` |
| `ai-model-192.168.40.189-02` | 模型服务 | SSE 流式聊天面 | 不可判定 | `/api/labs/MM_04/chat`（`phase=3`） |
| `ai-rag-192.168.40.189-03` | RAG库 | RAG 检索链路（痕迹） | 不可判定 | `/explore` |
| `ai-vector-192.168.40.189-04` | 向量库 | 不可判定 | 不可判定 | `/api/labs/MM_05/summary` |
| `ai-agent-192.168.40.189-05` | agent系统 | agent 编排面（推断） | 不可判定 | `/api/labs/DE_01/summary` |
| `ai-mcp-192.168.40.189-06` | MCP工具面 | 凭据校验预言机 | 不可判定 | `/api/secrets/validate` |
| `ai-guardrail-192.168.40.189-07` | 护栏 | 护栏（放行原样回显） | 不可判定 | 不可判定（行为类） |

凭证线索：仅 `ai-model-…-02` 有指纹 `Bearer-26924458`（`set-cookie: aivp_sid=<uuid>` 的 SHA-256 前 8 位），其余为「无」；产物中不含任何明文凭据（AC-15 正则断言）。

---

## 5. 证据清单（`MANIFEST.jsonl`，7 行）

| step_id | 时间戳 | 输出 sha256（前 16） | 截图 sha256（前 12） | 截图类型 | 三件套 |
|---|---|---|---|---|---|
| recon-01 | 22:41:42 | `b199edf0ab34f306` | `ca501313a881` | url | 齐全 |
| recon-02 | 22:41:48 | `f4df9d212ceb55b7` | `c7f1a9e49b8b` | transcript | 齐全 |
| recon-03 | 22:41:57 | `efbd15a7acf72dd2` | `ea29965b9ac1` | url | 齐全 |
| recon-04 | 22:42:05 | `7f4a083709669f0b` | `6ab9c85162c0` | url | 齐全 |
| recon-05 | 22:42:14 | `d21a34d3f2f566d7` | `6ab9c85162c0` | url | 齐全 |
| recon-06 | 22:42:15 | `0a77187e814fbe2c` | `7d97885185e0` | transcript | 齐全 |
| recon-07 | 22:42:17 | `0c5daf1e1eac02df` | `210a9331a14a` | transcript | 齐全 |

> **复核提示**：`recon-04` 与 `recon-05` 的截图哈希相同，属预期——两个 summary 端点返回**逐字节相同**的 422 schema（`{"detail":[{"type":"missing","loc":["query","request_id"],...}]}`），不是重复落盘。复核时以 sha256 比对 `recon-04-url.png` / `recon-05-url.png` 与 `curl` 原文即可确认。

每个 `recon-0N.md` 含：确切命令（bash 围栏，可直接 copy/paste）、关键输出（原始响应）、截图（访问证明）、分析注记（判定与依据，与原始输出分离）、脚本/PoC（本次均为「未使用脚本」）、证据校验表。**AI 交互日志仅出现在真正向目标模型发送提示的 `recon-02` 与复用其响应的 `recon-07`**；其余步骤不臆造交互留痕（§6.3 真实性，见 §7-6）。

---

## 6. 官方规范对齐矩阵

| 官方要求 | 落点 | 实测 |
|---|---|---|
| 每步确切命令且可 copy/paste（S3 §1） | 片段「确切命令」 | 7/7 具备，命令为完整 `curl` 含请求体 |
| 相关控制台输出（S3 §1） | 「关键输出」 | 7/7 原始响应；bundle 类超长输出截断并注明 |
| 脚本/exploit 来源或副本 + 修改说明（S3 §1） | 「脚本 / PoC」 | 本次 0 脚本，7/7 显式声明「未使用脚本」；机制经 AC-17 双态用例验证 |
| 每阶段截图（S3 §1） | 「截图（访问证明）」 | 7/7 真实浏览器渲染，标注 `url`/`transcript` 类型 |
| copy/paste 可复现（S3 §1、§6.1） | 命令围栏 + 报告第 4 节 | 逐条可复跑（见第 8 节） |
| 模型交互入正文（§6.3） | 「AI 交互日志」 | `recon-02`/`recon-07` 记录通道/模型/提示/输出/采纳 |
| flag 双通道一致（§6.2 / §2 失分条款） | 「flag 取证（双通道一致）」 | 本次侦察阶段无 flag，状态「未提供」；机制经 AC-18/AC-20 验证 |
| 术语合规（§8.2-8） | 片段叙述正文 | `check_glossary.py` 0 命中（29 个废弃术语） |

---

## 7. 偏差、豁免与限制（GOVERNANCE §8.3）

1. **CLI 未内置 `recon-07` 的合成 flag**：`SKILL.md` 原命令模板含 `--flag "AI-ASSETS-<ENGAGEMENT>-<DATE>"`。实现未自动合成该标记——侦察阶段的自造标记会被报告读者误认为取分证据，属证据失真。**偏离理由**：证据真实性优先于模板字面一致；操作者若在交战约定中定义了标记，可经 `--flag-panel` / `--flag-shot` 显式登记（机制已实现并测试）。
2. **`transcript` 截图类型**：POST/SSE 端点无法用 GET 页面截图代表，故渲染「命令 + 原始响应」转录页后截图，并在片段中标注类型。**偏离理由**：以 URL 截图冒充 POST 结果为证据失真；标注后读者可自行判断证据强度。
3. **`recon-04` 记「不可判定」而非「不存在」**：被动面无端口证据，主动探测未执行（默认被动档）。**限制**：如需定级，须显式 `--profile active`（定向 6333/8080/19530/8000，上限 8 端口）。
4. **覆盖率**：`tools/recon_ai` 行覆盖 90.2%（门槛 80%）；未覆盖集中在 `shot.py` 的浏览器失败分支与 `runner` 的极端 IO 分支。
5. **环境边界**：本验证针对 AIVP 演练实例，其资产构成不外推为 OSAI 考试环境事实（见调研文档 §1）。
6. **阶段 10 复审后的行为变更**：输出经凭据脱敏（`<REDACTED>`）后才入证据；时间盒为运行时到期即中止（不再仅记常量）；探测级存在性三值独立于类别级判定；凭据线索由 `set-cookie` 压缩为指纹。上述均已在本次重跑中生效。
7. **判定文案重复包裹修正（v1.3）**：`probes.judge_guardrail` 的 `behavior` 已含「护栏」语义，`product` 又包一层「护栏（%s）」，产出 `护栏（护栏放行原样回显）`。现 `behavior` 改为 `放行原样回显`/`拒答`/`改写/截断`，产品名归一为 `护栏（放行原样回显）`。
8. **报告侧截图形态（v1.4 修正）**：正文按 `report_exam/sections.py` 的契约以 `![]()` 内嵌（7/7），不再以文件名文字引用——文字引用在 PDF 中即为无图，属 §6.1 不可豁免项。图片地址为 `report/assets/<file>.png`：预览器按「工作区根 + 原文 src」解析，`../evidence/...` 曾被解析成 `D:/文档/GitHub/evidence/...` 而报 `Failed to load image`；且 `evidence/` 在 `.gitignore` 中，直接引用会使克隆者看到空图。`report/assets/` 为 `evidence/recon-ai/shots/` 的逐字节镜像（`diff` 校验相等），随仓库提交。
9. **AI 交互日志归属修正**：首版实现对 `recon-03/04/05/06` 亦输出了复用 `recon-02` 的交互留痕，属跨步错归属（会把他人步骤的模型交互计入本步判定依据）。已改为仅「真的发送了提示」的步骤产出，并新增回归用例 `test_ai_log_only_for_steps_that_prompt_the_model`；本版证据为该修复后的重跑结果。

---

## 8. 复现步骤（技术读者可直接执行）

```bash
# 1. 全量重建证据与清单（约 35 秒，7 次截图）
python tools/recon_ai/cli.py run --target http://192.168.40.189 --lab MM_04 \
  --out-dir evidence/recon-ai

# 2. 只看资产清单
python tools/recon_ai/cli.py inventory --path evidence/recon-ai/ai-assets.json

# 3. 单步复核（示例：recon-01）
curl -s http://192.168.40.189/api/config

# 4. 门禁复验
python -m unittest discover -s tests -q
python scripts/measure_coverage.py --target recon-ai --min 80
python scripts/validate_skill.py && python scripts/check_glossary.py \
  && python scripts/check_token_budget.py --check
```

---

## 9. 门禁记录（阶段 8 / 9）

| 编号 | 检查项 | 依据 | 实测 | 判定 | 结论 |
|---|---|---|---|---|---|
| B3 | 语法与测试 | §2.1 | `py_compile` 全通过；`unittest discover` 185 用例 OK | 符合 | PASS |
| B4 | 证据契约 | §2.1 | 7 步各一份片段，三件套 7/7；`MANIFEST.jsonl` 7 行 | 符合 | PASS |
| B5 | 证据与 flag | §2.1 | 截图与命令同源可复现；flag 阶段不适用（§7-1） | 符合 | PASS |
| B6 | CI 门禁 | S1–S4 | `measure_coverage --target recon-ai --min 80` → 90.2% | 符合 | PASS |
| B7 | PyRIT 对象图 | §2.1 | 本包无 pyrit 导入（零第三方，AC-23 用例断言） | 符合 | PASS |
| AC-24 | 端到端 | 验收 | 本次运行退出码 0，7 片段 + 7 截图 + 清单 + 报告 | 符合 | PASS |
| AC-25 | S0 套件 | 验收 | 四个校验器全 PASS | 符合 | PASS |
| C4 | 产物预算 | AGENTS.md C4 | 单片段 1.4–3.2KB；报告 ≤3KB；证据集 472KB（本地，不入库） | 符合 | PASS |

**阶段结论**：`PASS`（不符合项 0）。**阶段 10 复审修复**：3 项硬违规（flag 段被表格破坏致 `report_exam` 解析失效／严格模式失败未影响退出码／CI 未编译新包）全部清零，并新增 2 个回归用例锁定该二项契约。**红→绿留痕**：首次运行 `recon-02` 因 `ProbeResult` 缺 `ok` 属性抛异常（已隔离并暴露缺陷）→ 补属性后转绿；覆盖率首测 77.4% 未达门槛 → 补 25 个单元用例后 90.2%；`test_ac22` 断言位置错误 → 移入临时目录作用域后转绿。
