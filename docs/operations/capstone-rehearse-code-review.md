# capstone-rehearse 双轴代码审查（阶段 10）

> **固定基线**：`git merge-base origin/main HEAD` = `20ce2eb`；审查对象 `20ce2eb..b778ec6`（28 文件 / 1879 行新增，diff 非空）。修复以第二个 Conventional Commit 落地。
> **方法**：两个只读子 agent 并行独立审查，两轴报告并列、不合并、不重排；逐条分类「硬违规 / 判断项」；硬违规清零后复跑门禁套件。

## 1. 两轴并列结论

| 轴 | 发现数 | 硬违规 | 判断项 | 最严重项 | 处置后硬违规 |
|---|---|---|---|---|---|
| **Standards**（编码规范） | 5 | 1 | 4 | `docs/specs/capstone-rehearse-spec-v1.md:92` MD012 连续空行，CI S1 markdownlint 阻断 | **0** |
| **Spec**（规格忠实度） | 8 | 1 | 7 | `tools/capstone_rehearse/walk.py:23-36` `_chain` 自写三件套真值判据，未复用 `registry.fragment_pieces`，违反 C1 / AC-03 | **0** |

Spec 轴确认：**规格覆盖矩阵 25/25 无遗漏**；seam「2 新 + 复用 1」与阶段 2 用户核对结论一致且数量未增；四件产出、VG-1…VG-6、演练标注、`-real` 过滤齐全；未见「未演练写成已通过 / 建议伪装实测 / 超时隐瞒 / 真实考试利用」；依赖方向单向、既有模块不反向依赖；共享文件未改。

## 2. 逐条发现与分类

### Standards 轴

| # | 位置 | 描述 | 分类 | 处置 |
|---|---|---|---|---|
| S-1 | `spec-v1.md:92` | 末尾 2 个连续空行触发 MD012，S1 实跑确认 `1 issue` | 硬违规 | 删除多余空行 |
| S-2 | `test_capstone_rehearse.py:156-161,225-231,240-245` | AC-16/23/25 读源码/文档结构，属扫描型断言 | 判断项 | 改进项：AC-23/25 本身即源码/文档验收，扫描为合理判据 |
| S-3 | `test_capstone_rehearse.py:21; cli.py:83` | 依赖 `report_exam._types` / `report_exam.index` 既有契约模块 | 判断项 | 改进项：属既有判据复用；新增替身 seam 会违反阶段 2 结论 |
| S-4 | `spec-v1 7982/8000`、`spec-v2 9984/10000`、`gate-stage9 1999/2000` | C4 余量极小（修复后 v1 为 7981/8000） | 判断项 | 改进项：后续编辑须先复验 `--artifact` |
| S-5 | `ci.yml:55`（未改） | 新包未列入 S1 `py_compile` 路径 | 判断项 | 改进项：按 ADR-0006 不改共享文件；S2 `unittest discover` 与覆盖率测试已覆盖语法 |

### Spec 轴

| # | 位置 | 描述 | 分类 | 处置 |
|---|---|---|---|---|
| P-1 | `walk.py:23-36` | `_chain` 自写真值判据且比既有更宽（「（未提供）」亦判真） | 硬违规 | 改为委托 `registry.fragment_pieces(Fragment.raw)` |
| P-2 | `test_capstone_rehearse.py:44-51` | 替身未复用既有 `MemoryEvidenceSource` | 判断项 | **已顺带改进**：`CountingSource` 包装既有 adapter |
| P-3 | `walk.py:69`、`clock.py:37` | 接口多出 `closed_gates` / `Clock.measured()` | 判断项 | 改进项：分别为 AC-17 取证输入与 AC-08 实测字段所需；VG-5 张力由报告免责声明承接 |
| P-4 | `test_capstone_rehearse.py:181-182` | AC-14 `assertNotIn("checks", …)` 为空断言 | 判断项 | 改进项：后续补只读契约测试 |
| P-5 | `test_capstone_rehearse.py:156-161` | AC-16 源码白名单仅扫 `walk.py` | 判断项 | **已顺带改进**：扩展到 6 个核心模块，排除合法的证据生产端 |
| P-6 | `test_capstone_rehearse.py:233-238` | AC-24 仅实跑一类产物上限 | 判断项 | 改进项：门禁已实跑六类 `--artifact` |
| P-7 | `walk.py:62-63` | AC-06 超盒仅追加「须记录」建议，无独立放弃理由字段 | 判断项 | 改进项：报告 §2 显示压缩建议，时间盒行含耗时与关键节点 |
| P-8 | 核对一致项 | seam / 四件产出 / 核实闸 / 隔离 / 依赖方向 / 无假称 | 确认项 | 无缺陷 |

## 3. 硬违规修复清单与复验

| 编号 | 修正文件与动作 | 复验命令 | 复验结果 |
|---|---|---|---|
| S-1 | `docs/specs/capstone-rehearse-spec-v1.md` 末尾删 1 空行（7982B→7981B，语义不变） | `npx markdownlint-cli2 <全部新增 md>` → `0 issues`；`--artifact spec-v1` → 7981/8000 PASS | PASS |
| P-1 | `walk.py` 导入并委托 `fragment_pieces(raw)`；测试夹具补 `Fragment.raw`、包装 `MemoryEvidenceSource`；`implementation.md` AC-03 行同步 | `python -m unittest tests.test_capstone_rehearse ...` → 35 OK；`grep fragment_pieces walk.py` → 3 处 | PASS |

两项修复均不改变 v1/v2 规格语义与验收条件；历史门禁记录按留痕语义保留原实测值（v1 7982B 为阶段 2 当时值）。

## 4. 门禁套件复跑（硬违规清零后）

| 检查 | 命令 | 结果 |
|---|---|---|
| B1 | `python scripts/validate_skill.py` | PASS（16 技能） |
| B2 | `python scripts/check_glossary.py` | PASS（50 废弃术语） |
| B3 | `python -m py_compile tools/capstone_rehearse/*.py`；`python -m unittest discover -s tests` | OK；`Ran 652 … OK (skipped=2)` |
| B4 | `--emit-evidence` 重生成 6 份片段 | 三件套齐全 6/6 |
| B5 | 片段 flag 双通道 | 「否 / 未提供」，不伪造 |
| B6 | `measure_coverage.measure` | 90.1%（421/467 行）≥80 |
| B7 | 源码扫描 `import pyrit` / 旧名 | 0 命中 |
| B8 | 固定点 diff、issue #233 互链、一手来源锚点 | 完整 |
| S1 markdownlint | `npx markdownlint-cli2 <新增 md>` | 0 issues |

## 5. 结论

两轴报告各自结论完整；每条发现带文件位置与分类；**硬违规 0**；规格覆盖矩阵 25/25 无遗漏；门禁套件全绿。判断项共 9 项记录为改进项（其中 2 项已顺带改进），不阻断交付。**PASS**，进入阶段 11。
