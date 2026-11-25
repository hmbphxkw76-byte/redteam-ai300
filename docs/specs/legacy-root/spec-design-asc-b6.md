# 设计记录 — attack-supply-chain Ch9 B6 边界加固（阶段 6）

> 判据事实源：`docs/research/attack-supply-chain-ch9-b6-hardening-canonical.md`；本文件只记模块/接口/依赖方向。

## 1. seam 决策
- 复用 `collect_evidence.py` 为唯一证据出口（B6-4）；新增 emitter 只组装 argv 并经注入 `command.run` 执行。
- 保留 `ch9_boundary.classify()` 公开名；返回类型升级为 `BoundaryVerdict`，附 dict 兼容 shim 保证轻量版零回归。

## 2. 模块与接口

| 模块 | 单一职责 | 公开接口 | 依赖 |
|---|---|---|---|
| `ch9_boundary` | 类型化边界判定 + 显式转交规则 | `BoundaryVerdict`, `classify`, `OWNERS`, `REASONS` | 标准库 |
| `ch9_boundary_evidence` | strict 证据 argv + 发射 | `build_evidence_argv`, `emit_strict_evidence` | `ch9_boundary`, ctx.command |
| `ch9_boundary_runner` | 判定 + 证据附着 | `run_boundary` | 上述两者 |

## 3. 依赖方向（无环）
```
ch9_boundary_runner → ch9_boundary → (标准库)
                    → ch9_boundary_evidence → ch9_boundary → (标准库)
```
`ch9_boundary` 不 import 本项目任何模块；转交目标以字面 `路径#锚点` 字符串存在（非 import，避免跨技能耦合）。

## 4. 测试替身
`FakeCommand` 离线；断言只看 `BoundaryVerdict` 字段与 argv 列表。

## 5. 权衡与否决
- 否决：改 `scripts/tools_manifest.json` / `measure_coverage.py` 注册 coverage target——两文件在其它 worktree 有 staged 改动（ADR-0006）；改用独立脚本复用 `measure_coverage.measure()`。
- 否决：在边界模块执行 Sidecar 拦截或投毒本体（P-4）。
- 否决：裸 dict 返回（AC-05 要求 frozen dataclass）。

## 6. 覆盖率门槛
≥90%；`verify_asc_b6_coverage.py --min 90` 复现。

## 7. 冲突标注
共享六项（GLOSSARY/check_token_budget/measure_coverage/tools_manifest/ci.yml/collect_evidence 契约）本分支零 delta。
