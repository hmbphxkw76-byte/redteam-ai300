# 设计记录 — foothold-traditional Ch9 A3/C2 加固（阶段 6）

> 单一事实源：判据见 `docs/research/foothold-traditional-ch9-hardening-canonical.md`；本文件只记模块/接口/依赖方向。

## 1. seam 决策
- 复用既有 `collect_evidence.py` 作为唯一证据出口（H-6）；新增 `emit_strict_evidence` 仅组装参数列表并调用注入的 `command.run`，不另建证据实现。
- 保留 `ch9_entry.py` 两个公开函数入口；返回类型由裸 dict 升级为 `TriadVerdict`（类型化，字段与 collect_evidence 参数同构）。

## 2. 模块与接口

| 模块 | 单一职责 | 公开接口 | 依赖 |
|---|---|---|---|
| `ch9_model` | 五值结论类型 + reason 枚举 + 指纹结构 | `TriadVerdict`, `OUTCOMES`, `VALID_REASONS` | 标准库 |
| `ch9_entry` | SSRF env harvest / GPU 立足点判据 | `ssrf_credential_entry`, `gpu_foothold_entry`（返回 `TriadVerdict`） | `ch9_model`, ctx.command |
| `ch9_evidence` | strict 证据参数组装与发射 | `emit_strict_evidence`, `build_evidence_argv` | `ch9_model`, ctx.command |
| `ch9_runner` | 两步编排 + 证据附着 | `run_ch9` | 上述三者 |

## 3. 依赖方向（无环）
```
ch9_runner → ch9_entry → ch9_model
           → ch9_evidence → ch9_model → (标准库)
```
`ch9_model` 不 import 本项目任何模块；证据 CLI 路径由 `ch9_evidence` 以仓库相对路径解析（无硬编码盘符）。

## 4. 测试替身
`FakeCommand`（argv→CommandResult）离线；断言只看 `TriadVerdict` 字段与 `build_evidence_argv` 返回的列表，不测私有函数。

## 5. 权衡与否决
- 否决：直接改 `scripts/measure_coverage.py` / `scripts/tools_manifest.json` 增 target——这两文件在其它 worktree 有 staged 改动（ADR-0006 共享冲突）；改用独立脚本 `scripts/verify_ch9_ft_coverage.py` 复用 `measure_coverage.measure()`，零共享文件改动。
- 否决：在 GPU 步骤执行 CVE 载荷（P-4，属 attack-infra ch9-gpu）。
- 否决：明文落 output（P-1）。

## 6. 覆盖率门槛
本轮 ≥90%（高于 CI 全局 80%）；`verify_ch9_ft_coverage.py --min 90` 复现，复用 tracer 逻辑不自写（C1）。

## 7. ADR / 冲突标注
无新增 ADR；三层隔离由 worktree 与 push 前锁检查承载；共享文件（GLOSSARY/budget/manifest/ci.yml/collect_evidence/契约）本分支零 delta。
