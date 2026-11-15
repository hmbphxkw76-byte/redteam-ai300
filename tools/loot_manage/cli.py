#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""loot-manage 命令行薄封装：init / validate / register / query / set-status / empty-state。"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime

from . import registry as reg


def _now() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _read(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write(path: str, text: str) -> None:
    d = os.path.dirname(os.path.abspath(path))
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def _next_id(text: str) -> str:
    r = reg.parse_registry(text)
    nums = [int(m.group(1)) for m in (re.match(r"L-(\d+)", x.id or "") for x in r.rows) if m]
    return "L-%d" % ((max(nums) + 1) if nums else 1)


def cmd_init(args) -> int:
    if os.path.exists(args.registry) and not args.force:
        print("ERROR: 登记簿已存在（用 --force 覆盖）：%s" % args.registry, file=sys.stderr)
        return 2
    _write(args.registry, reg.SKELETON)
    print("已初始化登记簿：%s" % args.registry)
    return 0


def cmd_validate(args) -> int:
    if not os.path.isfile(args.registry):
        print("ERROR: 登记簿不存在：%s" % args.registry, file=sys.stderr)
        return 2
    result = reg.validate(reg.parse_registry(_read(args.registry)),
                          root=args.root, require_loot=args.require_loot,
                          check_pieces=args.check_pieces)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for chk, ok in result["checks"].items():
            print("[%s] %s" % ("OK" if ok else "FAIL", chk))
        for w in result["warnings"]:
            print("WARN: %s" % w)
        for b in result["blocking"]:
            print("ERROR: %s" % b)
        print("结论：%s" % ("PASS" if result["passed"] else "BLOCKED"))
    return 0 if result["passed"] else 1


def cmd_register(args) -> int:
    text = _read(args.registry) if os.path.isfile(args.registry) else reg.SKELETON
    if args.path is not None:
        _write(args.registry, reg.append_attack_path(text, args.path))
        print("已追加攻击路径：%s" % args.path)
        return 0
    if not args.type:
        print("ERROR: register 需要 --type 或 --path", file=sys.stderr)
        return 2
    status = args.status or reg.DEFAULT_STATUS.get(args.type, "")
    dual = reg.DASH
    if args.type == "flag":
        if not args.flag_panel or not args.flag_shot:
            print("ERROR: flag 登记必须同时提供 --flag-panel 与 --flag-shot", file=sys.stderr)
            return 2
        dual = "面板=%s；截图=%s" % (args.flag_panel, args.flag_shot)
        if "proof.txt" in (args.content or "") and "仅可提交一次" not in dual:
            dual += "；仅可提交一次"
    row = reg.LootRow(
        id=args.id or _next_id(text), type=args.type,
        content=args.content or "", host=args.host or "",
        evidence=args.evidence or "", timestamp=args.timestamp or _now(),
        status=status, dual=dual)
    _write(args.registry, reg.append_row(text, row))
    print("已登记：%s" % row.id)
    return 0


def cmd_query(args) -> int:
    """查询登记行（SKILL loot-02.3：横向移动前查存活会话与有效凭据）。"""
    if not os.path.isfile(args.registry):
        print("ERROR: 登记簿不存在：%s" % args.registry, file=sys.stderr)
        return 2
    parsed = reg.parse_registry(_read(args.registry))
    if args.reusable:
        rows = reg.reusable_rows(parsed)
    else:
        rows = reg.query_rows(parsed, type_=args.type, status=args.status, host=args.host)
    if args.json:
        payload = [{"id": x.id, "type": x.type, "content": x.content,
                    "host": x.host, "status": x.status, "dual": x.dual} for x in rows]
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        if not rows:
            print("（无匹配登记行）")
        for x in rows:
            print("%s\t%s\t%s\t%s\t%s" % (x.id, x.type, x.content, x.host, x.status))
    return 0


def cmd_set_status(args) -> int:
    """原位更新状态并保留原行（SKILL「失败与豁免」：失效不得删除记录）。"""
    if not os.path.isfile(args.registry):
        print("ERROR: 登记簿不存在：%s" % args.registry, file=sys.stderr)
        return 2
    new_text, ok, msg = reg.update_status(_read(args.registry), args.id, args.status)
    if not ok:
        print("ERROR: %s" % msg, file=sys.stderr)
        return 1
    _write(args.registry, new_text)
    print(msg)
    return 0


def cmd_empty_state(args) -> int:
    """记录空态与原因（SKILL「失败与豁免」：空态本身即为有效产出）。"""
    text = _read(args.registry) if os.path.isfile(args.registry) else reg.SKELETON
    _write(args.registry, reg.mark_empty_state(text, args.reason))
    print("已记录空态原因：%s" % args.reason)
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="loot-manage", description="战利品登记簿工具")
    p.add_argument("--registry", default=None, help="登记簿路径（默认 <root>/loot/registry.md）")
    p.add_argument("--root", default=".", help="仓库根，用于解析证据片段路径（默认 .）")
    sub = p.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("init", help="初始化空登记簿")
    pi.add_argument("--force", action="store_true", help="覆盖已存在文件")

    pv = sub.add_parser("validate", help="校验登记簿质量门")
    pv.add_argument("--json", action="store_true", help="输出 JSON（verify-evidence 契约）")
    pv.add_argument("--require-loot", action="store_true", help="空态即失败（缺口信号）")
    pv.add_argument("--check-pieces", action="store_true", help="校验证据片段三件套")

    pr = sub.add_parser("register", help="登记一行或一条攻击路径")
    pr.add_argument("--type", choices=sorted(reg.TYPES))
    pr.add_argument("--content")
    pr.add_argument("--host")
    pr.add_argument("--evidence")
    pr.add_argument("--status")
    pr.add_argument("--flag-panel")
    pr.add_argument("--flag-shot")
    pr.add_argument("--id")
    pr.add_argument("--timestamp")
    pr.add_argument("--path", help="攻击路径行（与 --type 互斥）")

    pq = sub.add_parser("query", help="查询登记行（横向复用）")
    pq.add_argument("--type", choices=sorted(reg.TYPES))
    pq.add_argument("--status", help="按状态筛选（如 存活 / 有效）")
    pq.add_argument("--host", help="按来源主机筛选")
    pq.add_argument("--reusable", action="store_true",
                    help="仅返回可复用项（凭据=有效 / 会话=存活）")
    pq.add_argument("--json", action="store_true", help="输出 JSON")

    ps = sub.add_parser("set-status", help="原位更新某行状态（失效时保留原行）")
    ps.add_argument("--id", required=True, help="登记编号，如 L-3")
    ps.add_argument("--status", required=True, help="目标状态（须与类型匹配）")

    pe = sub.add_parser("empty-state", help="记录无战利品的空态与原因")
    pe.add_argument("--reason", required=True, help="空态原因（如 目标不可达）")
    return p


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if not args.registry:
        args.registry = os.path.join(args.root, "loot", "registry.md")
    if args.cmd == "init":
        return cmd_init(args)
    if args.cmd == "validate":
        return cmd_validate(args)
    if args.cmd == "register":
        return cmd_register(args)
    if args.cmd == "query":
        return cmd_query(args)
    if args.cmd == "set-status":
        return cmd_set_status(args)
    if args.cmd == "empty-state":
        return cmd_empty_state(args)
    return 2


if __name__ == "__main__":
    sys.exit(main())
