#!/usr/bin/env python3
"""三层隔离 ③ 共享检出锁：阻断多 worktree 并发修改共享文件 + 契约落后基线提示。

背景：本项目为多 worktree 并行沙箱，多个主线任务会同时修改同一批「共享文件」
（check_token_budget.py / measure_coverage.py / ci.yml / GLOSSARY.md 等）。若两个
worktree 各自改同一文件后分别提交，merge 到 main 时会产生内容冲突——本脚本在
提交/推送前检测这种「共享文件已被其他 worktree 改动」的并发风险并阻断。

契约漂移（新增）：共享工具 `tools/collect_evidence.py` 的契约由
`docs/contracts/collect_evidence.contract.md` 唯一登记，其 CHANGELOG 逐条记录
契约变更 commit。若某 worktree 的基线落后于某个契约变更 commit，且该 worktree
消费共享工具（skills/*/SKILL.md 引用 collect_evidence.py），则给出明确「契约冲突
提示」，避免「晚于契约变更合入的 skill 基于旧契约编码」的漂移（实证 PR #250→#230→#254）。

判定逻辑（保守、无网络依赖）：
  1. 对每个共享文件，比较「各 worktree 相对其自身基线（merge-base HEAD origin/main）
     的本地改动」；同一文件在 >=2 个 worktree 都被改动即判并发检出冲突。
  2. 对每个 worktree，取契约清单 CHANGELOG 的变更 commit，若存在「非该 worktree
     基线祖先」的变更 commit，且该 worktree 消费共享工具，则输出契约冲突提示。
仅标准库。用法：
  python scripts/checkout_lock.py --check [--base main] [--no-contract]
  退出码：0=安全；1=检测到并发共享文件改动 / 契约落后基线（阻断）；2=内部错误。
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import subprocess
import sys

# 默认共享文件清单（ADR 三层隔离约定的四类 + 契约漂移新增的契约文件）。
DEFAULT_SHARED_FILES = (
    "scripts/check_token_budget.py",
    "scripts/measure_coverage.py",
    ".github/workflows/ci.yml",
    "GLOSSARY.md",
    "tools/collect_evidence.py",
    "docs/contracts/collect_evidence.contract.md",
)

CONTRACT_MANIFEST = "docs/contracts/collect_evidence.contract.md"
CHANGE_RE = re.compile(r"commit:`([0-9a-f]{7,40})`\s+PR:#?(\d+)")


def _parse_change_commits(text: str) -> list[tuple[str, str]]:
    """从契约清单文本解析 [(commit, pr)]（纯函数，供单测与落后基线检测复用）。"""
    return CHANGE_RE.findall(text)


def _git_env() -> dict[str, str]:
    """隔离 git 环境变量。

    pre-push hook 运行时 git 会注入 GIT_DIR / GIT_WORK_TREE / GIT_INDEX_FILE /
    GIT_PREFIX。若继承这些变量，每个 `git -C <worktree>` 仍指向调用 push 的那个
    worktree 的仓库，导致「所有 worktree 都被判改动同一文件」的假阳性（实证：
    在 worktree 内 push 时 lock 误报 GLOSSARY.md 被 7 个 worktree 改动）。
    此处构造干净环境，让 `-C` 按各 worktree 自身仓库解析。
    """
    env = dict(os.environ)
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_PREFIX", "GIT_COMMON_DIR"):
        env.pop(key, None)
    return env


def _run(cmd: list[str], cwd: str | None = None, check: bool = True) -> subprocess.CompletedProcess:
    # 固定 UTF-8：Git 输出为 UTF-8，Windows 默认按 GBK 解码会把中文 worktree
    # 路径解成乱码，CreateProcess(cwd=...) 随即报 NotADirectoryError。
    proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=_git_env())
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


def _origin_main(base: str) -> str:
    """origin/<base> 的 commit。"""
    proc = _run(["git", "rev-parse", "origin/%s" % base], check=False)
    if proc.returncode == 0:
        return proc.stdout.strip()
    proc = _run(["git", "merge-base", "HEAD", "origin/HEAD"], check=False)
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip()
    raise RuntimeError("无法确定基线 commit（origin/%s 与 origin/HEAD 均不可用）" % base)


def _wt_base(worktree: str, origin_main: str) -> str:
    """该 worktree 自身基线 = merge-base(HEAD, origin/main)；回退 HEAD 再回退 origin/main。"""
    proc = _run(["git", "merge-base", "HEAD", origin_main], cwd=worktree, check=False)
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip()
    proc = _run(["git", "rev-parse", "HEAD"], cwd=worktree, check=False)
    if proc.returncode == 0 and proc.stdout.strip():
        return proc.stdout.strip()
    return origin_main


def _is_ancestor(commit: str, base_commit: str, worktree: str) -> bool:
    """commit 是否为 base_commit 的祖先（即 commit 在 worktree 基线之前已存在）。"""
    proc = _run(["git", "merge-base", "--is-ancestor", commit, base_commit],
                cwd=worktree, check=False)
    return proc.returncode == 0


def _modified_in(worktree: str, shared: tuple[str, ...], base_commit: str) -> set[str]:
    """返回该 worktree 中，相对其自身 base_commit 有本地改动的共享文件集合。"""
    changed: set[str] = set()
    for f in shared:
        # 该文件在 worktree 中是否存在？
        exists = _run(["git", "ls-files", "--error-unmatch", f], cwd=worktree, check=False)
        if exists.returncode != 0:
            continue
        # 与自身基线比较（工作树 vs 自身基线 blob），而非统一 origin/main，
        # 避免「落后基线 worktree 因 main 已前进而被误判为本地改动」。
        diff = _run(["git", "diff", "--quiet", base_commit, "--", f], cwd=worktree, check=False)
        if diff.returncode != 0:
            changed.add(f)
    return changed


def _consumes_contract(worktree: str) -> bool:
    """该 worktree 是否消费共享工具（skills/*/SKILL.md 引用 collect_evidence.py）。"""
    for sk in glob.glob(os.path.join(worktree, "skills", "*", "SKILL.md")):
        try:
            with open(sk, encoding="utf-8") as fh:
                if "collect_evidence.py" in fh.read():
                    return True
        except OSError:
            continue
    return False


def _has_unmerged_work(worktree: str, origin_main: str) -> bool:
    """HEAD 非 origin/main 祖先 = 仍有未合并提交（非已合并的僵尸 worktree）。"""
    proc = _run(["git", "rev-parse", "HEAD"], cwd=worktree, check=False)
    if proc.returncode != 0 or not proc.stdout.strip():
        return False
    return not _is_ancestor(proc.stdout.strip(), origin_main, worktree)


def _contract_change_commits(origin_main: str) -> list[tuple[str, str]]:
    """从 origin/main 的契约清单 CHANGELOG 读取 [(commit, pr)]。"""
    proc = _run(["git", "show", "%s:%s" % (origin_main, CONTRACT_MANIFEST)], check=False)
    if proc.returncode != 0:
        return []
    return _parse_change_commits(proc.stdout)


def check(shared: tuple[str, ...], base: str, with_contract: bool = True) -> int:
    worktrees = _worktrees()
    origin_main = _origin_main(base)

    # —— ① 并发共享文件改动（相对各 worktree 自身基线） ——
    offenders: dict[str, list[str]] = {}
    for wt in worktrees:
        wt_base = _wt_base(wt, origin_main)
        for f in _modified_in(wt, shared, wt_base):
            offenders.setdefault(f, []).append(wt)
    conflicts = {f: wts for f, wts in offenders.items() if len(wts) >= 2}

    # —— ② 契约落后基线（仅当 worktree 消费共享工具） ——
    lagging: list[tuple[str, list[tuple[str, str]]]] = []
    if with_contract:
        changes = _contract_change_commits(origin_main)
        for wt in worktrees:
            if not _has_unmerged_work(wt, origin_main):
                continue  # 已合并的僵尸 worktree：无待推送内容，不判落后
            wt_base = _wt_base(wt, origin_main)
            behind = [(c, pr) for c, pr in changes if not _is_ancestor(c, wt_base, wt)]
            if behind and _consumes_contract(wt):
                lagging.append((wt, behind))

    if not conflicts and not lagging:
        print("共享检出锁：通过（无并发修改共享文件、无契约落后基线）。")
        return 0

    blocked = False
    if conflicts:
        blocked = True
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
    if lagging:
        blocked = True
        print("共享检出锁：检测到契约落后基线，阻断提交/推送（契约冲突提示）。", file=sys.stderr)
        for wt, behind in sorted(lagging):
            print("  - %s 的基线落后于 %d 个契约变更：" % (wt, len(behind)), file=sys.stderr)
            for c, pr in behind:
                print("      commit %s（PR #%s）" % (c, pr), file=sys.stderr)
        print(
            "处置：先 `git merge origin/main`（或 rebase）到最新基线，再按契约清单 CHANGELOG "
            "逐条自查并断言消费语义（尤其 shot_status 三态），最后重新过本锁。"
            "契约清单：docs/contracts/collect_evidence.contract.md。",
            file=sys.stderr,
        )
    return 1


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="三层隔离 ③：共享检出锁")
    ap.add_argument("--check", action="store_true", help="执行并发检出与契约落后基线检测")
    ap.add_argument("--base", default="main", help="基线分支（缺省 main）")
    ap.add_argument("--shared", nargs="*", default=None,
                    help="共享文件清单（缺省为内置默认六项）")
    ap.add_argument("--no-contract", action="store_true", help="跳过契约落后基线检测")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.check:
        build_parser().print_help()
        return 2
    shared = tuple(args.shared) if args.shared else DEFAULT_SHARED_FILES
    try:
        return check(shared, args.base, with_contract=not args.no_contract)
    except RuntimeError as exc:
        print("错误：%s" % exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
