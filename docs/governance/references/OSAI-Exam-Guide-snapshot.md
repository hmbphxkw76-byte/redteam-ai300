# OSAI Exam Guide 一手源快照（S3）

> **性质**：官方事实存档，非规范正文；官方原文为唯一权威。本文件只做留痕与指针，不定义流程。  
> **来源 URL**：<https://help.offsec.com/hc/en-us/articles/46593096734612-OSAI-Exam-Guide>  
> **文章 ID**：`46593096734612` · **标题**：OSAI Exam Guide – OffSec Support Portal  
> **抓取日期**：2026-11-14（GMT+8）  
> **页面时间元数据**：仅显示相对时间 "1 month ago"，未见绝对更新日期。  
> **抓取方式**：WebFetch 定向逐段提取官方页面原文，三次不同提示词交叉覆盖；搜索结果摘要与二手博客不作为依据。  
> **可达性记录**：沙箱内 `curl` 直连 help.offsec.com 返回 HTTP 000 / SSL 错误 35，`r.jina.ai` 镜像连接失败（exit 7）；原文经 WebFetch 通道取得。  
> **权威指针**：`docs/research/report-exam-canonical.md` §0 / §10；官方报告模板 S1 见 `docs/governance/references/OSAI-Exam-Report.pdf`。

---

## 1. Documentation Requirements（Section 1，逐字）

```text
You are required to write a report describing your exploitation process for each target in the environment.

Your report must document all of your attacks, including every step taken, all commands issued, any code or scripts written, and the relevant console output. Where you use an existing script or exploit, you must provide a link to its source or a copy of the code, along with documentation of any modifications you made to it. Each stage of your attack should also be supported by screenshots showing the various steps and stages of the exploitation process.

In addition, your report must include a summary and overview of the vulnerabilities identified, the attacks performed, and the overall exploitation process. Your documentation should be thorough enough that your attacks can be replicated step-by-step, via a copy/paste approach, by a technically competent reader.

The documentation requirements are very strict and failure to provide sufficient documentation will result in reduced or zero points being awarded. Please note that once your exam report is submitted, your submission is final. If any screenshot or other information is missing, you will not be allowed to send them and we will not request them.
```

## 2. Exam Restrictions（Section 1，逐字）

```text
The exam is entirely open book. You are free to consult any documentation, reference material, or notes you wish, and there are no restrictions on the tools you may use — you may employ any tooling, framework, or technique you find appropriate to complete the objectives.

Above all, this exam is designed with the active use of AI in mind, and we strongly encourage you to leverage it throughout every stage of your attack, from reconnaissance and vulnerability identification through exploitation, privilege escalation, and lateral movement.

AI is treated as a valuable part of the modern red teamer's toolkit, and the environment has been built so that you can use it to its fullest. We recommend directing AI to assist with analyzing targets, crafting and adapting payloads, troubleshooting failed attempts, and interpreting the AI-focused vectors you encounter.

Learners who choose not to make use of AI will likely find the exam extremely challenging.
```

同节另有两条约束（逐字要点）：

```text
NOTE: While you may use Discord as a resource for searching for information during the exam, under no circumstances are you permitted to seek or receive assistance from others on the platform.

Downloading any applications, files, or source code from the exam environment to your local machine is strictly forbidden. An exception is made for material you need to process locally on your Kali VM — for example, password hashes or encrypted keys you crack offline.
```

## 3. Point Allocation（Section 2，逐字）

```text
The exam environment consists of ten machines: six target machines distributed across two attack chains, one standalone host, one Domain Controller, and two intentionally not vulnerable machines. The intentionally not vulnerable machines carry no points and are present to add realism to the environment. The eight scored targets total a maximum of 100 points.

Points are allocated by target type: each AI-vector machine is worth 15 points, each traditional-vector machine is worth 10 points, and the standalone AI-focused machine is worth 15 points. The Domain Controller holds a flag worth 5 points; because both chains converge on the DC by different routes, this flag can be submitted only once, even if you complete both chains.

You must achieve a minimum score of 75 points to pass the exam and receive the OffSec AI Red Teamer (OSAI) certification. Points will be awarded for each target based on submitting the correct answer and the completeness of your findings in the exam report, including adherence to the Documentation Requirements.

An interactive shell is not required to complete OSAI exam objectives. Learners may retrieve the required proof files through any valid method.
```

## 4. Point Disqualification（Section 2，逐字）

```text
- Failure to provide the proof file contents in both the control panel and a screenshot
- Lack of documentation
```

## 5. 时长与提交窗口（逐字）

```text
You will have 24 hours to complete the exam. Once your exam has started, you will see a timer at the bottom of your screen.

Once the exam is finished, you will have another 24 hours to upload your documentation within the OffSec Portal.
```

```text
Learners must submit their report within 24 hours of completing the exam. Failure to meet this deadline will result in an automatic exam failure.
```

## 6. Submission（Section 3，逐字）

```text
The exam report upload menu is built directly into the learning portal, so there's no need to visit any external websites. Once you click to end the exam or when your exam time runs out, a pop-up will appear for submitting your exam report. Simply click the 'Submit Exam Files' button at the bottom right. Please note that after submission, you will not be able to make any changes to your report. This step is final, so be sure to review your exam thoroughly before submitting.
```

**Submission Checklist（逐字）**：

```text
- Your exam report is in PDF format
- You have used the following format for the PDF file name
  "OSAI-OS-XXXXX-Exam-Report.pdf", where "OS-XXXXX" is your OSID
- Your PDF has been archived into a .7z file (Please DO NOT archive it with a password)
- You have used the following format for the .7z file name
  "OSAI-OS-XXXXX-Exam-Report.7z", where "OS-XXXXX" is your OSID
- You have made sure that your archive is not more than 100MB
```

## 7. Submission Format and Name / Archive File（逐字）

```text
Your exam report must be submitted in PDF format archived into a .7z file. Please make sure to include all your queries as text inside the exam report PDF file itself. No other file formats will be accepted within the .7z file other than PDF file format.

If you submit your report in any other file format, we will not request or remind you to send a PDF report archived into a .7z file and your exam report will not be scored.
```

```text
Please do not archive your .7z and PDF(s) files with a password. Our system will not accept should you upload a password-protected files.

You must submit your documentation in a .7z file. Please use your Kali machine to create your .7z file.
```

```text
7z a OSAI-OS-XXXXX-Exam-Report.7z OSAI-OS-XXXXX-Exam-Report.pdf
```

```text
After uploading your exam file, the site will provide you with the MD5 hash of your uploaded file. Please make sure to verify that you have uploaded your report correctly by checking and comparing the MD5 hashes of your uploaded exam file and the file you have locally.
```

## 8. Suggested Documentation Templates / Results（逐字要点）

```text
Ideally, one of the following templates should be used for the exam report: Microsoft Word / OpenOffice/LibreOffice. You may use your own template as long as the information is presented in a structured, professional manner and follows all other requirements outlined above.
```

```text
You will receive your certification exam results (pass/fail) within ten (10) business days after submitting your documentation.
```

## 9. 事实到 canonical 编号的映射（只写指针）

| S3 官方事实                                                            | 对应落点                                                                           |
| ------------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| 10 台环境 / 2 台 intentionally not vulnerable / 8 计分目标 / 100 分 / 75 及格 | `docs/research/report-exam-canonical.md` F-6.1、F-6.3；`GOVERNANCE.md` §2.1–§2.3 |
| AI 向量 15 / 传统向量 10 / 独立机 15 / 域控 5；proof flag 仅提交一次                | canonical F-6.2（原标「推导」，现升级为 S3 已核实）、F-1.6                                      |
| "completeness of your findings in the exam report" 为给分条件           | canonical F-6.1；§2.3 目标分 ≥85 的依据                                               |
| Point Disqualification（面板 + 截图双通道；文档缺失）                            | canonical F-3.3；`GOVERNANCE.md` §2.4；`skills/verify-evidence` vrf-04           |
| Documentation Requirements（每步命令/输出/脚本/修改说明/截图/copy-paste 复现）       | canonical F-1.4；`GOVERNANCE.md` §6.1；`skills/report-exam/SKILL.md` §2 五段式      |
| 24h 考试 + 24h 提交窗口、提交后不可修改                                          | canonical F-4.3；`GOVERNANCE.md` §5.4、§6.4                                      |
| PDF / `.7z` 命名、无密码、≤100MB、仅 PDF 入档、MD5 上传校验                        | canonical F-4.1、F-4.2；`GOVERNANCE.md` §6.4                                     |
| open book、无工具限制、strongly encourage AI；禁止从考试环境下载文件                  | 本文件 §2；T03 政策复核                                                                |

## 10. 核实边界与偏差记录

- S3 原文**未出现** `trad_vector.txt` / `ai_vector.txt` / `proof.txt` 文件名及其路径；该事实来自 **S1**（`OSAI-Exam-Report.pdf` 第 5 页），见 `skills/report-exam/references/official-requirements.md` §6 与 canonical F-1.5。不得把文件名误标为 S3 来源。
- S3 原文**未出现**字母编号附录 A / D / E；`skills/report-exam/templates/osai-report-template-en.md` 的 `## A. Scripts & PoC` / `## D. AI Session / Prompt History` / `## E. Screenshot Index` 属仓库 extension，不是 S1 官方强制条目（S1 Appendix 为一段无编号说明）。canonical F-1.7 已按此修正。
- S3 原文**未明示**「AI prompt / 会话历史须入报告附录」；该条来自 S1 的 Requirements 与 Appendix 段落，且 S3 §7 要求 "include all your queries as text inside the exam report PDF file itself"，二者方向一致。
- WebFetch 返回的部分段落含 `[...]` 省略标记，本快照为**关键段落逐字存档**，非整页全文镜像；未取到的段落（Objectives 后半、Exam Connection 完整步骤、Guidelines/Contact Protocol 全文）不影响本项目任何验收条件。页面无绝对更新日期，仅相对时间。
- 分值构成中「6 台链式主机 = 4 AI 向量 + 2 传统向量」仍属**推导**：S3 明示每台分值与总分，未明示链式主机中两类各几台。

## 11. 关联一手源：AI Usage Policy in OffSec Exams（供 T03 复核）

> **URL**：<https://help.offsec.com/hc/en-us/articles/35549468971156-AI-Usage-Policy-in-OffSec-Exams>  
> **抓取日期**：2026-11-14 · **页面时间元数据**："4 months ago" · **标题**：AI Usage Policy in OffSec Exams

```text
We acknowledge that many tools and platforms now incorporate AI-powered features designed to improve productivity and efficiency. While you are not required to disable AI-enhanced applications such as Notion, Google AI Overview, or similar tools that assist with organization or summarization, there are restrictions on the use of AI chatbots and Large Language Models (LLMs), except in the case of the OSEE and OSAI exams which the use of AI chatbots and LLMs are allowed.
```

```text
The usage of AI chatbots and LLMs including but not limited to OffSec KAI, ChatGPT, DeepSeek, Gemini, Copilot and similar AI assistants is strictly prohibited during any OffSec exams except for OSEE and OSAI which the usage is allowed.
```

**核实结论**：15:21 会话记录的「AI 工具政策冲突（通用政策仅 OSEE 例外允许）」与当前官方原文不符 —— 现行通用政策明确将 **OSAI 与 OSEE 并列**列为允许例外，与 OSAI Exam Guide 的 "strongly encourage" 一致。该冲突在一手源层面已消解；T03 的书面确认由「高优先阻断」降级为「可选留痕」，二手博客所称「ChatGPT 禁用」不可作为决策依据。
