#!/usr/bin/env python3
"""三层隔离 ① 分支隔离：主线任务的干净 worktree 编排。

用途：每个主线（/主线 [技能名]）任务应在独立 worktree + 独立 feat/* 分支上
落地，避免并行任务在共享工作树里互相污染共享文件（check_token_budget.py /
measure_coverage.py / ci.yml / GLOSSARY.md 等）。本脚本把这一纪律固化为可执行命令。

设计（对齐 ADR「三层隔离」）：
  - 分支隔离（本脚本）：`create` 用 `git worktree add --detach origin/main` 建干净
    基线，再 `checkout -b feat/<name>`；`list` 列出全部 worktree；`remove` 清理。
  - 串行合并（ci.yml concurrency + merge_group）：main 级合并串行化。
  - 共享检出锁（checkout_lock.py + pre-push hook）：阻断并发改共享文件。

仅标准库，无外部依赖。用法：
  python scripts/mainline_worktree.py create <skill-name> [--dir <path>]
  python scripts/mainline_worktree.py list
  python scripts/mainline_worktree.py remove <path> [--force]
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys

# 缺省 worktree 根目录（与既有并行工作树 /d/_*_wt 约定一致）。
DEFAULT_WORKTREE_ROOT = "D:/" if os.name == "nt" else "/"


def _run(cmd: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise RuntimeError(
            "命令失败: %s\n%s\n%s" % (" ".join(cmd), proc.stdout, proc.stderr)
        )
    return proc


def _branch_for(skill: str) -> str:
    """技能名 → 分支名。非法字符替换为 '-'，确保是合法 ref。"""
    safe = "".join(c if (c.isalnum() or c in "-_") else "-" for c in skill)
    safe = safe.strip("-")
    if not safe:
        raise ValueError("技能名无法映射为合法分支名: %r" % skill)
    return "feat/%s" % safe


def cmd_create(skill: str, directory: str | None, base: str) -> int:
    """建干净 worktree（origin/main）+ 切 feat/<skill> 分支。"""
    branch = _branch_for(skill)
    if not directory:
        directory = os.path.join(DEFAULT_WORKTREE_ROOT, "_%s_wt" % skill.replace("/", "_"))
    directory = os.path.abspath(directory)

    # 0) 确认远端 main 存在并可 fetch。
    _run(["git", "fetch", "origin", base])

    # 1) 若目录已存在则报错（避免覆盖在制工作树）。
    if os.path.exists(directory):
        print("错误：目录已存在，拒绝覆盖：%s" % directory, file=sys.stderr)
        print("提示：用 `list` 查看既有 worktree，或换一个 --dir。", file=sys.stderr)
        return 1

    # 2) worktree add --detach origin/<base>。
    _run(["git", "worktree", "add", "--detach", directory, "origin/%s" % base])

    # 3) 在该 worktree 内建 feat 分支。
    _run(["git", "checkout", "-b", branch], cwd=directory)

    print("已创建隔离 worktree：%s" % directory)
    print("分支：%s（基线 origin/%s）" % (branch, base))
    print("下一步：cd %s 后按 11 阶段落地；完成后用 `remove` 清理。" % directory)
    return 0


def cmd_list() -> int:
    """列出全部 worktree + 分支 + HEAD。"""
    proc = _run(["git", "worktree", "list", "--porcelain"], check=False)
    # porcelain 输出按块解析：每块有 worktree/HEAD/branch 键。
    entries: list[dict[str, str]] = []
    cur: dict[str, str] = {}
    for line in proc.stdout.splitlines():
        if line == "":
            if cur:
                entries.append(cur)
                cur = {}
            continue
        if " " in line:
            key, _, val = line.partition(" ")
            cur[key] = val
    if cur:
        entries.append(cur)

    if not entries:
        print("(无 worktree)")
        return 0

    print("%-48s %-40s %s" % ("PATH", "BRANCH", "HEAD"))
    for e in entries:
        branch = e.get("branch", "(detached)")
        head = e.get("HEAD", "")[:12]
        print("%-48s %-40s %s" % (e.get("worktree", ""), branch, head))
    return 0


def cmd_remove(directory: str, force: bool) -> int:
    """清理 worktree（默认不强删未提交改动；目标已不存在视为幂等成功）。"""
    directory = os.path.abspath(directory)
    if not os.path.exists(directory):
        # 目录已不存在：可能已被合并分支删除连带清理。prune 残留元数据后幂等返回 0。
        _run(["git", "worktree", "prune"], check=False)
        print("worktree 已不存在（幂等）：%s" % directory)
        return 0
    args = ["git", "worktree", "remove"]
    if force:
        args.append("--force")
    args.append(directory)
    _run(args)
    _run(["git", "worktree", "prune"], check=False)
    print("已移除 worktree：%s" % directory)
    return 0


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="三层隔离 ①：主线任务干净 worktree 编排",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_create = sub.add_parser("create", help="建干净 worktree + feat/<skill> 分支")
    p_create.add_argument("skill", help="技能名（映射为 feat/<skill> 分支）")
    p_create.add_argument("--dir", default=None, help="worktree 路径（缺省 D:/_<skill>_wt）")
    p_create.add_argument("--base", default="main", help="基线分支（缺省 main）")

    sub.add_parser("list", help="列出全部 worktree")

    p_remove = sub.add_parser("remove", help="清理 worktree")
    p_remove.add_argument("directory", help="worktree 路径")
    p_remove.add_argument("--force", action="store_true", help="强删（含未提交改动）")

    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.cmd == "create":
            return cmd_create(args.skill, args.dir, args.base)
        if args.cmd == "list":
            return cmd_list()
        if args.cmd == "remove":
            return cmd_remove(args.directory, args.force)
    except RuntimeError as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return 1
    except ValueError as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
