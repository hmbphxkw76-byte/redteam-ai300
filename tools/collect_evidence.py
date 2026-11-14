#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""共享证据收集工具（P0 / 计分单元：通用）。

依据 GOVERNANCE.md 第六章「质量基线」把一次攻击/侦察步骤的输入打包为结构化
markdown 证据片段，服务全部 P0 技能（`recon-ai` / `attack-ai-agent` /
`attack-rag` / `attack-mcp-tool` / `foothold-traditional` 等）的证据基线。

职责（In scope）
  - 将「确切命令 + 关键输出 + 截图（路径或钩子）+ 脚本来源与修改说明 +
    AI 交互日志 + flag 双通道」渲染为一份可被 `report-exam` 的 Attack
    Walkthrough 小节直接复用、技术读者可 copy/paste 逐步复现的 markdown 片段
    （§6.1 / §6.2 / §6.3 / §7.1 / §7.2）。
  - 片段内附「目标标识 + 时间戳 + 执行分级 + 五件套（含三件套）齐全校验」表。
  - `--manifest` 追加一行 JSONL 证据清单记录（哈希 / 时间戳 / 留存入径 / 件套
    状态），使整份证据集可被独立复核，不依赖会话上下文。

Out of scope
  - 不含任何实际攻击逻辑（留在各 SKILL.md 与攻击脚本）。
  - 不含截图捕获实现（仅接收截图路径或钩子命令；钩子由操作者/上游编排执行）。

术语
  - 片段固定标签遵循 GLOSSARY.md（如「诱饵机」而非「蜜罐」）。
  - 对输入文本中的 `_Avoid_` 废弃术语作 stderr 预警（不阻断）。

退出码：0 = 成功；1 = 错误（缺必需输入 / 严格模式三件套不全 / 严格模式 flag
双通道不一致 / 写入失败）；2 = 用法错误。仅依赖 Python 标准库。
"""
import argparse
import hashlib
import json
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
# 官方文档要求「所用脚本或其来源 + 修改说明」（S1/S3 §1），无脚本时须显式声明
SCRIPT_PIECE = "脚本/PoC"


def read_text(path):
    """以 UTF-8 读取文本文件，非法字节以替换符兜底，避免工具输出编码差异崩坏。"""
    with open(path, "rb") as f:
        return f.read().decode("utf-8", "replace")


def now():
    """返回当前本地时区时间（tz-aware）。"""
    return datetime.now().astimezone()


def sha256_text(text):
    """文本证据指纹（UTF-8），用于证据清单的完整性校验。"""
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


def sha256_file(path):
    """文件证据指纹；文件不存在返回空串（不抛异常，交由调用方判定）。"""
    if not path or not os.path.isfile(path):
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


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


def _flag_dual(pair_flag, flag_panel, flag_shot):
    """解析 flag 双通道（§6.2）：面板提交值 vs 截图/正文值。

    `--flag` 为兼容旧调用的单值形式，等价于两个通道取同一值。
    返回 (panel, shot, status)，status ∈ {"一致", "不一致", "未提供"}。
    """
    panel = (flag_panel or "").strip()
    shot = (flag_shot or "").strip()
    legacy = (pair_flag or "").strip()
    if legacy:
        panel = panel or legacy
        shot = shot or legacy
    if not panel and not shot:
        return "", "", "未提供"
    if panel and shot and panel == shot:
        return panel, shot, "一致"
    return panel, shot, "不一致"


def build_fragment(step_id, command, output="", screenshot=None, shot_cmd=None,
                   ai_log="", flag="", flag_panel="", flag_shot="", target="",
                   title="", timestamp=None, out_path=None, avoid_terms=None,
                   script=None, script_src="", script_note="", profile="",
                   shot_kind="", note=""):
    """渲染证据片段，返回 (markdown_text, report)。

    report 含：complete（三件套是否齐全）、missing（缺失项）、
    required_status / optional_status（逐项状态）、avoid_terms（输入中的废弃术语）、
    script（脚本小节状态）、flag_status（双通道一致性）、hashes（证据指纹）。
    """
    timestamp = timestamp or now()
    avoid_terms = [] if avoid_terms is None else avoid_terms
    command = command or ""
    output = output or ""
    ai_log = ai_log or ""
    target = target or ""
    script = script or ""
    script_src = (script_src or "").strip()
    script_note = (script_note or "").strip()
    note = (note or "").strip()

    has_cmd = bool(command.strip())
    has_out = bool(output.strip())
    has_shot = bool(screenshot) or bool(shot_cmd)
    required_status = {
        "确切命令": has_cmd,
        "关键输出": has_out,
        "截图": has_shot,
    }
    panel, shot_value, flag_status = _flag_dual(flag, flag_panel, flag_shot)
    has_script = bool(script or script_src)
    optional_status = {
        "AI 交互日志": bool(ai_log.strip()),
        "flag 双通道": flag_status != "未提供",
    }
    complete = all(required_status.values())
    missing = [k for k in REQUIRED_PIECES if not required_status[k]]

    shot_missing = bool(screenshot) and not os.path.isfile(screenshot)

    blob = "\n".join([step_id, command, output, ai_log, flag, flag_panel,
                      flag_shot, target, title, script_src, script_note, note])
    terms_found = [t for t in avoid_terms if t in blob]

    heading = "### 步骤 %s" % step_id
    if title:
        heading += "：%s" % title

    meta_bits = "> **目标**：`%s`　|　**时间戳**：`%s`" % (
        target or "（未指定）", timestamp.isoformat(timespec="seconds"))
    if profile:
        meta_bits += "　|　**执行分级**：`%s`" % profile
    meta_bits += "　|　**证据片段**（collect_evidence.py）"

    lines = [
        heading,
        "",
        meta_bits,
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
            if shot_kind:
                lines.append("")
                lines.append("> 截图类型：`%s`（`url` = 目标页面直截；"
                             "`transcript` = 请求/响应转录页渲染）" % shot_kind)
        if shot_cmd:
            lines.append("")
            lines.append("> 截图捕获钩子：`%s`（由操作者执行后落盘）" % shot_cmd)
        if shot_missing:
            lines.append("")
            lines.append("> 提示：截图文件未找到：`%s`（请确认已落盘）。" % screenshot)
    else:
        lines.append("（未提供）")

    if note:
        # 分析注记独立成节：保证「关键输出」保持原始，不混入推断
        lines += ["", "#### 分析注记（可选）", "", note]

    # 脚本 / PoC 小节：官方要求「所用脚本须附来源链接或代码副本及修改说明」
    lines += ["", "#### 脚本 / PoC（来源与修改说明）", ""]
    if has_script:
        lines += ["| 项 | 内容 |", "|---|---|"]
        if script:
            digest = sha256_file(script)
            lines.append("| 本地副本 | `%s`（sha256: `%s`） |"
                         % (embed_path(script, out_path), digest or "（未找到）"))
        lines.append("| 来源 | %s |" % (script_src or "（未提供来源链接，使用本地副本）"))
        lines.append("| 修改说明 | %s |" % (script_note or "未做修改（原样使用）"))
    else:
        lines.append("未使用脚本：本步未登记脚本或 PoC 副本。")

    if ai_log.strip():
        lines += ["", "#### AI 交互日志", "", fence(ai_log, "text")]

    if flag_status != "未提供":
        # 标题与 fenced 原值块为下游契约（report_exam.index.parse_fragment 按此解析），
        # 双通道明细表附在其后；一致性状态以显式判据行给出，不改标题以免解析失效。
        lines += ["", "#### flag 取证（双通道一致）", "",
                  fence(panel or shot_value, "text"), ""]
        if flag_status == "不一致":
            lines += ["> **一致性判定**：不一致 —— 面板值与截图值不同，"
                      "按 §6.2 失分条款阻断提交。", ""]
        lines += ["| 通道 | 值 |", "|---|---|",
                  "| 控制面板提交值 | %s |" % (("`%s`" % panel) if panel else "（缺失）"),
                  "| 截图/正文中的值 | %s |" % (("`%s`" % shot_value) if shot_value else "（缺失）"),
                  "| 一致性 | **%s** |" % flag_status]

    lines += ["", "#### 证据校验（五件套 / 三件套）", "",
              "| 证据项 | 必需 | 状态 |", "|---|---|---|"]
    for k in REQUIRED_PIECES:
        lines.append("| %s | 是 | %s |" % (k, "已提供" if required_status[k] else "缺失"))
    for k in OPTIONAL_PIECES:
        lines.append("| %s | 否 | %s |" % (k, "已提供" if optional_status[k] else "未提供"))
    lines.append("| %s | 否 | %s |" % (SCRIPT_PIECE, "已提供" if has_script else "未使用脚本"))
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
        "script": has_script,
        "flag_status": flag_status,
        "hashes": {
            "output": sha256_text(output),
            "screenshot": sha256_file(screenshot),
            "script": sha256_file(script),
        },
    }
    return markdown, report


def build_manifest_record(step_id, command, report, timestamp, profile="",
                          retention="", target="", screenshot="", shot_kind="",
                          script=""):
    """构造证据清单行（JSONL）。字段集见 GLOSSARY「证据清单」与 AC-19。

    显式参数而非 argparse Namespace：格式与 CLI 解耦，便于被其它调用方复用。
    """
    return {
        "step_id": step_id,
        "command": command,
        "sha256": report["hashes"]["output"],
        "timestamp": timestamp.isoformat(timespec="seconds"),
        "profile": profile,
        "retention": retention,
        "target": target,
        "screenshot": screenshot,
        "screenshot_sha256": report["hashes"]["screenshot"],
        "shot_kind": shot_kind,
        "script": script,
        "script_sha256": report["hashes"]["script"],
        "pieces": {
            "确切命令": report["required_status"]["确切命令"],
            "关键输出": report["required_status"]["关键输出"],
            "截图": report["required_status"]["截图"],
            "AI 交互日志": report["optional_status"]["AI 交互日志"],
            "flag 双通道": report["optional_status"]["flag 双通道"],
            "脚本/PoC": report["script"],
        },
        "flag_dual": report["flag_status"],
        "complete": report["complete"],
    }


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="把一次攻击/侦察步骤打包为结构化 markdown 证据片段"
                    "（对齐 GOVERNANCE §质量门 / §6）。",
    )
    ap.add_argument("--step", required=True, help="步骤标识（step_id），如 recon-01")
    ap.add_argument("--cmd", required=True, help="确切命令（技术读者可直接 copy/paste）")
    ap.add_argument("--out", required=True, help="输出 markdown 路径；'-' 表示写 stdout")
    ap.add_argument("--output", "--stdout", dest="output", help="命令输出（关键输出，内联文本）")
    ap.add_argument("--output-file", help="命令输出文件（路径；'-' 表示读 stdin）")
    ap.add_argument("--screenshot", help="截图路径（本地文件）")
    ap.add_argument("--shot-cmd", help="截图捕获钩子命令（仅记录，不执行）")
    ap.add_argument("--shot-kind", choices=("url", "transcript"),
                    help="截图类型：url=目标页面直截；transcript=请求/响应转录页渲染")
    ap.add_argument("--script", help="所用脚本/PoC 本地副本路径（记录 sha256）")
    ap.add_argument("--script-src", help="脚本来源链接（官方要求二选一）")
    ap.add_argument("--script-note", help="对脚本所做修改的说明")
    ap.add_argument("--note", help="分析注记（与原始输出分离，避免污染证据原文）")
    ap.add_argument("--ai-log", help="AI 交互日志（内联文本）")
    ap.add_argument("--ai-log-file", help="AI 交互日志文件（路径）")
    ap.add_argument("--flag", help="flag 值（兼容形式：等价于面板值与截图值相同）")
    ap.add_argument("--flag-panel", help="flag 双通道之一：控制面板提交值")
    ap.add_argument("--flag-shot", help="flag 双通道之二：截图/正文中的值")
    ap.add_argument("--target", default="", help="目标标识（主机/IP）")
    ap.add_argument("--title", default="", help="步骤标题（可选）")
    ap.add_argument("--profile", default="", help="执行分级（passive/active 等，写入证据头）")
    ap.add_argument("--manifest", help="证据清单 JSONL 路径（追加一行）")
    ap.add_argument("--retention", help="留存入径（默认取 --out 路径）")
    ap.add_argument("--append", action="store_true", help="追加到 --out 文件末尾（默认覆盖）")
    ap.add_argument("--strict", action="store_true",
                    help="三件套不全或 flag 双通道不一致时以退出码 1 失败（质量门强制）")
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

    if args.script and not os.path.isfile(args.script):
        print("ERROR: 脚本副本不存在：%s" % args.script, file=sys.stderr)
        return 1

    avoid = parse_avoid_terms(args.glossary)
    timestamp = now()
    markdown, report = build_fragment(
        step_id=args.step,
        command=args.cmd,
        output=output,
        screenshot=args.screenshot,
        shot_cmd=args.shot_cmd,
        shot_kind=args.shot_kind or "",
        ai_log=ai_log,
        flag=args.flag or "",
        flag_panel=args.flag_panel or "",
        flag_shot=args.flag_shot or "",
        target=args.target,
        title=args.title,
        timestamp=timestamp,
        out_path=args.out,
        avoid_terms=avoid,
        script=args.script or "",
        script_src=args.script_src or "",
        script_note=args.script_note or "",
        profile=args.profile or "",
        note=args.note or "",
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

    # —— 证据清单（JSONL，逐行追加；供 report-exam 与人工复核独立消费） ——
    if args.manifest:
        record = build_manifest_record(
            args.step, args.cmd, report, timestamp,
            profile=args.profile, retention=(args.retention or args.out),
            target=args.target, screenshot=args.screenshot or "",
            shot_kind=args.shot_kind or "", script=args.script or "")
        man_dir = os.path.dirname(os.path.abspath(args.manifest))
        if man_dir and not os.path.isdir(man_dir):
            os.makedirs(man_dir, exist_ok=True)
        with open(args.manifest, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    failed = False
    if not report["complete"]:
        # 诊断信息走 stderr，保证 `--out -` 时 stdout 仅含 markdown，可被下游直接消费
        print("提示：三件套不全（缺失：%s）。可用 --strict 强制失败。" % "、".join(report["missing"]),
              file=sys.stderr)
        failed = True
    if report["flag_status"] == "不一致":
        print("提示：flag 双通道不一致（面板=%r 截图=%r）。可用 --strict 强制失败。"
              % (args.flag_panel or args.flag, args.flag_shot), file=sys.stderr)
        failed = True
    if failed and args.strict:
        if not report["complete"]:
            print("ERROR: 严格模式，三件套不全（缺失：%s）。" % "、".join(report["missing"]),
                  file=sys.stderr)
        if report["flag_status"] == "不一致":
            print("ERROR: 严格模式，flag 双通道不一致。", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
