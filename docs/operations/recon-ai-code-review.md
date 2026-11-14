# recon-ai 双轴代码审查报告（阶段 10）

> **基线** `git merge-base origin/main HEAD` = `d83dc32`（本次改动前主干）
> **审查对象** 新增 `tools/recon_ai/`（10 模块）、修改 `tools/collect_evidence.py`、`scripts/measure_coverage.py`、`.github/workflows/ci.yml`、`skills/recon-ai/SKILL.md`、`GLOSSARY.md`；新增 3 份文档、2 份测试
> **方式** 两轴独立并行审查（Standards 轴 / Spec 轴），不合并、不重排；逐条分类为「硬违规 / 判断项」

---

## 1. Standards 轴（编码规范与工程质量）

- 发现数：**27**（硬违规 3 / 判断项 24）
- 最严重项：证据格式变更破坏下游解析（见 S-H1）

| 编号 | 位置 | 问题 | 分类 | 处置 |
|---|---|---|---|---|
| S-H1 | `tools/collect_evidence.py` flag 段 | 改为表格后 `report_exam.index.parse_fragment` 只能解析到表头，双通道比对恒为假 → 报告侧静默失去 flag 校验 | 硬违规 | **已修**：恢复 fenced 原值块（契约），双通道明细表置于其后；新增回归用例 `test_flag_fragment_reparsed_by_report_exam` |
| S-H2 | `tools/recon_ai/runner.py`、`cli.py` | `--strict` 失败仅记 warning，进程仍返回 0 → C8 质量门可被绕过 | 硬违规 | **已修**：新增 `quality_failures` 通道，`cli` 以其决定退出码 1；新增用例 `test_missing_screenshot_surfaces_as_quality_failure` |
| S-H3 | `.github/workflows/ci.yml` | S1 `py_compile` 未覆盖新包，6 个模块在语法门禁之外 | 硬违规 | **已修**：编译目标追加 `tools/recon_ai/*.py` |
| S-J1 | `model.py` | 截断提示声称「全文见留存入径」，实际未持久化原文 | 判断项 | **已修**：改为「完整响应 N 字节，命令可重跑取全文」 |
| S-J2 | `transport.py` | docstring 声称禁重定向，实际跟随 30x | 判断项 | **已修**：`_NoRedirect` 处理器显式拒绝跟随（探测不外溢） |
| S-J3 | `probes.py` | 判据文案称「回退→不存在」，实现从不返回 ABSENT | 判断项 | **已修**：探测级 `ProbeResult.existence` 三值落地，判据引用之 |
| S-J4 | `inventory.py` | `step_id` 由类别下标二次推导，与 `STEP_SPECS` 构成双源（C1） | 判断项 | **已修**：改为 `{spec.category: spec.step_id}` 映射 |
| S-J5 | `probes.py` | 端口清单在注记中硬编码，与主动请求声明重复 | 判断项 | **已修**：`_port_list()` 从 `active_requests` 生成 |
| S-J6 | `cli.py` | 片段文件名由字符串拼接，与 `EvidenceWriter` 漂移 | 判断项 | **已修**：改用 `report.evidence_paths` 反查 |
| S-J7 | `runner.py` | `req.collect` 解析异常被 `except: pass` 吞掉 | 判断项 | **已修**：入 `warnings` |
| S-J8 | `model.py` / `inventory.py` | `credential_hint` 从未被调用，SKILL.md 的指纹规则未落地 | 判断项 | **已修**：从 `set-cookie` 提取并压缩为 `Bearer-<8>` |
| S-J9 | `runner.py` 报告 | 复核命令把 JSONL 喂给 `verify_evidence --payload`（必然解码失败） | 判断项 | **已修**：改为 `cli.py inventory --path` |
| S-J10 | `docs/.../recon-ai-design.md` | 依赖表、接口名、截断口径与代码不一致 | 判断项 | **已修**：v1.1 逐行对齐实际导出与依赖 |
| S-J11 | `__init__.py` | docstring 称「仅两个入口」但导出 9 个符号 | 判断项 | **已修**：改为「深模块 + 2 个主入口」表述 |
| S-J12 | `collect_evidence.py` | 共享工具硬编码「分析注记（recon-ai）」标签与 attack 场景不适用的措辞 | 判断项 | **已修**：标签改「（可选）」，脚本说明中性化 |
| S-J13 | `collect_evidence.py` | 废弃术语扫描遗漏 `script_src`/`flag_panel`/`flag_shot` | 判断项 | **已修**：纳入扫描范围 |
| S-J14 | `collect_evidence.py` | 清单构造耦合 argparse `Namespace`，无法按 API 复用 | 判断项 | **已修**：改显式关键字参数 |
| S-J15 | 多模块 | 死代码（`signature_summary`/`specs_for`/`load_collector`/`_ok_or_unknown`）与未使用导入 | 判断项 | **已修**：全部删除，`grep` 0 命中 |
| S-J16 | `tests/` | 空断言（`":{host}:"` 只对被动请求检查；`1-65535` 永不命中）、AC-23 黑名单式判定 | 判断项 | **已修**：改为 tag 过滤、端口上限断言、`sys.stdlib_module_names` 反向判定 |
| S-J17 | `tests/test_recon_ai_units.py` | 依赖回环 HTTP 服务与「1 号端口关闭」假设 | 判断项 | **接受**：端口 0 自动分配 + 2s 超时，沙箱内稳定；保留以覆盖真实 urllib 分支 |
| S-J18 | `tests/test_recon_ai.py` | AC-22 通过 monkeypatch 全局 `JUDGES` 注入故障（白盒） | 判断项 | **接受**：故障注入无外部等价手段，已加注释说明用途 |
| S-J19 | `runner.py` | AI 日志版式在编排层拼装，而格式应由共享收集器拥有 | 判断项 | **留待后续**：`--ai-log` 已支持结构化传入，版式细化需与 report-exam 的附录格式一并设计，避免二次改动 |
| S-J20 | `probes.py` | 实验面 ID（`MM_04/MM_05/DE_01/MCP_01`）硬编码 | 判断项 | **部分修**：`--lab` 覆盖主聊天面；其余实验面 ID 属目标特定事实，改配置化需引入外部 profile 文件（超出本切片范围），已在调研文档登记为环境事实 |

---

## 2. Spec 轴（规格忠实度）

- 覆盖：25 条 AC，首轮**覆盖 20 / 缺口 5**；修复后**覆盖 25 / 缺口 0**
- 最严重项：SKILL.md 自身指令与「不支持的操作」冲突（全端口扫描、字典爆破）

| AC | 首轮缺口 | 处置 | 复验 |
|---|---|---|---|
| AC-01 | 判据 `grep "^profile: passive$"` 与产物格式不符 | 证据头固定写 `**执行分级**：`passive``，用例断言该行 | `test_ac01` |
| AC-03 | JSON 只有 `generated_at`，无 `timestamp` | 清单 JSON 增加 `timestamp` 别名（与 `generated_at` 等值） | `test_ac03` |
| AC-04 | 只测了 `is_spa_fallback`，未断言「回退→不存在」 | 新增探测级 `existence` 三值，用例断言 `/v1/models` 为 ABSENT、超时为 UNDETERMINED | `test_ac04` |
| AC-10 | 清单无 `phase` 字段，用例断言的是 `request_id` | `Asset.phase` 作为可选附加字段，取 recon-02 的 SSE `phase=3` | `test_ac10` |
| AC-15 | 只查两个固定串，且 sha256 会被「32 位以上串」误命中 | 改为正则判明文凭据特征（Bearer/sk-/cookie），并断言指纹存在 | `test_ac15` |

#### 越界核查

1. SKILL.md 与边界冲突：原文 `nmap -sC -sV -p-`（全端口）与 `ffuf ... mcp-wordlist.txt`（字典扫描）与「不支持的操作」2、3 条矛盾 → **已修**：改为被动优先 + `--profile active` 定向端口（≤8）；recon-06 改为单次语义探测，`ffuf` 降级为授权后可选项。
2. B7 禁止名（`pyrit.orchestrator` / `*Orchestrator` / `AzureOpenAIChatTarget` / `XpiaAttack`）：技能、实现、测试、产物 **0 命中**。
3. 废弃术语（`GLOSSARY.md` 标注 `_Avoid_` 的旧称，涉及「演练目标」「诱饵机」两词的俗名）：技能正文、实现、测试、产物 **0 命中**；`check_glossary.py` 29 项全过。

---

## 3. 复跑结果（阶段 10 门禁）

| 检查 | 命令 | 结果 |
|---|---|---|
| 语法 | `python -m py_compile tools/recon_ai/*.py tools/collect_evidence.py` | 通过 |
| 全量测试 | `python -m unittest discover -s tests` | 187 用例 OK |
| 覆盖率 | `python scripts/measure_coverage.py --target recon-ai --min 80` | 91.1% |
| 覆盖率（全量） | `python scripts/measure_coverage.py --target all --min 80` | 90.9% |
| 技能解剖 | `python scripts/validate_skill.py` | 16 技能全合规 |
| 术语 | `python scripts/check_glossary.py` | PASS（29 项 0 命中） |
| 预算契约 | `python scripts/check_token_budget.py --check` | PASS（14 锚点齐全） |

**结论**：硬违规 **0**；判断项已处置 18 项、接受 2 项、留待后续 1 项、部分修 1 项。阶段 10 `PASS`。
