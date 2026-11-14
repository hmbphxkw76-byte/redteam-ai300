"""打包、命名合规与 verify-evidence 八项检查单衔接（§6.4 / §7.3 / §8.2）。

pandoc / 7z 以 subprocess 惰性调用：导入本模块不触发外部工具；
CI/沙箱缺工具时显式失败并转 VG-3 核实闸，不静默跳过。
"""
import os
import re
import subprocess

from ._types import ReportModel
from .skeleton import COPYRIGHT

MAX_ARCHIVE_BYTES = 100 * 1024 * 1024  # §6.4：≤100MB
PDF_NAME = "OSAI-OS-{osid}-Exam-Report.pdf"
ZIP_NAME = "OSAI-OS-{osid}-Exam-Report.7z"

# S1 §7.1 四章 + TOC 条目（AC-03 / AC-04）
REQUIRED_ANCHORS = [
    "## Introduction",
    "## Objective",
    "## Requirements",
    "# Executive Summary",
    "## High-Level Attack Path",
    "# Attack Walkthrough",
    "# Appendix",
    "Offsec AI Red Teamer Report",
]


def _default_runner(argv, **kwargs):
    return subprocess.run(argv, **kwargs)


def render_pdf(markdown_text, out_dir, osid, runner=None):
    """pandoc --toc 渲染 EN 版 PDF；返回 pdf 路径。缺 pandoc 抛 RuntimeError（VG-3）。"""
    runner = runner or _default_runner
    os.makedirs(out_dir, exist_ok=True)
    src = os.path.join(out_dir, "report-en.md")
    pdf = os.path.join(out_dir, PDF_NAME.format(osid=osid))
    with open(src, "w", encoding="utf-8") as f:
        f.write(markdown_text)
    try:
        runner(["pandoc", "--toc", src, "-o", pdf], check=True,
               capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            "VG-3：pandoc 不可用或渲染失败（%s）；请核实 CI/沙箱 pandoc 安装。" % exc
        ) from exc
    return pdf


def make_archive(pdf_path, out_dir, osid, runner=None):
    """7z a -mx=9 无密码归档；返回 .7z 路径。缺 7z 抛 RuntimeError（VG-3）。"""
    runner = runner or _default_runner
    zip_path = os.path.join(out_dir, ZIP_NAME.format(osid=osid))
    if os.path.isfile(zip_path):
        os.remove(zip_path)
    try:
        runner(["7z", "a", "-mx=9", zip_path, pdf_path], check=True,
               capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            "VG-3：7z 不可用或打包失败（%s）；请核实 CI/沙箱 7z 安装。" % exc
        ) from exc
    return zip_path


def check_naming_and_size(pdf_path, zip_path, osid):
    """AC-12：命名合规、≤100MB、无密码。返回 (bool, missing_list)。"""
    missing = []
    exp_pdf = PDF_NAME.format(osid=osid)
    exp_zip = ZIP_NAME.format(osid=osid)
    if os.path.basename(pdf_path or "") != exp_pdf:
        missing.append("PDF 命名不符：期望 %s" % exp_pdf)
    if os.path.basename(zip_path or "") != exp_zip:
        missing.append("归档命名不符：期望 %s" % exp_zip)
    if zip_path and os.path.isfile(zip_path):
        if os.path.getsize(zip_path) > MAX_ARCHIVE_BYTES:
            missing.append("归档超过 100MB（§6.4）")
        # .7z 头部无 Encrypted 标记即无密码；此处以不传 -p 为保证，机读复核留给 CI
    return (len(missing) == 0), missing


def verify_report(model: ReportModel, report_md, appendix_md="",
                  pdf_path=None, zip_path=None):
    """verify-evidence 八项检查单（vrf-01..08）+ proof.txt 单次。

    返回 dict：checks（逐项 boolean）、passed、blocking、missing（非阻断缺失清单）。
    依 SKILL §9，未取分目标的证据缺失属预期，记为 missing 而非阻断项。
    """
    frags = [f for fs in model.hosts.values() for f in fs]
    checks = {}
    blocking = []
    missing = []

    # vrf-01 五要素与元信息（CI S1 validate_skill 覆盖，此处核对报告侧元信息）
    checks["vrf-01"] = bool(re.search(r"# OSID:\s*\S+", report_md)) and (
        "Copyright © 2026 OffSec Ltd. All rights reserved." in report_md
    )
    if not checks["vrf-01"]:
        blocking.append("vrf-01：OSID 或逐字版权声明缺失")

    # vrf-02 优先级与评分杠杆（报告含 8 计分目标清单）
    checks["vrf-02"] = "Target Inventory & Point Allocation" in report_md
    if not checks["vrf-02"]:
        blocking.append("vrf-02：目标计分清单缺失")

    # vrf-03 每步骤三件套：仅对「已取分」（有 flag 取证）的片段作阻断判定；
    # 依 SKILL §9 / verify-evidence「失败与豁免」，未取分目标的证据缺失属预期，
    # 如实记入 missing（待补录），不计入阻断项。
    scored = [f for f in frags if f.flag]
    checks["vrf-03"] = all(f.command and f.output and f.screenshot for f in scored)
    for f in frags:
        lack = [k for k, v in (("命令", f.command), ("输出", f.output),
                               ("截图", f.screenshot)) if not v]
        if lack:
            missing.append("vrf-03：%s 三件套缺 %s（未取分属预期，待补录）"
                           % (f.step_id, "、".join(lack)))

    # vrf-04 flag 双通道一致：有 flag 文本即视为已提供双通道占位；
    # 缺 flag 的主机如实记为未达成，不计阻断（SKILL §9）
    flags = [f for f in frags if f.flag]
    checks["vrf-04"] = all(model.dual_channel.get(f.host, False) for f in flags)
    for h, fs in model.hosts.items():
        if not any(f.flag for f in fs):
            missing.append("vrf-04：%s 无 flag 双通道证据（未达成，待补录）" % h)

    # vrf-05 AI 交互已入附录
    with_ai = [f for f in frags if f.ai_log.strip()]
    checks["vrf-05"] = all(f.ai_log.strip() in appendix_md for f in with_ai) if with_ai else True
    if with_ai and not checks["vrf-05"]:
        blocking.append("vrf-05：AI 交互日志未全量入 Appendix D")

    # vrf-06 报告结构完整可复现
    checks["vrf-06"] = all(a in report_md for a in REQUIRED_ANCHORS)
    for a in REQUIRED_ANCHORS:
        if a not in report_md:
            blocking.append("vrf-06：报告缺锚点 %s" % a)

    # vrf-07 提交格式 / 命名 / ≤100MB（未生成产物时记为待执行，不阻断）
    if pdf_path and zip_path:
        ok, miss = check_naming_and_size(pdf_path, zip_path, model.osid)
        checks["vrf-07"] = ok
        missing.extend(miss)
    else:
        checks["vrf-07"] = True
        missing.append("vrf-07：PDF/.7z 产物尚未生成（VG-3 核实闸）")

    # vrf-08 术语合规（CI check_glossary 覆盖；报告正文不得含 _Avoid_ 字面）
    banned = ["蜜罐", "rabbit hole", "证据切片", "靶机", "靶标"]
    checks["vrf-08"] = not any(b in report_md for b in banned)

    # 域控 proof.txt 单次（§2.2）：仅统计 flag 取证记录，
    # 不把骨架中的 `type ...\proof.txt` 命令模板计为提交。
    proof_count = sum(1 for f in frags if "proof.txt" in (f.flag or ""))
    checks["proof-single"] = proof_count <= 1
    if not checks["proof-single"]:
        blocking.append("proof.txt 提交记录 %d 次，违反 §2.2 单次约束" % proof_count)

    passed = all(checks.values()) and not blocking
    return {"checks": checks, "passed": passed,
            "blocking": blocking, "missing": missing}


def package(model: ReportModel, en_markdown, out_dir, runner=None):
    """编排渲染 → 归档 → verify-evidence 衔接（AC-12 / AC-13）。

    缺 pandoc/7z 时返回 passed=False 且记录 VG-3，不抛断流程。
    """
    result = {"pdf": None, "zip": None, "verify": None, "passed": False,
              "blocking": [], "vg3": False}
    ai = ""
    try:
        pdf = render_pdf(en_markdown, out_dir, model.osid, runner=runner)
        zip_path = make_archive(pdf, out_dir, model.osid, runner=runner)
        result["pdf"], result["zip"] = pdf, zip_path
    except RuntimeError as exc:
        result["blocking"].append(str(exc))
        result["vg3"] = True
    v = verify_report(model, en_markdown, appendix_md=en_markdown,
                      pdf_path=result["pdf"], zip_path=result["zip"])
    result["verify"] = v
    result["blocking"].extend(v["blocking"])
    result["passed"] = v["passed"] and not result["vg3"] and not result["blocking"]
    return result
