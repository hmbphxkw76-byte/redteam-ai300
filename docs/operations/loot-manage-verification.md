# loot-manage 端到端验证（§8.1(d)）

> **性质**：阶段 8 交付物的端到端演示证据。环境：Python 3.11、仅标准库、零网络。
> **被测**：`tools/loot_manage/`（`registry.py` + `cli.py`）与 `loot/registry.md` 空骨架。
> **演示目录**：`mktemp -d` 临时工作区，不污染产品登记簿 `loot/registry.md`。

## 1. 初始化与空态

```bash
python -m tools.loot_manage --registry "$T/loot/registry.md" init
python -m tools.loot_manage --registry "$T/loot/registry.md" --root "$T" validate
```

输出：`结论：PASS`（空表结构合法）。加 `--require-loot` 时退出码 `1`，`ERROR: 空态：登记簿无任何战利品`——作为 `capstone-rehearse` 缺口信号。

## 2. 凭据登记（loot-01 / AC-1）

```bash
python -m tools.loot_manage --registry "$T/loot/registry.md" --root "$T" \
  register --type 凭据 --content "u:p" --host 10.0.0.1 --evidence loot/demo-01.md
```

输出：`已登记：L-1`；`validate` 八项检查全 `OK`，`结论：PASS`。

## 3. flag 双通道（loot-03 / AC-3, AC-6）

```bash
python -m tools.loot_manage --registry "$T/loot/registry.md" --root "$T" \
  register --type flag --content "ai_vector.txt" --host 10.0.0.2 \
  --evidence loot/demo.md --flag-panel "FLAG{abc}" --flag-shot "shots/ai.png"
```

`validate --json` 输出：

```json
{"passed": true, "flags": [{"id": "L-1", "host": "10.0.0.2",
  "panel": "FLAG{abc}", "shot": "shots/ai.png", "consistent": true}]}
```

缺 `--flag-shot` 时退出码 `2`：`ERROR: flag 登记必须同时提供 --flag-panel 与 --flag-shot`。
`consistent` 的语义为「两通道均已提供」；值级一致性由 `verify-evidence` 在下游读取截图核对（本登记存截图**路径**）。

## 4. 攻击路径沉淀（loot-04 / AC-4）

```bash
python -m tools.loot_manage --registry "$T/loot/registry.md" --root "$T" register --path "入口 10.0.0.1 → 10.0.0.2"
```

输出：`已追加攻击路径：入口 10.0.0.1 → 10.0.0.2`；有登记行时 `validate` 要求该小节非空。

## 5. 反例（AC-9）

| 反例 | 期望 | 实测 |
|---|---|---|
| 表头删一列 | 退出 1，`表头列不符` | 符合 |
| 行单元格数≠8 | 退出 1，`单元格数≠8` | 符合 |
| 证据路径不存在 | 退出 1，`证据片段路径不存在` | 符合 |
| flag 行无双通道 | 退出 1，`flag 行缺双通道` | 符合 |
| 有行但攻击路径空 | 退出 1，`攻击路径小节为空` | 符合 |
| 编号重复 / 非 `L-<n>` | 退出 1，`编号重复` / `编号格式非法` | 符合 |

## 6. 产品登记簿

`python -m tools.loot_manage --registry loot/registry.md validate` → `结论：PASS`（空骨架合法，`attack_path` 无行时为真）。

## 7. 质量门对照

| SKILL.md 质量门 | 落地校验 |
|---|---|
| 表结构 8 列齐全 | `checks.columns`（列名集合） |
| 每行可追溯（证据路径存在） | `checks.evidence` |
| 每个 flag 双通道 | `checks.dual_channel` + `flags[].consistent` |
| 无战利品散落对话 | 工具规范：编号 `L-<n>` 唯一；`--json` 为唯一引用源 |
| 登记即时 | `register` 即时追加 |
