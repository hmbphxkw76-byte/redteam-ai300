# threat-model — 阶段 7 `domain-modeling` 门禁记录（历史留痕回填）

> 回溯核验：不表示原流程按序执行；判定依据见右列，均由现有产物或本次复跑支撑。

| 检查项 | 依据 | 实测摘要 | 判定 |
|---|---|---|---|
| 本阶段产物 | 主线 §3.7 | `GLOSSARY.md` 收录「AI向量机」「诱饵机」「信任边界」「威胁模型」「优先级攻击图」等条目，含定义与 `_Avoid_` 禁用同义词 | 符合（回溯） |
| 上游复核 | 主线 §2.3 | `python -m unittest discover -s tests/threat_model -t . -q` → 73 例 OK | 符合（回溯） |
| B1–B9 相关项 | 主线 §2.1 | B2 `python scripts/check_glossary.py` 对 threat-model 条目零废弃术语命中（全局非 0 由 report-exam 既存文件导致，与本技能无关）；B1 术语表结构合规 | 替代（回溯） |

**结论：PASS（回溯）**。证据指针：`GLOSSARY.md`（计分/攻击面/Ch10 小节）、`docs/operations/domain.md`；提交 `9c5581d`。
