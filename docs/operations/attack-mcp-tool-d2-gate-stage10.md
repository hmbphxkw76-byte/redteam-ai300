# 阶段 10 门禁记录 — code-review（双轴）

> 变更域：D-2；固定点 `e55ae64`；diff = `0df38d4` / `d458f19` / `29736fe`。

## 双轴结论

| 轴 | 发现数 | 最严重项 | 硬违规 |
|---|---|---|---|
| Standards | 6（均判断项） | 启动契约在两处表述不一致（C1 单一事实源） | 0 |
| Spec | 4（含 1 项实现有误） | `ensure_server` 先登记后启动，失败后留死实例 | 1（实现有误） |

- **Standards 轴**：无硬违规。判断项：docstring 契约表述重复；`started_server` 先于 `start()` 赋值；`server_started` 只写不读；`daemon_threads` 与父类重复；`_BoundServer` 命名不揭示独占语义；两个测试 helper 同形。
- **Spec 轴**：AC-06/07 用例不到位（仅线程名断言、仅 stub 冲突）；AC-04 未跑完整路径；`ensure_server` 早退判据为 `started_server is not None`，启动失败后仍返回未监听实例。

## 修复（提交 `08d6b85`）

- `ensure_server` 改为「先启动后登记」，失败不留就绪态；补断言「后续步骤不得复用 `:0/mcp`」。
- `_BoundServer` → `_PortExclusiveServer`；删除重复 `daemon_threads`。
- 补 AC-04（完整路径 + 注入实例存活）、AC-06（mock 校验自建实例 start/stop + 端口释放）、AC-07（真实占端口，非 stub）。

## 判定

- 判定：PASS（硬违规已清零；判断项中的 C1 表述重复已随 docstring 重写消解）。
- 复验：`python -m unittest discover -s tests -t . -q` → 1693 例 OK；`measure_coverage --target attack-mcp-tool --min 90` → 94.4%。
- 结论：双轴并列、结论完整、硬违规 0。
