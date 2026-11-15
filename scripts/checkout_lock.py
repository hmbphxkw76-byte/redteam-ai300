#!/usr/bin/env python3
"""三层隔离 ③ 共享检出锁：阻断多 worktree 并发修改共享文件。

背景：本项目为多 worktree 并行沙箱，多个主线任务会同时修改同一批「共享文件」
（check_token_budget.py / measure_coverage.py / ci.yml / GLOSSARY.md 等）。若两个
worktree 各自改同一文件后分别提交，merge 到 main 时会产生内容冲突——本脚本在
提交/推送前检测这种「共享文件已被其他 worktree 改动」的并发风险并阻断。

判定逻辑（保守、无网络依赖）：
  对每个共享文件，比较「当前 worktree 的本地改动」与「其他 worktree 的本地改动」，
  若同一文件在 >=2 个 worktree 里都相对 origin/main（或共同基线）产生了本地改动，
  即判定为并发检出冲突，输出并集提示并返回非 0。

仅标准库。用法：
  python scripts/checkout_lock.py --check [--base main]
  退出码：0=安全；1=检测到并发共享文件改动（阻断）；2=内部错误。
"""
from __future__ import annotations

import argparse
import subprocess
import sys

# 默认共享文件清单（ADR 三层隔离约定的四类，本会话踩坑对象）。
DEFAULT_SHARED_FILES = (
    "scripts/check_token_budget.py",
    "scripts/measure_coverage.py",
    ".github/workflows/ci.yml",
    "GLOSSARY.md",
)


def _run(cmd: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        raise RuntimeError(
            "命令失败: %s\n%s\n%s" % (" ".join(cmd), proc.stdout, proc.stderr)
        )
    return proc


def _worktrees() -> list[str]:
    """返回所有 worktree 路径（绝对路径）。"""
    proc = _run(["git", "worktree", "list", "--porcelain"])
    paths: list[str] = []
    for line in proc.stdout.splitlines():
        if line.startswith("worktree "):
            paths.append(line[len("worktree "):])
    return paths


def _base_commit(base: str) -> str:
    """origin/<base> 的 commit；无则回退 HEAD~ 基线。"""
    proc = _run(["git", "rev-parse", "origin/%s" % base], check=False)
    if proc.returncode == 0:
        return proc.stdout.strip()
    proc = _run(["git", "merge-base", "HEAD", "origin/HEAD"], check=False)
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip()
    raise RuntimeError("无法确定基线 commit（origin/%s 与 origin/HEAD 均不可用）" % base)


def _modified_in(worktree: str, shared: tuple[str, ...], base_commit: str) -> set[str]:
    """返回该 worktree 中，相对 base_commit 有本地改动的共享文件集合。"""
    changed: set[str] = set()
    for f in shared:
        # 该文件在 worktree 中是否存在？
        exists = _run(["git", "ls-files", "--error-unmatch", f], cwd=worktree, check=False)
        if exists.returncode != 0:
            continue
        # 与 base 比较（工作树 vs base 的 blob）。
        diff = _run(["git", "diff", "--quiet", base_commit, "--", f], cwd=worktree, check=False)
        if diff.returncode != 0:
            changed.add(f)
    return changed


def check(shared: tuple[str, ...], base: str) -> int:
    worktrees = _worktrees()
    base_commit = _base_commit(base)

    # 每个共享文件 → 哪些 worktree 改了它。
    offenders: dict[str, list[str]] = {}
    for wt in worktrees:
        for f in _modified_in(wt, shared, base_commit):
            offenders.setdefault(f, []).append(wt)

    conflicts = {f: wts for f, wts in offenders.items() if len(wts) >= 2}

    if not conflicts:
        print("共享检出锁：通过（无并发修改共享文件）。")
        return 0

    print("共享检出锁：检测到并发修改共享文件，阻断提交/推送。", file=sys.stderr)
    for f, wts in sorted(conflicts.items()):
        print("  - %s 被 %d 个 worktree 改动：" % (f, len(wts)), file=sys.stderr)
        for wt in wts:
            print("      %s" % wt, file=sys.stderr)
    print(
        "处置：先在单个 worktree 串行合入共享文件（取并集、预算取合并后实际内容+余量），"
        "再提交其余任务；禁止各自提交后靠 main 合并解冲突。",
        file=sys.stderr,
    )
    return 1


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="三层隔离 ③：共享检出锁")
    ap.add_argument("--check", action="store_true", help="执行并发检出检测")
    ap.add_argument("--base", default="main", help="基线分支（缺省 main）")
    ap.add_argument("--shared", nargs="*", default=None,
                    help="共享文件清单（缺省为内置默认四项）")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.check:
        build_parser().print_help()
        return 2
    shared = tuple(args.shared) if args.shared else DEFAULT_SHARED_FILES
    try:
        return check(shared, args.base)
    except RuntimeError as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
