#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""共享证据收集工具（P0 / 计分单元：通用）。

依据 GOVERNANCE.md 第六章「质量基线」把一次攻击步骤的输入打包为结构化
markdown 证据片段，服务全部 P0 攻击技能（`attack-ai-agent` / `attack-rag` /
`attack-mcp-tool` / `foothold-traditional` 等）的证据基线。

职责（In scope）
  - 将「确切命令 + 关键输出 + 截图（路径或钩子）+ AI 交互日志 + flag 双通道」
    渲染为一份可被 `report-exam` 的 Attack Walkthrough 小节直接复用、技术读者可
    copy/paste 逐步复现的 markdown 片段（§6.1 / §6.2 / §6.3 / §7.1 / §7.2）。
  - 片段内附「目标标识 + 时间戳 + 五件套（含三件套）齐全校验」表。

Out of scope
  - 不含任何实际攻击逻辑（留在各 SKILL.md 与攻击脚本）。
  - 不含截图捕获实现（仅接收截图路径或钩子命令，钩子由操作者另行执行）。

术语
  - 片段固定标签遵循 GLOSSARY.md（如「诱饵机」而非「蜜罐」）。
  - 对输入文本中的 `_Avoid_` 废弃术语作 stderr 预警（不阻断）。

退出码：0 = 成功；1 = 错误（缺必需输入 / 严格模式三件套不全 / 写入失败）；
2 = 用法错误。仅依赖 Python 标准库，本地与 CI 判定一致。
"""
import argparse
import os
import re
import sys
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLOSSARY_PATH = os.path.join(ROOT, "GLOSSARY.md")

# 三件套（§6.1，必需）：确切命令 + 关键输出 + 截图
REQUIRED_PIECES = ["确切命令", "关键输出", "截图"]
# 五件套 = 三件套 + AI 交互日志（§6.3）+ flag 双通道（§6.2），后两项可选
OPTIONAL_PIECES = ["AI 交互日志", "flag 双通道"]


def read_text(path):
    """以 UTF-8 读取文本文件，非法字节以替换符兜底，避免工具输出编码差异崩坏。"""
    with open(path, "rb") as f:
        return f.read().decode("utf-8", "replace")


def now():
    """返回当前本地时区时间（tz-aware）。"""
    return datetime.now().astimezone()


def parse_avoid_terms(glossary_path=GLOSSARY_PATH):
    """从 GLOSSARY.md 提取 `_Avoid_` 废弃术语（与 scripts/check_glossary.py 同源）。

    返回规范词之外、长度 >1 的废弃术语列表；术语表缺失时返回空表（不阻断）。
    """
    if not os.path.isfile(glossary_path):
        return []
    text = read_text(glossary_path)
    canonical = set()
    avoid = []
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"^\*\*(.+?)\*\*:", s)
        if m:
            canonical.add(m.group(1).strip())
            continue
        if s.startswith("_Avoid_:"):
            raw = s.split(":", 1)[1]
            for t in re.split(r"[、,/]", raw):
                t = re.sub(r"[（(].*?[)）]", "", t).strip().strip("`").strip()
                if len(t) > 1 and t not in canonical:
                    avoid.append(t)
    return avoid


def fence(text, lang=""):
    """用 Markdown 围栏包裹文本；围栏长度随内容内最长反引号串自适应，避免破坏围栏。"""
    longest = max([len(m) for m in re.findall(r"`+", text)] or [0])
    n = max(3, longest + 1)
    f = "`" * n
    return "%s%s\n%s\n%s" % (f, lang, text.rstrip("\n"), f)


def embed_path(path, out_path=None):
    """把截图路径转成适合 markdown 的引用：尽量相对输出文件所在目录，统一正斜杠。"""
    if not path:
        return path
    p = os.path.abspath(path)
    if out_path and out_path != "-":
        out_dir = os.path.dirname(os.path.abspath(out_path))
        try:
            rel = os.path.relpath(p, out_dir)
            # 仅当截图位于输出目录子树内时才用相对路径，避免 ".." 连串
            if rel != ".." and not rel.startswith(".." + os.sep):
                p = rel
        except ValueError:
            pass  # 跨盘符无法取相对路径，回退绝对路径
    return p.replace("\\", "/")


def build_fragment(step_id, command, output="", screenshot=None, shot_cmd=None,
                   ai_log="", flag="", target="", title="", timestamp=None,
                   out_path=None, avoid_terms=None):
    """渲染证据片段，返回 (markdown_text, report)。

    report 含：complete（三件套是否齐全）、missing（缺失项）、
    required_status / optional_status（逐项状态）、avoid_terms（输入中的废弃术语）。
    """
    timestamp = timestamp or now()
    avoid_terms = [] if avoid_terms is None else avoid_terms
    command = command or ""
    output = output or ""
    ai_log = ai_log or ""
    flag = flag or ""

    has_cmd = bool(command.strip())
    has_out = bool(output.strip())
    has_shot = bool(screenshot) or bool(shot_cmd)
    required_status = {
        "确切命令": has_cmd,
        "关键输出": has_out,
        "截图": has_shot,
    }
    optional_status = {
        "AI 交互日志": bool(ai_log.strip()),
        "flag 双通道": bool(flag.strip()),
    }
    complete = all(required_status.values())
    missing = [k for k in REQUIRED_PIECES if not required_status[k]]

    shot_missing = bool(screenshot) and not os.path.isfile(screenshot)

    blob = "\n".join([step_id, command, output, ai_log, flag, target, title])
    terms_found = [t for t in avoid_terms if t in blob]

    heading = "### 步骤 %s" % step_id
    if title:
        heading += "：%s" % title

    lines = [
        heading,
        "",
        "> **目标**：`%s`　|　**时间戳**：`%s`　|　**证据片段**（collect_evidence.py）"
        % (target or "（未指定）", timestamp.isoformat(timespec="seconds")),
        "",
        "#### 确切命令",
        "",
        fence(command, "bash") if has_cmd else "（未提供）",
        "",
        "#### 关键输出",
        "",
        fence(output, "text") if has_out else "（未提供）",
        "",
        "#### 截图（访问证明）",
        "",
    ]
    if has_shot:
        if screenshot:
            lines.append("![%s 截图](%s)" % (step_id, embed_path(screenshot, out_path)))
        if shot_cmd:
            lines.append("")
            lines.append("> 截图捕获钩子：`%s`（由操作者执行后落盘）" % shot_cmd)
        if shot_missing:
            lines.append("")
            lines.append("> 提示：截图文件未找到：`%s`（请确认已落盘）。" % screenshot)
    else:
        lines.append("（未提供）")

    if ai_log.strip():
        lines += ["", "#### AI 交互日志", "", fence(ai_log, "text")]
    if flag.strip():
        lines += ["", "#### flag 取证（双通道一致）", "", fence(flag, "text")]

    lines += ["", "#### 证据校验（五件套 / 三件套）", "",
              "| 证据项 | 必需 | 状态 |", "|---|---|---|"]
    for k in REQUIRED_PIECES:
        lines.append("| %s | 是 | %s |" % (k, "已提供" if required_status[k] else "缺失"))
    for k in OPTIONAL_PIECES:
        lines.append("| %s | 否 | %s |" % (k, "已提供" if optional_status[k] else "未提供"))
    lines.append("")
    if complete:
        lines.append("**三件套齐全**：是。")
    else:
        lines.append("**三件套齐全**：否（缺失：%s）。" % "、".join(missing))

    markdown = "\n".join(lines) + "\n"
    report = {
        "complete": complete,
        "missing": missing,
        "required_status": required_status,
        "optional_status": optional_status,
        "avoid_terms": terms_found,
        "shot_missing": shot_missing,
    }
    return markdown, report


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="把一次攻击步骤打包为结构化 markdown 证据片段（对齐 GOVERNANCE §质量门 / §6）。",
    )
    ap.add_argument("--step", required=True, help="步骤标识（step_id），如 recon-01")
    ap.add_argument("--cmd", required=True, help="确切命令（技术读者可直接 copy/paste）")
    ap.add_argument("--out", required=True, help="输出 markdown 路径；'-' 表示写 stdout")
    ap.add_argument("--output", "--stdout", dest="output", help="命令输出（关键输出，内联文本）")
    ap.add_argument("--output-file", help="命令输出文件（路径；'-' 表示读 stdin）")
    ap.add_argument("--screenshot", help="截图路径（本地文件）")
    ap.add_argument("--shot-cmd", help="截图捕获钩子命令（仅记录，不执行）")
    ap.add_argument("--ai-log", help="AI 交互日志（内联文本）")
    ap.add_argument("--ai-log-file", help="AI 交互日志文件（路径）")
    ap.add_argument("--flag", help="flag 双通道内容（面板提交 + 截图一致的 flag 值）")
    ap.add_argument("--target", default="", help="目标标识（主机/IP）")
    ap.add_argument("--title", default="", help="步骤标题（可选）")
    ap.add_argument("--append", action="store_true", help="追加到 --out 文件末尾（默认覆盖）")
    ap.add_argument("--strict", action="store_true", help="三件套不全时以退出码 1 失败（质量门强制）")
    ap.add_argument("--glossary", default=GLOSSARY_PATH, help="GLOSSARY.md 路径（术语预警来源）")
    args = ap.parse_args(argv)

    # —— 关键输出：内联 > 文件 > stdin ——
    output = ""
    if args.output_file == "-":
        output = sys.stdin.read()
    elif args.output_file:
        if not os.path.isfile(args.output_file):
            print("ERROR: 命令输出文件不存在：%s" % args.output_file, file=sys.stderr)
            return 1
        output = read_text(args.output_file)
    elif args.output:
        output = args.output

    # —— AI 交互日志 ——
    ai_log = ""
    if args.ai_log_file:
        if not os.path.isfile(args.ai_log_file):
            print("ERROR: AI 交互日志文件不存在：%s" % args.ai_log_file, file=sys.stderr)
            return 1
        ai_log = read_text(args.ai_log_file)
    elif args.ai_log:
        ai_log = args.ai_log

    avoid = parse_avoid_terms(args.glossary)
    markdown, report = build_fragment(
        step_id=args.step,
        command=args.cmd,
        output=output,
        screenshot=args.screenshot,
        shot_cmd=args.shot_cmd,
        ai_log=ai_log,
        flag=args.flag,
        target=args.target,
        title=args.title,
        out_path=args.out,
        avoid_terms=avoid,
    )

    for t in report["avoid_terms"]:
        print("WARN: 输入含废弃术语 %r，应改用 GLOSSARY.md 规范词（如「诱饵机」）。" % t,
              file=sys.stderr)

    if args.out == "-":
        sys.stdout.write(markdown)
    else:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        mode = "a" if args.append else "w"
        with open(args.out, mode, encoding="utf-8") as f:
            if args.append and os.path.exists(args.out) and os.path.getsize(args.out) > 0:
                f.write("\n")
            f.write(markdown)
        st = report["required_status"]
        print("已生成证据片段：%s" % args.out)
        print("三件套：命令[%s] 输出[%s] 截图[%s]" % (
            "已提供" if st["确切命令"] else "缺失",
            "已提供" if st["关键输出"] else "缺失",
            "已提供" if st["截图"] else "缺失",
        ))

    if not report["complete"]:
        # 诊断信息走 stderr，保证 `--out -` 时 stdout 仅含 markdown，可被下游直接消费
        print("提示：三件套不全（缺失：%s）。可用 --strict 强制失败。" % "、".join(report["missing"]),
              file=sys.stderr)
        if args.strict:
            print("ERROR: 严格模式，三件套不全（缺失：%s）。" % "、".join(report["missing"]),
                  file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
