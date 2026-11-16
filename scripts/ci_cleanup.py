#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""CI/CD 流水线标准化清理器（仅标准库，对齐 ADR-0003）。

安全不变量（任何一条被破坏即拒绝动作，宁可漏清不可误删）：

  1. 默认 dry-run；只有显式 --apply 才真正删除。
  2. 白名单清理：仅匹配 CACHE_*/BUILD_*/EGG_INFO 的**未跟踪**路径可删除。
  3. 保留清单优先：.git、工作区记忆、运行数据、依赖目录、dist 交付物默认保留。
  4. git 跟踪的文件永不删除；目录内存在任一被跟踪文件时，整目录受保护。
  5. 符号链接不跟随、不删除其目标；realpath 越出根路径的候选一律跳过。
  6. 幂等：候选不存在记为 absent，重复执行不再删除、不报错。

阶段（phase）：
  pre     阶段开始前清陈年缓存与临时文件（绝不触碰 dist 交付物）
  post    阶段结束后清理，--status 记录 success/failure/cancel 结局
  verify  只读核验：清理范围内无残留 + --keep 指定交付物仍然存在

退出码：0 = 通过；1 = verify 发现残留或交付物缺失；2 = 参数/执行错误。
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Iterable

# —— 必须保留（永不清理）：源码/配置/依赖/运行数据/交付物 ——
# 说明：dist 仅在 post 阶段且显式 --clean-dist 时，按 DIST_FILE_NAMES 精确清理。
PROTECTED_TOPLEVEL = frozenset({
    ".git", ".workbuddy", "evidence", "loot", "dist", ".env",
    ".venv", "venv", "node_modules", "site-packages", ".tox", ".nox",
})

# —— 可清理：Python/测试/覆盖率缓存（未跟踪时才生效） ——
CACHE_DIR_NAMES = frozenset({
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "htmlcov",
})
BUILD_DIR_NAMES = frozenset({"build"})
EGG_INFO_SUFFIX = ".egg-info"
CACHE_FILE_NAMES = frozenset({".coverage", "coverage.xml"})
CACHE_FILE_PREFIXES = (".coverage.",)
CACHE_FILE_SUFFIXES = (".pyc", ".pyo")

# —— 仅 post + --clean-dist 允许的已知构建输出 ——
DIST_FILE_NAMES = frozenset({
    "redteam-ai300-skills.tgz", "redteam-ai300-skills.tgz.sha256",
})

VALID_PHASES = ("pre", "post", "verify")
VALID_STATUS = ("success", "failure", "cancelled", "skipped")


@dataclasses.dataclass(frozen=True)
class Candidate:
    path: Path
    scope: str  # workspace | temp
    kind: str   # dir | file | target


def _rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return os.path.relpath(str(path), str(root)).replace(os.sep, "/")


def _within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def load_tracked(root: Path) -> tuple[set[str], bool]:
    """读取 git 跟踪路径（POSIX 相对路径）。返回 (集合, 是否成功读取)。"""
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z"],
            capture_output=True, check=False,
        )
    except OSError:
        return set(), False
    if proc.returncode != 0:
        return set(), False
    tracked = set()
    for raw in proc.stdout.split(b"\x00"):
        if raw:
            tracked.add(raw.decode("utf-8", "replace").replace(os.sep, "/"))
    return tracked, True


def has_tracked_under(rel: str, tracked: set[str]) -> bool:
    """目录自身或其任一后代被跟踪时为 True（整目录受保护）。"""
    if rel in tracked:
        return True
    prefix = rel.rstrip("/") + "/"
    return any(p.startswith(prefix) for p in tracked)


def _cleanable_file(name: str, rel: str, allow_dist: bool) -> bool:
    top = rel.split("/")[0]
    if top == "dist":
        # dist 默认整体保留；仅 post + --clean-dist 时按已知输出精确清理。
        return bool(allow_dist and name in DIST_FILE_NAMES)
    if top in PROTECTED_TOPLEVEL:
        return False
    return (
        name in CACHE_FILE_NAMES
        or name.startswith(CACHE_FILE_PREFIXES)
        or name.endswith(CACHE_FILE_SUFFIXES)
    )


def enumerate_workspace(
    root: Path, tracked: set[str], allow_dist: bool
) -> tuple[list[Candidate], list[tuple[str, str]]]:
    """枚举工作区内可清理候选；返回 (候选, 跳过项[(路径, 原因)])。"""
    candidates: list[Candidate] = []
    skipped: list[tuple[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        base = Path(dirpath)
        # 1) 符号链接目录不入队、不跟随
        kept_dirs = []
        for name in dirnames:
            p = base / name
            if p.is_symlink():
                skipped.append((_rel(root, p), "symlink"))
            else:
                kept_dirs.append(name)
        dirnames[:] = kept_dirs
        # 2) 顶层保留目录整体剪枝（dist 在 post + --clean-dist 时允许下降，
        #    但仍只按 DIST_FILE_NAMES 精确匹配文件，不会整目录删除）。
        if base == root:
            dirnames[:] = [
                d for d in dirnames
                if d not in PROTECTED_TOPLEVEL or (d == "dist" and allow_dist)
            ]
        # 3) 目录候选（命中即剪枝，避免枚举其内部产生重复删除）
        for name in list(dirnames):
            p = base / name
            rel = _rel(root, p)
            if has_tracked_under(rel, tracked):
                continue
            if (name in CACHE_DIR_NAMES or name in BUILD_DIR_NAMES
                    or name.endswith(EGG_INFO_SUFFIX)):
                candidates.append(Candidate(p, "workspace", "dir"))
                dirnames.remove(name)
        # 4) 文件候选
        for name in filenames:
            p = base / name
            if p.is_symlink():
                skipped.append((_rel(root, p), "symlink"))
                continue
            rel = _rel(root, p)
            if has_tracked_under(rel, tracked):
                continue
            if _cleanable_file(name, rel, allow_dist):
                candidates.append(Candidate(p, "workspace", "file"))
    return candidates, skipped


def enumerate_temp(
    targets: Iterable[str], temp_roots: Iterable[Path]
) -> tuple[list[Candidate], list[tuple[str, str]]]:
    """枚举显式临时目标；越出 temp 根 / 符号链接 / temp 根自身一律跳过。"""
    roots = [Path(os.path.realpath(str(r))) for r in temp_roots]
    candidates: list[Candidate] = []
    skipped: list[tuple[str, str]] = []
    for raw in targets:
        p = Path(raw).expanduser()
        rp = Path(os.path.realpath(str(p)))
        if not any(_within(rp, r) for r in roots):
            skipped.append((str(p), "outside-temp-root"))
            continue
        if rp in roots:
            skipped.append((str(p), "temp-root-itself"))
            continue
        if p.is_symlink():
            skipped.append((str(p), "symlink"))
            continue
        if not p.exists():
            continue  # 幂等：不存在即无需清理
        candidates.append(Candidate(p, "temp", "target"))
    return candidates, skipped


def remove(
    candidates: Iterable[Candidate], dry_run: bool
) -> tuple[list[tuple[Candidate, str]], list[tuple[Candidate, str]]]:
    """执行删除；返回 (已处理[(候选,结果)], 失败[(候选,错误)])。"""
    removed: list[tuple[Candidate, str]] = []
    failed: list[tuple[Candidate, str]] = []
    for cand in candidates:
        if dry_run:
            removed.append((cand, "dry-run"))
            continue
        try:
            if cand.path.is_dir() and not cand.path.is_symlink():
                shutil.rmtree(cand.path)
            else:
                cand.path.unlink()
            removed.append((cand, "removed"))
        except OSError as exc:
            failed.append((cand, str(exc)))
    return removed, failed


def _audit_line(report: dict) -> str:
    return (
        "ci_cleanup[{phase}/{status}/{mode}]: workspace={w} temp={t} "
        "skipped={s} failed={f} residue={r} -> {verdict}"
    ).format(
        phase=report["phase"], status=report["status"], mode=report["mode"],
        w=len(report["workspace_removed"]), t=len(report["temp_removed"]),
        s=len(report["skipped"]), f=len(report["failed"]),
        r=len(report["residue"]), verdict=report["verdict"],
    )


def build_report(args: argparse.Namespace) -> tuple[dict, int]:
    root = Path(os.path.realpath(str(Path(args.root).expanduser())))
    temp_roots = [Path(os.path.realpath(str(Path(p).expanduser()))) for p in args.temp_root]
    tracked, tracked_ok = load_tracked(root)
    allow_dist = args.phase == "post" and args.clean_dist
    ws_cands, ws_skip = enumerate_workspace(root, tracked, allow_dist)
    tmp_cands, tmp_skip = enumerate_temp(args.temp_target, temp_roots)
    candidates = ws_cands + tmp_cands
    skipped = ws_skip + tmp_skip

    dry_run = args.phase != "verify" and not args.apply
    removed, failed = ([], []) if args.phase == "verify" else remove(candidates, dry_run)

    # verify 阶段：只读核验（重新枚举当前残留）+ 交付物存在性断言
    residue: list[dict] = []
    keep: list[dict] = []
    if args.phase == "verify":
        if not args.keep_only:
            ws_left, _ = enumerate_workspace(root, tracked, allow_dist)
            tmp_left, _ = enumerate_temp(args.temp_target, temp_roots)
            residue = [
                {"path": _rel(root, c.path) if c.scope == "workspace" else str(c.path),
                 "scope": c.scope, "kind": c.kind}
                for c in ws_left + tmp_left
            ]
        for raw in args.keep:
            p = Path(raw).expanduser()
            if not p.is_absolute():
                p = root / p  # 相对交付物路径按 --root 解析，不依赖进程 CWD
            resolved = Path(os.path.realpath(str(p)))
            present = p.exists() and _within(resolved, root)
            keep.append({"path": str(p), "present": bool(present)})

    residue_ok = not residue or (args.phase == "verify" and args.allow_residue)
    verdict = "PASS" if not failed and residue_ok and all(k["present"] for k in keep) else "FAIL"
    report = {
        "phase": args.phase,
        "status": args.status,
        "mode": "verify" if args.phase == "verify" else ("dry-run" if dry_run else "apply"),
        "root": str(root),
        "tracked_loaded": tracked_ok,
        "tracked_count": len(tracked),
        "workspace_removed": [
            {"path": _rel(root, c.path), "kind": c.kind, "result": result}
            for c, result in removed if c.scope == "workspace"
        ],
        "temp_removed": [
            {"path": str(c.path), "result": result}
            for c, result in removed if c.scope == "temp"
        ],
        "failed": [{"path": str(c.path), "error": err} for c, err in failed],
        "skipped": [{"path": p, "reason": reason} for p, reason in skipped],
        "residue": residue,
        "residue_allowed": bool(residue and residue_ok),
        "keep": keep,
        "verdict": verdict,
    }
    code = 1 if verdict == "FAIL" else 0
    return report, code


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="CI/CD 标准化清理器（默认 dry-run；白名单 + 保留清单双保险）"
    )
    ap.add_argument("phase", choices=VALID_PHASES, help="pre / post / verify")
    ap.add_argument("--root", default=str(Path(__file__).resolve().parent.parent),
                    help="工作区根（默认脚本所在仓库根）")
    ap.add_argument("--temp-root", action="append", default=[],
                    help="允许的临时根，可重复；默认追加系统临时目录")
    ap.add_argument("--temp-target", action="append", default=[],
                    help="显式临时目标路径，可重复；必须落在某个 temp-root 内")
    ap.add_argument("--keep", action="append", default=[],
                    help="verify 阶段断言存在的交付物路径，可重复")
    ap.add_argument("--keep-only", action="store_true",
                    help="verify 阶段只断言 --keep 交付物，不检查残留（用于交付物门禁）")
    ap.add_argument("--allow-residue", action="store_true",
                    help="verify 阶段发现残留仅告警不失败（dry-run 审计模式）")
    ap.add_argument("--apply", action="store_true", help="真正删除（缺省仅报告）")
    ap.add_argument("--clean-dist", action="store_true",
                    help="仅 post 生效：清理 dist/ 中已知构建输出（须在产物上传之后）")
    ap.add_argument("--status", default="success", choices=VALID_STATUS,
                    help="审计用的作业结局（success/failure/cancelled/skipped）")
    ap.add_argument("--json", action="store_true", help="输出机器可读 JSON 报告")
    ap.add_argument("--verbose", action="store_true", help="输出逐项明细")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.temp_root:
        args.temp_root = [tempfile.gettempdir()]
    else:
        args.temp_root = list(dict.fromkeys(args.temp_root + [tempfile.gettempdir()]))
    if args.clean_dist and args.phase != "post":
        print("错误：--clean-dist 仅允许在 post 阶段使用。", file=sys.stderr)
        return 2

    try:
        report, code = build_report(args)
    except (OSError, ValueError) as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(_audit_line(report))
        if args.verbose:
            for item in report["workspace_removed"] + report["temp_removed"]:
                print("  - %s (%s)" % (item["path"], item["result"]))
            for item in report["skipped"]:
                print("  ! 跳过 %s (%s)" % (item["path"], item["reason"]))
            for item in report["failed"]:
                print("  x 失败 %s (%s)" % (item["path"], item["error"]))
            for item in report["residue"]:
                print("  x 残留 %s (%s)" % (item["path"], item["scope"]))
            for item in report["keep"]:
                print("  %s 交付物 %s" % ("OK" if item["present"] else "缺失", item["path"]))
    return code


if __name__ == "__main__":
    raise SystemExit(main())
