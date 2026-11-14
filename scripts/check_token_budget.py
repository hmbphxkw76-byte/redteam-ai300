#!/usr/bin/env python3
"""全项目 token 预算检查器（标准库，零外部依赖，对齐 ADR-0003 / CI 密闭）。

用途：
  --report   输出受管文本的字节数、估算 token、重复块统计（不阻断）
  --check    静态层：BUDGETS 超限 + 规范契约锚点缺失，任一命中退出码 1（CI S1 门禁）
  --artifact KIND PATH   动态层：按 C4 判定仓库外产物上限，超限退出码 1
  --local    附带报告本地记忆文件体积与 C7 蒸馏状态（gitignore，CI 不可见）
  --strict-duplication  重复块也作为阻断项（默认仅告警）

三层保障模型见 docs/governance/adr/0005-token-budget-discipline.md。

估算口径（保守近似，非计费值，仅用于相对比较与回归判定）：
  CJK / 全角字符 ≈ 1 token/字符；其余字符 ≈ 4 字符/token。
事实唯一来源：AGENTS.md「Token 预算纪律」；本脚本不定义流程语义。
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# 单一事实源：产物字节上限。显式路径优先于通配（按 dict 插入顺序首个命中生效）。
# 上限取「当前基线 + 必要增量」，语义是「禁止无约束增长」，不要求删除既有内容。
BUDGETS: dict[str, int] = {
    "AGENTS.md": 6000,
    "GLOSSARY.md": 9000,
    "docs/governance/GOVERNANCE.md": 17000,
    "docs/operations/skill-mainline-workflow.md": 28000,
    "docs/standards/cross-ide-mainline-workflow.md": 30000,
    # 11000 → 12000：S1 由 4 项扩为 6 项、S4 增加契约复核，均为已记录的合法增量；
    # 压缩后实测 10,971 字节，保留约 1KB 余量以容纳后续门禁条目。
    "docs/standards/CI-CD.md": 12000,
    "docs/skill-specs-backlog.md": 14000,
    "skills/report-exam/SKILL.md": 21000,
    "docs/research/*.md": 16000,
    "docs/operations/*.md": 17000,
    "docs/governance/adr/*.md": 8000,
    "skills/*/SKILL.md": 12000,
}

MANAGED_GLOBS = (
    "AGENTS.md",
    "GLOSSARY.md",
    "docs/**/*.md",
    "skills/**/*.md",
)

MIN_DUP_CHARS = 240  # 小于此长度的段落不计入重复块，避免模板句式噪声

# 冷备文档：默认不随会话加载，仅在迁移 / 审计 / 取证时按路径按需读取（AGENTS.md C3）。
COLD_GLOBS = (
    "docs/standards/cross-ide-mainline-workflow.md",
    "docs/standards/prompts/*.md",  # 11 阶段独立提示词：按 C3 单文件按需取用（README §1）
    "docs/skill-specs-backlog.md",
    "docs/operations/pyrit-implementation-workflow.md",
    "docs/operations/attack-ai-agent-implementation.md",
    "docs/research/pyrit-native-api-attack-ai-agent.md",
    "docs/research/pyrit-v110-api-verification.md",
    "skills/report-exam/templates/*.md",
    "skills/attack-rag/examples/*.md",
    ".workbuddy/memory/2026-*.md",  # 本地日志（gitignore，由 --local 单独报告）
)


# C4 动态产物上限（字节）。这些产物不在仓库内，由 --artifact 在 PR / 本地流程中判定。
ARTIFACT_LIMITS: dict[str, int] = {
    "spec-v1": 8000,
    "spec-v2": 10000,
    "gate-record": 2000,
    "pr-body": 3000,
    "issue-summary": 400,
    "agent-brief": 1000,
}

# 规范契约：防止「规范被删除 / 迁移未同步，而 CI 仍全绿」。每项为 (相对路径, 必须存在的锚点文本)。
CONTRACTS: tuple[tuple[str, str], ...] = (
    ("AGENTS.md", "## Token 预算纪律"),
    ("AGENTS.md", "**C8 不可豁免"),
    ("AGENTS.md", "C1–C8"),
    ("docs/operations/skill-mainline-workflow.md", "### 2.4 Token 预算约束"),
    ("docs/standards/CI-CD.md", "check_token_budget.py"),
    ("docs/standards/cross-ide-mainline-workflow.md", "C1–C8"),
    ("docs/governance/adr/0005-token-budget-discipline.md", "Accepted"),
    (".github/workflows/ci.yml", "check_token_budget.py --check"),
    (".github/workflows/ci.yml", "globs: |"),  # 逐行分隔；逗号分隔会静默匹配 0 文件
    (".github/workflows/ci.yml", "branches: ['**']"),  # feature 分支 push 亦触发门禁
    (".github/workflows/ci.yml", "PR_BODY"),  # C4 对 PR 正文的自动判定
    (".github/workflows/ci.yml", "Token 预算与规范契约复核 (S4)"),
    (".markdownlint-cli2.jsonc", "ignores"),  # 官方报告模板豁免
    ("scripts/check_token_budget.py", "ARTIFACT_LIMITS"),
)


def is_cold(rel: str) -> bool:
    return any(fnmatch.fnmatch(rel, pattern) for pattern in COLD_GLOBS)


def check_artifact(kind: str, path: Path) -> tuple[bool, int, int]:
    """C4 动态产物判定，返回 (是否合格, 实际字节, 上限字节)。"""
    if kind not in ARTIFACT_LIMITS:
        raise KeyError(f"未知产物类型 {kind}；可选：{', '.join(ARTIFACT_LIMITS)}")
    cap = ARTIFACT_LIMITS[kind]
    size = len(path.read_bytes())
    return size <= cap, size, cap


def check_contracts(root: Path = ROOT) -> list[str]:
    """静态层契约检查，返回缺失项描述列表；空列表表示契约齐全。"""
    missing: list[str] = []
    for rel, needle in CONTRACTS:
        path = root / rel
        if not path.is_file():
            missing.append(f"文件不存在：{rel}")
            continue
        if needle not in path.read_text(encoding="utf-8"):
            missing.append(f"缺锚点：{rel} 未包含「{needle}」")
    return missing


def estimate_tokens(text: str) -> int:
    """保守估算 token 数：CJK 按 1 字符/token，其余按 4 字符/token。"""
    wide = sum(1 for ch in text if ord(ch) > 0x2E7F)
    narrow = len(text) - wide
    return wide + (narrow + 3) // 4


def managed_files() -> list[Path]:
    seen: set[str] = set()
    out: list[Path] = []
    for pattern in MANAGED_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT).as_posix()
            if rel not in seen:
                seen.add(rel)
                out.append(path)
    return out


def budget_for(rel: str) -> int | None:
    for pattern, cap in BUDGETS.items():
        if fnmatch.fnmatch(rel, pattern):
            return cap
    return None


def normalize_block(block: str) -> str:
    return " ".join(block.split())


def duplicate_blocks(files: list[Path]) -> tuple[int, list[tuple[str, int, list[str]]]]:
    """返回 (重复浪费字符数, [(指纹, 单块字符数, 命中文件列表)...])。"""
    index: dict[str, tuple[int, list[str]]] = {}
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        for raw in text.split("\n\n"):
            block = normalize_block(raw)
            if len(block) < MIN_DUP_CHARS:
                continue
            digest = hashlib.sha256(block.encode("utf-8")).hexdigest()[:12]
            chars, owners = index.get(digest, (len(block), []))
            if rel not in owners:
                owners.append(rel)
            index[digest] = (chars, owners)
    hits = [(digest, chars, owners) for digest, (chars, owners) in index.items() if len(owners) > 1]
    hits.sort(key=lambda item: item[1] * (len(item[2]) - 1), reverse=True)
    wasted = sum(chars * (len(owners) - 1) for _, chars, owners in hits)
    return wasted, hits


def print_report(files: list[Path], show_all: bool) -> tuple[list[tuple[str, int, int]], int, int, int]:
    over: list[tuple[str, int, int]] = []
    total_bytes = 0
    total_tokens = 0
    cold_tokens = 0
    cold_count = 0
    rows: list[tuple[str, int, int, str]] = []
    for path in files:
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        size = len(text.encode("utf-8"))
        tokens = estimate_tokens(text)
        total_bytes += size
        total_tokens += tokens
        if is_cold(rel):
            cold_tokens += tokens
            cold_count += 1
        cap = budget_for(rel)
        status = "-" if cap is None else ("OK" if size <= cap else "OVER")
        if status == "OVER":
            assert cap is not None
            over.append((rel, size, cap))
        rows.append((rel, size, tokens, status))

    print(f"{'文件':<58} {'字节':>8} {'≈token':>9} {'上限/状态':>12}")
    print("-" * 92)
    for rel, size, tokens, status in rows:
        cap = budget_for(rel)
        cap_text = "-" if cap is None else (f"{cap} / {status}")
        if show_all or status == "OVER" or size >= 12000:
            print(f"{rel:<58} {size:>8} {tokens:>9} {cap_text:>12}")
    print("-" * 92)
    print(f"合计 {len(files)} 个受管文件：{total_bytes} 字节，约 {total_tokens} token（估算）")
    ratio = 100.0 * cold_tokens / total_tokens if total_tokens else 0.0
    print(
        f"冷备文档 {cold_count} 个：约 {cold_tokens} token（占 {ratio:.1f}%）；"
        "按 C3 默认不进入会话上下文"
    )
    return over, total_bytes, total_tokens, cold_tokens


LOCAL_MEMORY_LIMIT_BYTES = 24000  # AGENTS.md C7：单日日志达 24KB 触发主题蒸馏


def report_local_memory() -> int:
    """报告本地记忆文件体积（.workbuddy/ 被 gitignore，故不进入 CI 预算判定）。"""
    mem = ROOT / ".workbuddy" / "memory"
    files = sorted(mem.glob("*.md")) if mem.is_dir() else []
    if not files:
        print("\n本地记忆：目录不存在或无 .md 文件。")
        return 0
    flagged = 0
    print("\n本地记忆（不计入 CI 预算，按 C7 蒸馏）：")
    for path in files:
        size = path.stat().st_size
        tokens = estimate_tokens(path.read_text(encoding="utf-8"))
        mark = ""
        if size > LOCAL_MEMORY_LIMIT_BYTES and path.name != "MEMORY.md":
            mark = "  ← 超 24KB，按 C3 冷备；持久事实见 MEMORY.md 主题索引"
            flagged += 1
        print(f"  {path.name:<28} {size:>8} 字节  ≈{tokens:>6} token{mark}")
    if flagged:
        print(
            f"  C7 状态：{flagged} 个日志超阈值，持久事实已蒸馏进 MEMORY.md；"
            "原日志保持 append-only 并作冷备，不进入默认上下文。"
        )
    return flagged


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="全项目 token 预算检查器")
    parser.add_argument("--report", action="store_true", help="输出度量报告（默认动作）")
    parser.add_argument("--check", action="store_true", help="按 BUDGETS 判定超限，超限退出码 1")
    parser.add_argument("--all", action="store_true", help="列出全部文件（默认仅列大文件与超限项）")
    parser.add_argument("--strict-duplication", action="store_true", help="重复块作为阻断项")
    parser.add_argument("--local", action="store_true", help="附带报告本地记忆文件体积与 C7 蒸馏状态")
    parser.add_argument(
        "--artifact", nargs=2, metavar=("KIND", "PATH"),
        help=f"判定 C4 动态产物上限；KIND ∈ {', '.join(ARTIFACT_LIMITS)}",
    )
    args = parser.parse_args(argv)

    if args.artifact:
        kind, raw = args.artifact
        try:
            ok, size, cap = check_artifact(kind, Path(raw))
        except (KeyError, OSError) as exc:
            print(f"结论：BLOCKED（{exc}）")
            return 1
        print(f"C4 产物判定：{kind} · {raw} · {size}/{cap} 字节 · {'PASS' if ok else 'BLOCKED'}")
        return 0 if ok else 1

    files = managed_files()
    over, total_bytes, total_tokens, cold_tokens = print_report(files, args.all)
    wasted, hits = duplicate_blocks(files)
    print(f"重复块（≥{MIN_DUP_CHARS} 字符，跨文件）：{len(hits)} 组，冗余约 {wasted} 字符")
    for digest, chars, owners in hits[:5]:
        print(f"  [{digest}] {chars} 字符 × {len(owners)} 文件：{', '.join(owners[:3])}")

    failed = False
    missing = check_contracts() if args.check else []
    if args.check and over:
        failed = True
        print("\n超限项（BLOCKED）：")
        for rel, size, cap in over:
            print(f"  {rel}: {size} > {cap} 字节（+{size - cap}）")
    if args.check and missing:
        failed = True
        print(f"\n规范契约缺失（BLOCKED，{len(missing)} 项）：")
        for item in missing:
            print(f"  {item}")
    if args.check:
        print(f"规范契约：{len(CONTRACTS)} 项锚点，缺失 {len(missing)} 项")
    if args.strict_duplication and hits:
        failed = True
        print(f"\n重复块超限（BLOCKED）：{len(hits)} 组")
    if args.local:
        report_local_memory()
    if args.check and not failed:
        print("\n结论：PASS（产物预算 + 规范契约均齐全）")
    print(
        f"\n基线：{total_bytes} 字节 / 约 {total_tokens} token；"
        f"剔除冷备后默认热区约 {total_tokens - cold_tokens} token。口径见脚本头注。"
    )
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
