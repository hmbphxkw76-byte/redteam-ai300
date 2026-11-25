---
name: attack-multimodal
priority: P1
domain: D6
scoring_unit: AI向量机
trigger: recon-ai 已确认目标接受图像/PDF/文件上传或浏览器 UI 输入，并取得可达 AI 向量机的内网立足点
input: recon-ai 资产清单（多模态输入通道、target 类型、摄取路径）、attack-rag 伪装原语
output: 每步「命令 + 输出 + 截图」证据、跨模态响应对照、AI 交互日志、ai_vector.txt flag 双通道取证
---

# attack-multimodal — 跨模态注入与隐写载体

针对接受图像、PDF 或文件输入的多模态 AI 向量机（每台 15 分），复用 `attack-rag` 的伪装原语，以 PyRIT `1.1.0` 已核实的多模态 target 承载发送；确定性评分优先，不确定如实标 `UNDETERMINED`。

## 执行体

严格按 A → B → C → D 顺序推进，未过质量门不进入下一组：

- **A 通道与能力（multimodal-01/02）**：枚举图像上传、PDF、OCR、浏览器四类输入；判定是否接受 `image_path` 或文件输入消息片。
  - `python tools/attack_multimodal/demo.py --step multimodal-01 --target "<TARGET_ENDPOINT>"`
- **B 载荷（multimodal-03/04）**：生成白底白字、PDF 元数据、图像 OCR 伪装载荷；做 base64/ROT13/leetspeak/翻译变换绕过关键词过滤。
- **C 发送与判定（multimodal-05..08）**：经 `OpenAIChatTarget` 图像输入、`HTTPXAPITarget` 文件上传、`PlaywrightTarget` 浏览器 UI 分别注入并对照响应；确定性子串评分优先。
- **D flag（multimodal-09/10）**：定位并读取 `ai_vector.txt`；`whoami`/`id` 与 flag 同屏，双通道一致。

每步证据统一经 `python tools/collect_evidence.py --step multimodal-NN --cmd "<实测命令>" --out loot/multimodal-NN.md --shot-cmd "import -window root evidence/multimodal-NN.png" --ai-log "<prompt/模型/输出/采纳>" --strict` 落盘；正式取证改用 `--exam --scored-target`。

## 质量门

- 每步三件套齐全，AI 交互日志四字段齐备；载荷生成须记录原语来源与修改说明。
- 发送前后响应对照逐字保留；部分生效不得写成完全成功，无法判定标 `UNDETERMINED`。
- flag 双通道一致且访问证明同屏；不把截图路径当作面板 flag 值。
- 版本锁定 `pyrit==1.1.0`；target 只取权威索引已核实的 1.1.0 类，禁止 1.2.x 新增符号。
- 片段节标题与 flag fenced 原值块不得改写（下游 `report_exam.index.parse_fragment` 契约）。

## 校验标准

- `python -m unittest discover -s tests -t .` 通过；`tests/attack_multimodal/test_attack_multimodal_evidence_contract.py` 通过。
- `python scripts/check_glossary.py`、`python scripts/check_token_budget.py --check` 通过。
- 步骤可 copy/paste 复现；每条结论可回溯到证据片段路径。

## 失败与豁免

- 目标不接受任何文件/图像输入：记录判定依据后改走 `attack-ai-agent` 或 `attack-rag`，不伪造摄取效果。
- OCR 识别失败或载荷被拦截：如实记录响应与拦截原因，不重复同一被拦截动作。
- 疑似诱饵机（0 分）≤30 分钟内结束。
- 实现入口在 `tools/attack_multimodal/`；框架组合取自 `docs/research/osai-skill-framework-matrix.md` 第 18 项。

> 主线：`docs/operations/skill-mainline-workflow.md`（C1/C8：11 阶段、to-spec 两遍、G0）。
