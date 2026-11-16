#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""提交前断图校验（OSAI §6.1）：报告图片引用必须可解析、PNG 必须完整。

证据目录默认 gitignore，本脚本在打包前本地执行，校验 report/ 与 evidence/
的相对结构未被破坏；不做脱敏、不改动任何文件。
"""
import argparse
import os
import re

MD_IMAGE_RE = re.compile(r"!\[[^\]]*\]\(\s*([^)\s]+)")
HTML_IMAGE_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.I)
REMOTE_PREFIXES = ("http://", "https://", "data:", "#")


def image_refs(text):
    return MD_IMAGE_RE.findall(text) + HTML_IMAGE_RE.findall(text)


def _png_complete(path):
    try:
        if os.path.getsize(path) < 12:
            return False
        with open(path, "rb") as f:
            f.seek(-8, os.SEEK_END)
            return f.read(8) == b"IEND\xaeB`\x82"
    except OSError:
        return False


def check_report(report_path):
    """返回 (是否通过, 问题列表)；问题逐条含路径，便于修复。"""
    base = os.path.dirname(os.path.abspath(report_path))
    with open(report_path, encoding="utf-8") as f:
        text = f.read()
    problems, seen = [], set()
    for ref in image_refs(text):
        if ref.startswith(REMOTE_PREFIXES) or ref in seen:
            continue
        seen.add(ref)
        target = os.path.normpath(os.path.join(base, ref.split("#")[0]))
        if not os.path.isfile(target):
            problems.append("断图：%s 不存在（引用：%s）" % (target, ref))
        elif target.lower().endswith(".png") and not _png_complete(target):
            problems.append("PNG 不完整（缺 IEND）：%s" % target)
    return not problems, problems


def main(argv=None):
    parser = argparse.ArgumentParser(description="校验报告图片引用与证据包")
    parser.add_argument("report", help="报告 markdown 路径")
    args = parser.parse_args(argv)
    ok, problems = check_report(args.report)
    for item in problems:
        print("FAIL %s" % item)
    print("%s 图片引用与证据包一致：%s" % ("PASS" if ok else "BLOCKED", args.report))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())