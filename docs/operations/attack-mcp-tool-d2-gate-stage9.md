# 阶段 9 门禁记录 — tdd

> 变更域：D-2 服务生命周期与端口独占；规格 issue #464。

- **变更项**：新增 7 条用例（T1 幂等/状态、T2 二次监听、T3 注入已启动、T4 注入未启动、T5 端口冲突降级、T6 重绑窗口、T7 全量回归）；红→绿留痕三段：
  - T1 红：`AttributeError: 'PoisonedMcpServer' object has no attribute 'is_running'`
  - T3 红：`AssertionError: False is not true : 编排层不得关闭注入方持有的实例`
  - T2 红：`AssertionError: OSError not raised`
- **判定**：PASS（全量 1693 例 0 失败 2 跳过；覆盖率 94.4% ≥ 90%（含阶段 10 复查补测））。
- **复验**：`python -m unittest discover -s tests -t . -q`；`python scripts/measure_coverage.py --target attack-mcp-tool --min 90`。
- **结论**：每条 AC 有对应测试；红阶段有真实失败输出。
