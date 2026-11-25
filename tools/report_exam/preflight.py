#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""报告与提交件本地预检：占位文本、官方命名/体积/入档规则、本地 MD5。

只读；不生成 PDF/.7z，不接触考试门户。7z 探测可注入，便于离线单测。
依据：docs/governance/references/OSAI-Exam-Guide-snapshot.md:83-115。
"""
from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from typing import Callable, Iterable, Tuple

PDF_NAME = re.compile(r"^OSAI-OS-[A-Z0-9]{5}-Exam-Report\.pdf$", re.I)
ARCHIVE_NAME = re.compile(r"^OSAI-OS-[A-Z0-9]{5}-Exam-Report\.7z$", re.I)
MAX_BYTES = 100 * 1024 * 1024
PLACEHOLDERS = ("{{", "NOT ATTEMPTED", "待补录", "pending backfill", "TODO")


def scan_report_placeholders(text: str) -> list[Tuple[int, str]]:
    """返回 (行号, 占位符) 列表；行号从 1 起。"""
    found = []
    for no, line in enumerate(text.splitlines(), 1):
        for token in PLACEHOLDERS:
            if token in line:
                found.append((no, token))
    return found


def default_archive_probe(archive: str) -> Tuple[bool | None, list[str] | None, str]:
    """用系统 7z 只读列出归档：返回 (是否加密, 成员列表, 说明)。"""
    try:
        p = subprocess.run(["7z", "l", "-slt", archive], capture_output=True,
                           text=True, errors="replace", timeout=30)
    except FileNotFoundError:
        return None, None, "未找到 7z 命令，无法核验无密码与成员类型"
    except (OSError, subprocess.SubprocessError) as exc:
        return None, None, "7z 探测失败：%s" % exc
    if p.returncode != 0:
        return None, None, "7z 列出失败：%s" % p.stderr.strip()[:120]
    encrypted = any(line.strip().lower().replace(" ", "") == "encrypted=+"
                    for line in p.stdout.splitlines())
    members = [line.split("=", 1)[1].strip()
               for line in p.stdout.splitlines()
               if line.strip().lower().startswith("path = ")]
    members = [m for m in members if m and not m.startswith(".")]
    return encrypted, members, ""


def _md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check_submission(pdf: str, archive: str, expected_md5: str = "",
                     probe: Callable[[str], Tuple[bool | None, list[str] | None, str]] | None = None,
                     max_bytes: int = MAX_BYTES) -> dict:
    """按官方 Submission Checklist 判定；probe 可注入以离线测试。"""
    probe = probe or default_archive_probe
    checks = {
        "pdf_name": bool(pdf) and bool(PDF_NAME.match(os.path.basename(pdf))),
        "archive_name": bool(archive) and bool(ARCHIVE_NAME.match(os.path.basename(archive))),
        "size": bool(archive) and os.path.isfile(archive) and os.path.getsize(archive) <= max_bytes,
        "only_pdf": False,
        "no_password": False,
        "md5": True,
    }
    notes: list[str] = []
    local_md5 = ""
    if archive and os.path.isfile(archive):
        local_md5 = _md5(archive)
        encrypted, members, err = probe(archive)
        if err:
            notes.append(err)
        checks["only_pdf"] = bool(members) and all(m.lower().endswith(".pdf") for m in members)
        checks["no_password"] = encrypted is False
        if encrypted is None:
            notes.append("加密状态未知，按未通过处理")
        elif encrypted:
            notes.append("归档已加密，官方系统拒收")
    else:
        notes.append("归档文件不存在：%s" % archive)
    if expected_md5:
        checks["md5"] = bool(local_md5) and local_md5.lower() == expected_md5.strip().lower()
        if not checks["md5"]:
            notes.append("本地 MD5 与上传后期望值不一致")
    return {"ok": all(checks.values()), "checks": checks,
            "local_md5": local_md5, "notes": notes}


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="OSAI 报告与提交件本地预检（只读）")
    ap.add_argument("--report", help="报告 markdown 路径（占位符扫描）")
    ap.add_argument("--pdf", default="", help="PDF 路径")
    ap.add_argument("--archive", default="", help=".7z 路径")
    ap.add_argument("--expected-md5", default="", help="门户回传 MD5（可选）")
    args = ap.parse_args(list(argv) if argv is not None else None)
    if args.report:
        with open(args.report, encoding="utf-8") as f:
            hits = scan_report_placeholders(f.read())
        if hits:
            print("报告占位符（%s）：%d 处" % (args.report, len(hits)))
            for no, token in hits:
                print("  - %s:%d：%s" % (args.report, no, token))
        else:
            print("报告占位符（%s）：无" % args.report)
    result = check_submission(args.pdf, args.archive, args.expected_md5)
    for key, value in result["checks"].items():
        print("%s: %s" % (key, "PASS" if value else "BLOCKED"))
    print("local_md5: %s" % (result["local_md5"] or "（未计算）"))
    for note in result["notes"]:
        print("note: %s" % note)
    print("提交预检：%s" % ("PASS" if result["ok"] else "BLOCKED"))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
