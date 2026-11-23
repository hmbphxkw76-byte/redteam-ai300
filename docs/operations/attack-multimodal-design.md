# attack-multimodal — 模块与接口设计记录（阶段 6）

> 阶段 6 `codebase-design` · 输入：规格 v2（#433）、工单（#434–#438）、调研 M1–M8
> 术语复用 GLOSSARY 既有条目（转换器/评分器/执行器/对象图），阶段 7 无新增术语 → GLOSSARY 不改。

## 1. seam 清单（沿用 jailbreak 已核对模式）

| seam | 职责 | 输入→输出 | 错误行为 |
|---|---|---|---|
| BackendFactory（唯一真实 seam） | 承载全部 PyRIT 调用 | 步骤规格+目标→攻击结果 | 缺失/失败抛注入异常 |
| RealPyRITBackend | 装配 1.1.0 多模态对象图 | 同上 | 端点缺失抛明确错误 |
| FakePyRITBackend | 同协议替身 | 同上 | 确定性假结果 |
| 证据适配器（复用） | collect_evidence 固定接口 | 步骤标识+产物→片段 | --strict 退出 1 |

新 seam = 0（与 jailbreak 同构），符合 §3.6。

## 2. 对象图（B7，全 1.1.0 已核实）

- 多模态 target：`OpenAIChatTarget`（image/text 输入，M2）、`PlaywrightTarget`（image_path，M5）、`HTTPXAPITarget`（文件上传，M6）
- 执行器：`AttackExecutor(max_concurrency=1)`；评分：`SubStringScorer` 优先 + `SelfAskRefusalScorer`
- 转换器：`Base64Converter`/`ROT13Converter`/`LeetspeakConverter`/`TranslationConverter`
- payload：复用 `attack-rag` 的 `multimodal_camouflage`（不重复实现）
- 禁用：0.x 编排器名、1.2.x 新增符号

## 3. 依赖方向

规格(#433) → 设计 → 实现(`tools/attack_multimodal/`) → 测试(`tests/attack_multimodal/`) → 证据(共享工具)。外部依赖仅经 seam 注入。

## 4. 被否决方案

- 否决"复制 handbook multimodal/inject.py"：不可 import、无引擎。
- 否决"重实现伪装原语"：违反 C1/复用原则。
- 否决"用 1.2.x 多模态新符号"：违反版本锁定。

## 5. G0 门禁（阶段 5/6/7）

| 阶段 | 检查 | 结论 |
|---|---|---|
| 5 | 工单标签 + brief + 阻塞边（#438 blockedBy 435/436/437） | PASS |
| 6 | seam 一致 / 对象图无禁用名 / 依赖单向 | PASS |
| 7 | 术语复用 / check_glossary / B9 矩阵补条目 | PASS（待实跑确认） |
