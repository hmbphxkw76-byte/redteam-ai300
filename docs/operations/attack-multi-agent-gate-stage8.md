# attack-multi-agent — 阶段 8 `implement-spec` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.8 | `tools/attack_multi_agent/` 13 个模块（含 `__init__`）+ 5 个顶层示意脚本；a2a-01…08 每步 1:1 落盘 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/attack_multi_agent -t . -q` → Ran 57 tests, OK (skipped=1) | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B3 `python -m py_compile` 全模块与 5 脚本 → 通过；B4 证据统一委托共享证据工具；B7 懒导入 PyRIT | 替代（回溯） |

- 模块清单：`model`、`a2a`、`scanner`、`steps`、`grade`、`evidence`、`shot`、`transport`、`runner`、`cli`、`poc`、`pyrit_attack`。
- 顶层薄壳：`tools/msg_inject.py`、`agent_impersonate.py`、`memory_poison.py`、`context_poison.py`、`workflow_disrupt.py`，命令与 SKILL 攻击路径 A/B/C 字面一致。
- 编译复跑：`python -m py_compile tools/attack_multi_agent/*.py tools/msg_inject.py tools/agent_impersonate.py tools/memory_poison.py tools/context_poison.py tools/workflow_disrupt.py` → 退出码 0。
- 硬编码检查：命令模板使用主机/端口占位符，未写入真实目标地址或凭据。

**结论：PASS（回溯）**。证据指针：`tools/attack_multi_agent/`、`tools/msg_inject.py` 等 5 脚本、`scripts/tools_manifest.json:235-252`；提交 `a69be85`。
