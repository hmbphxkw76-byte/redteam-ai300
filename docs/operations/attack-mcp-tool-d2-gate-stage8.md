# 阶段 8 门禁记录 — implement-spec

> 变更域：D-2 服务生命周期与端口独占；规格 issue #464。

- **变更项**：三次提交——A `0df38d4`（start 幂等 + is_running）、B `d458f19`（所有权契约）、C `29736fe`（Windows 地址独占）；改动限 `poison.py` / `runner.py`。
- **判定**：PASS（编译 309 文件 0 失败；每条 AC 有实现位置；无硬编码凭据）。
- **复验**：`python scripts/check_tools_compile.py` → 失败 0。
- **结论**：最小切片，未触碰 STEP_IDS / 证据格式 / 公共 API。
