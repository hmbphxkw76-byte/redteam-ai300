# verify-evidence 双轴代码审查（阶段 10）

- **基线**：`git merge-base` with `origin/main` = `6704ffb` → diff 覆盖 19+ 文件（实现 / 测试 / 规格 / 门禁记录）
- **方法**：两轴分离 —— Standards（写得对不对）与 Spec（做的是不是要求的）；Spec 轴由独立只读评审（Explore 子 agent）执行，Standards 轴以命令化检查 + 人工复核实跑
- **结论**：Standards 硬违规 0 / 判断项 4；Spec 硬违规 8（已全部修复）/ 判断项 4（转跟进）

---

## 1. Spec 轴（规格忠实度）

| # | AC/SKILL | 发现 | 分类 | 处置 |
|---|---|---|---|---|
| S-1 | AC-07 | 访问证明把整段片段原文（含命令块）当判定文本，命令里出现 `whoami` 即误判「同屏」 | 硬违规 | 改为只取「截图」节内联记录或显式 `access_proof` 字段 |
| S-2 | AC-01 | `from_loot` 固定 `report_md=""`，而 SKILL 声称两入口等价——实际 `--from-loot` 永远过不了 vrf-01/02/06 | 硬违规 | 新增 `--report`/`--appendix` 参数；SKILL 更正为「共用判定层，报告侧需显式给入」 |
| S-3 | AC-01 | 等价性用例两侧都传空报告，退化为「都失败即相等」 | 硬违规 | 用例改为填充报告 + 分值表，并加「只给登记簿必然阻断」反例 |
| S-4 | AC-10 | 「归档无密码」（§6.4.2「禁止」）无任何判定，`check_naming_and_size` 注释却说由打包侧保证 | 硬违规 | 新增 `Toolchain.archive_encrypted()`（7z `l -slt` 读 `Encrypted`），加密即阻断；工具缺失记 `NOTE-8` |
| S-5 | AC-11 | `_parse_time` 解析失败静默返回 None，畸形时间戳等同于「未提供」，窗口被绕过 | 硬违规 | 改为抛 `ValueError`；`verify()` 捕获后按「输入非法」阻断 |
| S-6 | AC-04 | vrf-02 首行 `INVENTORY_ANCHOR` 短路使「标题存在即通过」，与 §6 VG-1「不依赖标题」自相矛盾 | 硬违规 | 删除该常量与短路；无分值表时要求 8 个主机键全部出现于报告，缺则阻断 |
| S-7 | AC-17 | 无分值表分支完全不受覆盖（假盲区），且键集在 `report_exam/_types.py` 与校验器各写一份（C1） | 硬违规 | 键集与分值多重集收敛到 `tools/scored_targets.py`，两侧引用；新增一致性用例 |
| S-8 | SKILL vrf-proof | SKILL「提交次数 == 1 方可通过」与「未取分缺失不阻断」冲突，实现取 ≤1 | 硬违规 | SKILL 改为「不得超过 1 次；== 1 通过 / == 0 按豁免记录 / > 1 阻断」，质量门同步 |
| S-9 | AC-07 | 访问证明缺失仍记 `missing` 而非阻断（评审建议） | 判断项 | 保留 `missing` 但不足以掩盖：纯图片截图机器不可判（VG-2），改记 `NOTE-7` 并在规格定义 NOTE 口径；显式阻断留给「有同屏文本但缺 token」 |
| S-10 | AC-11 | 窗口时间缺失仍记 `missing`，理论上可不给时间规避 24h（评审建议） | 判断项 | 保留 `missing` + `NOTE-5`：考试结束时间是考生已知事实，改成 pending 会让「产物齐全但未填时间」永远不可提交，与 §6.4 的可操作性冲突；风险由 SKILL 人工复核条款兜底 |
| S-11 | §6 | 实现引入 VG-5/6/7，规格只定义 VG-1…VG-4（命名空间污染） | 判断项 | 全部改名为 `NOTE-5`…`NOTE-8`，规格 §6 增补 NOTE 口径段 |
| S-12 | AC-06 | `from_loot` 把同日登记簿的「面板=」值同时用作报告侧 flag，双通道比对退化为自比 | 判断项 | 登记簿不存报告侧值，机器无法独立取证；已在规格标注限制，转跟进 issue（需 `--report` 交叉检索 flag 文本） |

## 2. Standards 轴（编码规范）

| # | 位置 | 发现 | 分类 | 处置 |
|---|---|---|---|---|
| T-1 | `scripts/measure_coverage.py` | 与 origin/main 的 attack-rag 目标冲突，合并后残留冲突标记 | 硬违规 | 取并集（保留 attack-rag + verify-evidence 两目标），`py_compile` 复验 |
| T-2 | `report_exam/package.py` | 载荷丢弃 `Fragment.raw`，导致登记簿三件套判据在真实链路永不触发（与 AC-17 矛盾） | 硬违规 | 载荷补 `raw` 字段 |
| T-3 | `Toolchain.avoid_terms` | 术语表读取异常时返回 `[]`，vrf-08 静默通过（fail-open） | 硬违规 | 返回 `None`，判据层据此阻断 |
| T-4 | `check_naming_and_size` / `check_proof_single` | 阻断消息缺 `vrf-07` / `proof-single` 前缀，计数器与定位失效；局部变量名为 `missing` 与分级术语重名 | 硬违规 | 统一前缀与 `problems` 命名 |
| T-5 | `Toolchain.now()` / `_result(ok=None)` | 死代码 | 判断项 | 删除 |
| T-6 | `TOTAL_POINTS = 100` 与 `POINT_PATTERN` 双写 | 同口径两处硬编码，改一处即失配 | 判断项 | 由多重集求和推导并收敛到 `tools/scored_targets.py` |
| T-7 | `check_vrf03` | 循环内重复调用 `_scored()`（O(n²)）且用 `f in _scored(...)` 判等 | 判断项 | 改 `id()` 集合一次判定 |
| T-8 | AC-17 用例 | 仅断言替身被调用（实现细节），无行为断言（评审建议） | 判断项 | 保留调用计数（规格明确要求判据同源），另补键集单一事实源用例 |

## 3. 修复后复验

| 项目 | 命令 | 结果 |
|---|---|---|
| 语法 | `python -m py_compile tools/verify_evidence.py tools/scored_targets.py report_exam/package.py scripts/measure_coverage.py` | 全部通过 |
| 全量测试 | `python -m unittest discover -s tests` | `Ran 521 tests ... OK (skipped=2)` |
| 覆盖率 | `python scripts/measure_coverage.py --target verify-evidence --min 80` | 420/455 = **92.3%**（门槛 80） |
| 技能解剖 | `python scripts/validate_skill.py` | PASS（16 技能） |
| 术语 | `python scripts/check_glossary.py` | PASS（50 术语） |
| 预算 | `python scripts/check_token_budget.py --check` | GLOSSARY 16442/16500 OK，14 锚点齐 |

## 4. 残留判断项（不阻断交付，已转跟进）

- J-1：`from_loot` 双通道自比（S-12）——需引入报告侧 flag 交叉检索，转 issue。
- J-2：计分「已取分」判定用 flag 非空，未消费登记簿 `状态` 列——与 `loot-manage` 语义对齐后排期。
- J-3：`NOTE-7`/`NOTE-8` 依赖人工复核动作，SKILL 已列入「校验标准」人工判据，考试时须逐条过。
- J-4：`archive_encrypted` 依赖外部 7z；CI 有 7z，本地可能缺失，缺失时如实记 `NOTE-8` 而不放行。
