# verify-evidence 模块与接口设计（codebase-design）

> **阶段**：主线 阶段 6 · **输入**：规格 v2（`docs/specs/verify-evidence-spec-v2.md`）、工单 #206–#212、调研缺口 G1–G7
> **结论**：保持单模块 `tools/verify_evidence.py`，内部按 S-1…S-4 分层；新增依赖仅限既有纯函数（登记簿与术语检查器），依赖方向单向。

---

## 1. 模块职责与边界

| 层 | 职责 | 明确不做 |
|---|---|---|
| S-1 输入归一 | 把 payload JSON、登记簿 + 片段目录归一为统一输入字典（`report_md`/`appendix_md`/`osid`/`fragments`/`panel_flags`/`pdf_path`/`zip_path`/`exam_end_at`/`submit_at`） | 不校验产物内容合法性（留给判据层） |
| S-2 判据 | 九项独立判定，各返回 `(ok, blocking, missing, pending)` 四元组 | 不读写文件、不调子进程（外部能力一律走 S-3） |
| S-3 外部工具 | 技能校验结论、废弃术语表、文件 `stat`（存在/体积）、当前时间 | 不缓存跨调用的可变状态 |
| S-4 输出 | 版本化 JSON + 人读摘要 + 退出码 | 不改写任何产物 |

## 2. 公开接口（模块级，全部可被下游调用）

| 接口 | 签名（语义） | 输入 | 输出 | 错误行为 |
|---|---|---|---|---|
| `SCHEMA_VERSION` | 常量 | — | `"1.0"` | — |
| `SCORED_TARGETS` | 常量 | — | 8 个计分目标 → 分值（AI 15 / 传统 10 / 独立 15 / 域控 5） | — |
| `Toolchain` | 工具链对象 | 技能校验/技能元信息/术语表/文件 stat/归档加密 | 实例 | 能力缺失时记 `missing` 注记，不抛异常 |
| `load_payload` | 读 JSON 载荷 | 路径 | 输入字典 | 文件缺失/JSON 非法 → `ValueError`（CLI 转退出码 2） |
| `from_loot` | 由登记簿构造输入 | 登记簿路径、片段目录、报告/附录/分值表 | 输入字典（与 `load_payload` 同形） | 登记簿缺失 → `ValueError` |
| `from_fragments` | 由一批片段文件构造输入（US-03） | 片段目录、报告/附录/分值表/面板值 | 输入字典 | 目录不存在 → `ValueError` |
| `verify` | 执行九项判定 | 输入字典 + `require_artifacts` + 可选 `Toolchain` | 结果字典（9 checks + 分级列表 + 结论三元组） | 不抛异常，全部落到 `blocking`/`missing`/`pending` |
| `render_summary` | 人读摘要 | 结果字典 | 文本（阻断数/缺失数/核实闸数 + 逐条） | 空输入返回空串 |
| `main` | CLI | argv | 退出码 0/1/2 | 用法错误 2 |

## 3. 依赖方向（单向，无环）

```
main → verify → check_vrf01..08 / check_proof_single → Toolchain（注入）
                                    └→ loot_manage.registry.fragment_pieces（纯函数，复用判据）
                                    └→ scripts/check_glossary.parse_glossary（纯函数，术语同源）
```

- 不得反向：登记簿与术语检查器**不**感知校验器。
- `tools/report_exam/package.py` 位于下游，只调 `verify`，不触内部函数。

## 4. seam 与注入点（4 处，与规格 v1 §4 一致）

| seam | 位置 | 注入方式 | 测试替身 |
|---|---|---|---|
| S-1 | `load_payload` / `from_loot` | 参数（路径） | 临时目录夹具 |
| S-2 | `check_*` 系列 | 直接调用 | 单元断言 |
| S-3 | `Toolchain` | 构造参数默认值 | 假校验器 / 假术语表 / 假 stat / 假时钟 |
| S-4 | `verify` 返回值 + `render_summary` + 退出码 | 消费方 | 键集断言 |

## 5. 权衡与被否决方案

| 方案 | 结论 | 理由 |
|---|---|---|
| 拆为 `tools/verify_evidence/` 包 | **否决** | CI `py_compile` 路径与 `tools/report_exam/package.py` 的 `spec_from_file_location` 均绑定单文件路径；拆包需同改 CI 与下游，影响半径超出本技能 |
| 判据层内直接 `subprocess` 调 `check_glossary.py` | **否决** | 进程开销 + 输出文本解析易漂移；改为 import 同源 `parse_glossary`（术语判据同源，C1） |
| 24h 窗口降级为警告 | **否决** | S3 明示超时自动不及格（快照 `#L74`），必须阻断 |
| 截图 OCR 取 flag 值 | **否决** | 非官方要求，成本高且易误判；改「访问证明同屏」文字断言 + 人工兜底（VG-2） |
| 新增第二套三件套判据 | **否决** | 违反 C1；委托 `registry.fragment_pieces` |

## 6. 与 ADR 的关系

无冲突。`ADR-0002`（评分杠杆）体现为 `SCORED_TARGETS` 分值表；`ADR-0004`（PyRIT 锁版）对本技能为「零依赖」形式。
