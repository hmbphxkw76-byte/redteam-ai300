#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify-evidence 机读校验器（GOVERNANCE §8.2 八项检查单）。

仓库级共享组件：`skills/verify-evidence` 的**执行体**，`report-exam` 的
提交前置。独立于任何报告组装实现，避免门禁判据被下游重实现放宽。

判据（严格，对齐 verify-evidence SKILL.md vrf-01..08 + §2.2 单次约束）：
  1 五要素与元信息（OSID + 逐字版权声明）
  2 目标计分清单（评分杠杆）
  3 已取分片段三件套（命令 + 输出 + 截图）齐全；未取分缺失记 missing
  4 flag 双通道一致：面板提交值 == 报告 flag 值；有报告值无面板值即阻断
  5 AI 交互日志全量入 Appendix D
  6 报告四章与 TOC 锚点齐全、可 copy/paste 复现
  7 产物存在 + 命名合规 + 无密码 + ≤100MB
  8 术语合规：废弃术语**动态取自 GLOSSARY.md**（与 check_glossary 同源）
  + 域控 proof.txt 仅可提交一次（已取分时必须 == 1；无证据记 pending VG-4）

退出码：0 = 通过；1 = 阻断；2 = 用法错误。仅依赖 Python 标准库。
"""
import argparse
import importlib.util
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_GLOSSARY = os.path.join(ROOT, "GLOSSARY.md")
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024  # §6.4

REQUIRED_ANCHORS = (
    "## Introduction", "## Objective", "## Requirements",
    "# Executive Summary", "## High-Level Attack Path",
    "# Attack Walkthrough", "# Appendix", "Offsec AI Red Teamer Report",
)
COPYRIGHT_LINE = "Copyright © 2026 OffSec Ltd. All rights reserved."


def load_avoid_terms(glossary_path=DEFAULT_GLOSSARY):
    """复用 scripts/check_glossary.py 的解析逻辑，保证术语判据同源。"""
    path = os.path.join(ROOT, "scripts", "check_glossary.py")
    spec = importlib.util.spec_from_file_location("_check_glossary", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _canonical, avoid = mod.parse_glossary(glossary_path)
    return list(avoid)


def check_naming_and_size(pdf_path, zip_path, osid):
    """§6.4：命名、无密码（不传 -p，由调用方保证）、≤100MB。"""
    missing = []
    exp_pdf = "OSAI-OS-%s-Exam-Report.pdf" % osid
    exp_zip = "OSAI-OS-%s-Exam-Report.7z" % osid
    if os.path.basename(pdf_path or "") != exp_pdf:
        missing.append("PDF 命名不符：期望 %s" % exp_pdf)
    if os.path.basename(zip_path or "") != exp_zip:
        missing.append("归档命名不符：期望 %s" % exp_zip)
    if not (pdf_path and os.path.isfile(pdf_path)):
        missing.append("PDF 产物缺失（§6.4）")
    if not (zip_path and os.path.isfile(zip_path)):
        missing.append(".7z 归档产物缺失（§6.4）")
    if zip_path and os.path.isfile(zip_path):
        if os.path.getsize(zip_path) > MAX_ARCHIVE_BYTES:
            missing.append("归档超过 100MB（§6.4）")
    return (len(missing) == 0), missing


def verify(payload, require_artifacts=True):
    """执行八项检查单。payload 见模块 docstring / CLI --payload。

    返回 dict：checks（逐项 boolean）、passed、blocking、missing、pending。
    - blocking：违反「必须」条款，禁止提交。
    - pending：已登记的核实闸（VG-3 工具环境 / VG-4 真实取分），不计阻断，
      但 `submission_ready` 为 False。
    - missing：未取分目标的证据缺失（SKILL §9 预期），如实记录。
    """
    report = payload.get("report_md", "") or ""
    appendix = payload.get("appendix_md", "") or ""
    osid = payload.get("osid", "XXXXX")
    frags = payload.get("fragments", []) or []
    panel = payload.get("panel_flags", {}) or {}
    pdf = payload.get("pdf_path")
    zip_path = payload.get("zip_path")
    glossary = payload.get("glossary_path", DEFAULT_GLOSSARY)

    checks, blocking, missing, pending = {}, [], [], []

    # vrf-01 五要素与元信息
    checks["vrf-01"] = bool(re.search(r"# OSID:\s*\S+", report)) and COPYRIGHT_LINE in report
    if not checks["vrf-01"]:
        blocking.append("vrf-01：OSID 或逐字版权声明缺失")

    # vrf-02 目标计分清单
    checks["vrf-02"] = "Target Inventory & Point Allocation" in report
    if not checks["vrf-02"]:
        blocking.append("vrf-02：目标计分清单缺失")

    # vrf-03 已取分片段三件套
    scored = [f for f in frags if f.get("flag")]
    checks["vrf-03"] = all(
        f.get("command") and f.get("output") and f.get("screenshot") for f in scored
    )
    for f in frags:
        lack = [k for k, key in (("命令", "command"), ("输出", "output"),
                                 ("截图", "screenshot")) if not f.get(key)]
        if lack:
            missing.append("vrf-03：%s 三件套缺 %s（未取分属预期，待补录）"
                           % (f.get("step_id", "?"), "、".join(lack)))

    # vrf-04 flag 双通道一致（面板值 == 报告值，逐字）
    mismatches = []
    for f in scored:
        host = f.get("host", "")
        panel_value = panel.get(host)
        if panel_value is None:
            mismatches.append("%s 缺控制面板提交值" % f.get("step_id", "?"))
        elif panel_value != f.get("flag"):
            mismatches.append("%s 面板值 != 报告值" % f.get("step_id", "?"))
    checks["vrf-04"] = not mismatches
    for m in mismatches:
        blocking.append("vrf-04：%s（§6.2 / §2.4 双通道一致）" % m)
    for h in {f.get("host", "") for f in frags}:
        if not any(f.get("flag") for f in frags if f.get("host") == h):
            missing.append("vrf-04：%s 无 flag 双通道证据（未达成，待补录）" % h)

    # vrf-05 AI 交互日志全量入附录
    with_ai = [f for f in frags if (f.get("ai_log") or "").strip()]
    checks["vrf-05"] = all((f["ai_log"] or "").strip() in appendix for f in with_ai)
    if with_ai and not checks["vrf-05"]:
        blocking.append("vrf-05：AI 交互日志未全量入 Appendix D")
    if not with_ai and frags:
        missing.append("vrf-05：本次输入无 AI 交互日志（须回溯对应技能按 §6.3 补录）")

    # vrf-06 报告结构完整可复现
    checks["vrf-06"] = all(a in report for a in REQUIRED_ANCHORS)
    for a in REQUIRED_ANCHORS:
        if a not in report:
            blocking.append("vrf-06：报告缺锚点 %s" % a)

    # vrf-07 提交格式：dry-run 时记 None（未判定），绝不放宽为 True
    if require_artifacts:
        ok, miss = check_naming_and_size(pdf, zip_path, osid)
        checks["vrf-07"] = ok
        blocking.extend("vrf-07：%s" % m for m in miss)
    else:
        checks["vrf-07"] = None
        pending.append("VG-3：pandoc/7z 产物未生成，本次为 dry-run，不可提交")

    # vrf-08 术语合规（动态取自 GLOSSARY.md）
    try:
        avoid = load_avoid_terms(glossary)
    except (OSError, AttributeError):
        avoid = []
    # 逐字 include 的证据原文（S1 §6.1 / SKILL §3.2）不作术语改写：
    # vrf-08 只扫描叙述正文，证据区间由边界标记排除。
    scan_text = re.sub(
        r"<!-- EVIDENCE-FRAGMENT-START -->.*?<!-- EVIDENCE-FRAGMENT-END -->",
        "", report, flags=re.S)
    hits = [t for t in avoid if t in scan_text]
    checks["vrf-08"] = not hits
    if hits:
        blocking.append("vrf-08：报告叙述正文使用废弃术语 %s" % "、".join(hits))

    # 域控 proof.txt 单次（§2.2）
    proof_records = [f for f in frags
                     if "proof.txt" in (f.get("flag") or "")]
    checks["proof-single"] = len(proof_records) <= 1
    if len(proof_records) > 1:
        blocking.append("proof.txt 提交记录 %d 次，违反 §2.2 单次约束" % len(proof_records))
    if not proof_records:
        # SKILL §9：未取分目标的证据缺失属预期，不计阻断、也不阻断提交
        missing.append("VG-4：域控 proof.txt 尚未取分，单次提交约束待真实取分后闭环（预期）")

    # passed = 无阻断项（vrf-07 未判定不计入）；submission_ready 另要求产物齐全
    failed_checks = [k for k, v in checks.items() if v is False]
    passed = not failed_checks and not blocking
    submission_ready = passed and not pending and checks.get("vrf-07") is True
    return {"checks": checks, "passed": passed, "blocking": blocking,
            "missing": missing, "pending": pending,
            "failed_checks": failed_checks,
            "submission_ready": submission_ready}


def main(argv=None):
    ap = argparse.ArgumentParser(description="verify-evidence 八项检查单机读校验")
    ap.add_argument("--payload", required=True, help="JSON 载荷文件路径")
    ap.add_argument("--no-artifacts", action="store_true",
                    help="dry-run：不要求 PDF/.7z 产物（结果不可提交）")
    args = ap.parse_args(argv)
    try:
        with open(args.payload, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, ValueError) as exc:
        print("ERROR: 无法读取载荷：%s" % exc, file=sys.stderr)
        return 2
    result = verify(payload, require_artifacts=not args.no_artifacts)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
