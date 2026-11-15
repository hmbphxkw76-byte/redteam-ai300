# loot-manage 设计记录（codebase-design）

> **性质**：阶段 6 交付物（模块与接口设计）。输入：`skills/loot-manage/SKILL.md`、`docs/research/loot-manage-canonical.md`、#160 v2。
> **框架**：矩阵 ⑧（结构化凭据库 + 许可 AI，无攻击框架）；B7 为 N/A（不引入 PyRIT）。

## 1. 模块边界

单一包 `tools/loot_manage/`，三个职责层，依赖单向 `cli → registry`：

| 模块 | 职责 | 公开接口 |
|---|---|---|
| `registry.py` | 数据模型 + 解析 + 校验（纯函数，无 I/O 副作用） | `parse_registry(text) -> Registry`；`Registry.load(path)`；`validate(registry, root, require_loot=False) -> dict`；`append_entry(registry, row)`；`append_path(registry, line)` |
| `cli.py` | 薄封装：参数解析、退出码、JSON 输出 | `main(argv=None) -> int`（`init` / `validate` / `register`） |
| `__main__.py` | 入口 | `sys.exit(cli.main())` |

`registry.py` 不依赖 `cli.py`；`cli.py` 不直接解析 markdown（全部委托 registry）。

## 2. 数据模型

- `LootRow`：`id / type / content / host / evidence / timestamp / status / dual`（8 列一一对应）。
- `Registry`：`rows: list[LootRow]` + `attack_paths: list[str]` + `header: list[str]`。
- 表头匹配按**列名集合**（8 个规范化列名），非索引位置 → 列序调整不破坏解析（AC-12）。

## 3. 校验契约（`validate` 返回 dict）

```text
{
  "passed": bool,
  "checks": {"columns": bool, "rows": bool, "evidence": bool,
             "dual_channel": bool, "attack_path": bool, "ids": bool},
  "blocking": [str],   # 违反项（退出码 1）
  "flags": [{"id","host","panel","shot","consistent"}],  # 供 verify-evidence
  "missing": [str]
}
```

- `--json` 输出即 `verify-evidence` 的消费契约（AC-6）。
- 编号 `L-<n>` 唯一且格式合法（AC-10）；flag 行双通道含 `面板=`/`截图=`（AC-3）；有行时 `## 攻击路径` 非空（AC-4）。

## 4. Seam 清单（收敛自 v1 的 A/B/C）

| Seam | 位置 | 注入点 | 测试替身 |
|---|---|---|---|
| S1 解析/校验 | `registry.parse_registry` / `validate` | `text` 与 `root`（仓库根） | `tempfile` 临时登记簿 + 临时证据文件 |
| S2 登记 | `registry.append_entry` / `append_path` | `Registry` 实例 | 内存 `Registry` |
| S3 索引交接 | `cli.validate --json` | 标准输出 | 捕获 stdout |

**收敛结论**：v1 的「三 seam」保留语义，但物理上收敛为 2 模块（`registry` 核心 + `cli` 薄封装）。Seam 数量未增加，理由：接口少、实现深，降低后续变更面。

## 5. 依赖与约束

- **仅标准库**：`argparse` / `json` / `os` / `re` / `sys` / `datetime`；`requirements.txt` 不变。
- **零网络**：不向外部发送战利品内容（考试离线/保密硬约束，AC-11）。
- **不重复取证**：登记簿只存证据片段路径指针；截图捕获在本技能 Out of scope。
- **与既有工具同源**：术语 `_Avoid_` 判据复用 `GLOSSARY.md` 解析（不重实现）。

## 6. 被否决方案

| 方案 | 否决理由 |
|---|---|
| 仅保留 `printf` 模板、不写工具 | 手写易漂移，无法机读校验；与「可机读校验」质量门冲突 |
| 引入第三方表格库 | 违反零依赖与离线约束 |
| 把截图本体存入登记簿 | 违反 SKILL.md Out of scope 与单一事实源 |

## 7. 阶段 6 门禁记录（G0 · B2/B7/B8）

| 基线 | 判定 | 证据 |
|---|---|---|
| B2 术语 | 符合 | 用「战利品/登记簿/攻击路径/双通道」；无 `_Avoid_` |
| B7 PyRIT | 符合(N/A) | 无 `pyrit.orchestrator`/`*Orchestrator`/`AzureOpenAIChatTarget`；本包不依赖 PyRIT |
| B8 可追溯 | 符合 | 依赖单向 `cli→registry`；seam 与 v1 A/B/C 对齐 |

不符合项：0。结论：**PASS**。复验：`grep -nE "orchestrator|Orchestrator|AzureOpenAIChatTarget" docs/operations/loot-manage-design.md` → 无命中。
