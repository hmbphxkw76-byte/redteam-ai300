# 设计记录 — loot-manage Ch9 B5 六服务指纹加固（阶段 6）

> 判据事实源：`docs/research/loot-manage-b5-hardening-canonical.md`；本文件只记模块/接口/依赖方向。

## 1. seam 决策
- 复用既有 `registry`（8 列 schema / `append_row` / `validate`）为唯一登记出口；不新增列、不改判据（B5-4）。
- 保留 `ch9_cloud.py#register_cloud_fingerprint` 公开名与旧参数顺序；service 以可选参数追加，返回类型升级为 `CloudFingerprintVerdict`（dict 兼容 shim 零回归）。

## 2. 模块与接口

| 模块 | 单一职责 | 公开接口 | 依赖 |
|---|---|---|---|
| `ch9_b5_model` | 类型化结论 + 六服务枚举 + 来源映射 | `CloudFingerprintVerdict`, `CLOUD_SERVICES`, `SOURCES`, `REASONS` | 标准库 |
| `ch9_cloud` | 六服务指纹登记（重写加固） | `register_cloud_fingerprint`, `fingerprint_text`, `next_id` | `ch9_b5_model`, `registry` |
| `ch9_b5_trace` | 下游无损回溯探针 | `trace_from_loot` | `verify_evidence`, `registry` |

## 3. 依赖方向（无环）
```
ch9_cloud → ch9_b5_model → (标准库)
          → registry → (标准库)
ch9_b5_trace → verify_evidence → registry（既有消费路径，不改）
```
`ch9_b5_model` 不 import 本项目模块。

## 4. 测试替身
临时目录 + 真实 `collect_evidence` 片段文件测 `verify_evidence.from_loot` 无损回溯（AC-06），不用 mock 判据。

## 5. 权衡与否决
- 否决：改 `scripts/tools_manifest.json`/`measure_coverage.py` 注册 target——共享文件在其它 worktree staged（ADR-0006）；用独立脚本复用 tracer。
- 否决：新增登记簿列或改 8 列 schema（B5-4/P-4）。
- 否决：在登记模块调用云 API（R-1/D-1）。

## 6. 覆盖率
≥90%；`verify_lm_b5_coverage.py --min 90` 复现，复用 `measure_coverage.measure()`（C1）。

## 7. 冲突标注
共享六项（GLOSSARY/check_token_budget/measure_coverage/tools_manifest/ci.yml/collect_evidence 契约）本分支零 delta。
