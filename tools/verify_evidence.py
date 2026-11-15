#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""verify-evidence 机读校验器（GOVERNANCE §8.2 八项检查单 + §2.2 单次约束）。

仓库级共享组件：`skills/verify-evidence` 的**执行体**，`report-exam` 的提交前置。
独立于任何报告组装实现，避免门禁判据被下游重实现放宽。

分层（设计见 `docs/operations/verify-evidence-design.md`）：
  S-1 输入归一：`load_payload`（JSON 载荷）/ `from_loot`（登记簿 + 片段目录）
  S-2 判据：`check_vrf01` … `check_vrf08`、`check_proof_single`，各返回四元组
  S-3 外部工具：`Toolchain`（技能校验器 / 废弃术语表 / 文件 stat / 时钟，可注入）
  S-4 输出：`verify` 结果字典（schema 版本化）+ `render_summary` + 退出码

判定分级（术语见 GLOSSARY「判定分级」）：
  blocking 违反「必须」条款 → 禁止提交；missing 未取分目标的预期缺失 → 不阻断；
  pending 环境受限未生成产物（核实闸）→ 不阻断但 `submission_ready` 为 False。

退出码：0 = 通过；1 = 阻断；2 = 用法错误。仅依赖 Python 标准库。
"""
import argparse
import contextlib
import datetime
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_GLOSSARY = os.path.join(ROOT, "GLOSSARY.md")
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024  # §6.4
SUBMIT_WINDOW_HOURS = 24  # §6.4.3 / S3 快照 L74
SCHEMA_VERSION = "1.0"

REQUIRED_ANCHORS = (
    "## Introduction", "## Objective", "## Requirements",
    "# Executive Summary", "## High-Level Attack Path",
    "# Attack Walkthrough", "# Appendix", "Offsec AI Red Teamer Report",
)
COPYRIGHT_LINE = "Copyright © 2026 OffSec Ltd. All rights reserved."

# 计分目标键集与分值口径的唯一事实源（C1），见 tools/scored_targets.py
from tools.scored_targets import (  # noqa: E402  (常量随模块加载)
    DOMAIN_CONTROLLER_KEY as DC_KEY,
    POINT_PATTERN,
    SCORED_HOSTS as SCORED_TARGETS,
    TOTAL_POINTS,
)

CHECKS = ("vrf-01", "vrf-02", "vrf-03", "vrf-04",
          "vrf-05", "vrf-06", "vrf-07", "vrf-08", "proof-single")
ACCESS_PROOF_TOKENS = ("whoami", "id")

_LOOT_REGISTRY = None


def _load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    # 先注册到 sys.modules：dataclass / 装饰器解析 `cls.__module__` 依赖此表
    sys.modules.setdefault(name, mod)
    spec.loader.exec_module(mod)
    return mod


def _loot_registry():
    """登记簿模块（判据单一事实源，C1）：三件套与双通道复用其实现。"""
    global _LOOT_REGISTRY
    if _LOOT_REGISTRY is None:
        _LOOT_REGISTRY = _load_module(
            "_verify_loot_registry",
            os.path.join(ROOT, "tools", "loot_manage", "registry.py"))
    return _LOOT_REGISTRY


def load_avoid_terms(glossary_path=DEFAULT_GLOSSARY):
    """复用 scripts/check_glossary.py 的解析逻辑，保证术语判据同源。"""
    mod = _load_module("_check_glossary",
                       os.path.join(ROOT, "scripts", "check_glossary.py"))
    _canonical, avoid = mod.parse_glossary(glossary_path)
    return list(avoid)


# ---------------------------------------------------------------- S-3 外部工具


class Toolchain:
    """可注入的外部能力（S-3）。缺省实现调用仓库真实脚本 / 文件系统 / 时钟。"""

    def validate_skills(self, skills_dir=None):
        """技能解剖终检（vrf-01）：返回错误列表，空列表即通过。"""
        mod = _load_module("_validate_skill",
                           os.path.join(ROOT, "scripts", "validate_skill.py"))
        buf = io.StringIO()
        argv = [] if skills_dir is None else ["--skills-dir", skills_dir]
        try:
            with contextlib.redirect_stdout(buf):
                code = mod.main(argv)
        except SystemExit as exc:  # argparse 用法错误
            return ["技能校验器退出异常：%s" % exc.code]
        return [] if code == 0 else [buf.getvalue().strip() or "技能校验器返回非零"]

    def avoid_terms(self, glossary_path=DEFAULT_GLOSSARY):
        """废弃术语表；读取失败返回 None（判据层据此判「无法判定」而非放行）。"""
        try:
            return load_avoid_terms(glossary_path)
        except (OSError, AttributeError):
            return None

    def stat(self, path):
        """返回 (exists, size_bytes)。"""
        if path and os.path.isfile(path):
            return True, os.path.getsize(path)
        return False, 0

    def archive_encrypted(self, path):
        """归档是否设密码（§6.4.2）：True / False / None（无 7z 工具，无法判定）。"""
        exe = shutil.which("7z") or shutil.which("7za")
        if not exe or not path or not os.path.isfile(path):
            return None
        try:
            proc = subprocess.run([exe, "l", "-slt", path], capture_output=True,
                                  text=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            return None
        if proc.returncode != 0:
            return None
        m = re.search(r"^Encrypted\s*=\s*(\S+)\s*$", proc.stdout, re.M)
        return None if not m else m.group(1).strip() != "-"


# ---------------------------------------------------------------- S-1 输入归一


def _parse_points(raw):
    """分值表归一：{目标: 分值}；非法值按 -1 记录（必然不满足多重集判据）。"""
    out = {}
    for key, val in (raw or {}).items():
        try:
            out[str(key)] = int(val)
        except (TypeError, ValueError):
            out[str(key)] = -1
    return out


def _parse_time(value, field=""):
    """接受 datetime / ISO 8601 字符串 / epoch 秒。

    缺失返回 None；**格式非法抛 ValueError**（判定层据此阻断，不静默放行）。
    """
    if value in (None, ""):
        return None
    if isinstance(value, datetime.datetime):
        return value if value.tzinfo else value.replace(tzinfo=datetime.timezone.utc)
    if isinstance(value, (int, float)):
        return datetime.datetime.fromtimestamp(float(value), datetime.timezone.utc)
    try:
        dt = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        raise ValueError("%s 时间戳格式非法：%r（须 ISO 8601 或 epoch 秒）" % (field, value))
    return dt if dt.tzinfo else dt.replace(tzinfo=datetime.timezone.utc)


def normalize_payload(raw):
    """把任意输入归一为判据层可消费的固定形状（缺省值集中在此）。"""
    return {
        "report_md": raw.get("report_md", "") or "",
        "appendix_md": raw.get("appendix_md", "") or "",
        "osid": raw.get("osid", "XXXXX") or "XXXXX",
        "fragments": list(raw.get("fragments", []) or []),
        "panel_flags": dict(raw.get("panel_flags", {}) or {}),
        "target_points": _parse_points(raw.get("target_points")),
        "pdf_path": raw.get("pdf_path"),
        "zip_path": raw.get("zip_path"),
        "glossary_path": raw.get("glossary_path", DEFAULT_GLOSSARY),
        "exam_end_at": _parse_time(raw.get("exam_end_at"), "exam_end_at"),
        "submit_at": _parse_time(raw.get("submit_at"), "submit_at"),
    }


def load_payload(path):
    """读 JSON 载荷并归一。文件缺失 / JSON 非法 → ValueError。"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError) as exc:
        raise ValueError("无法读取载荷：%s" % exc)
    if not isinstance(raw, dict):
        raise ValueError("载荷须为 JSON 对象")
    return normalize_payload(raw)


def _osid_from_name(path):
    m = re.search(r"OS-(\w+)", os.path.basename(path or ""))
    return m.group(1) if m else "XXXXX"


def from_loot(registry_path, evidence_dir=None, report_md="", appendix_md="",
              target_points=None):
    """由战利品登记簿（+ 可选片段目录 + 报告正文）构造输入（S-1 第二入口）。

    只消费登记簿既有判据（`parse_registry` / `parse_dual` / `fragment_pieces`），
    不另写三件套或双通道判定（C1）。报告正文与分值表由调用方给出（通常为
    `report-exam` 产物）——单凭登记簿无法判定 vrf-01/02/06，缺省为空则如实阻断。
    """
    reg_mod = _loot_registry()
    try:
        with open(registry_path, "r", encoding="utf-8") as f:
            registry = reg_mod.parse_registry(f.read())
    except OSError as exc:
        raise ValueError("无法读取登记簿：%s" % exc)
    root = evidence_dir or os.path.dirname(os.path.abspath(registry_path))
    fragments, panel_flags = [], {}
    for row in registry.rows:
        host = (getattr(row, "host", "") or "").strip()
        frag_path = (getattr(row, "evidence", "") or "").strip()
        panel, shot = reg_mod.parse_dual(getattr(row, "dual", "") or "")
        if panel:
            panel_flags[host] = panel
        raw = ""
        if frag_path:
            p = frag_path if os.path.isabs(frag_path) else os.path.join(root, frag_path)
            if os.path.isfile(p):
                with open(p, "r", encoding="utf-8") as f:
                    raw = f.read()
        pieces = reg_mod.fragment_pieces(raw) if raw else {}
        fragments.append({
            "step_id": (getattr(row, "id", "") or "").strip(),
            "host": host,
            "command": "",
            "output": "",
            "screenshot": shot or frag_path,
            "ai_log": "",
            "flag": panel,
            "raw": raw,
            "pieces": {k: bool(pieces.get(k))
                       for k in ("command", "output", "screenshot")},
        })
    return normalize_payload({"fragments": fragments, "panel_flags": panel_flags,
                              "osid": _osid_from_name(registry_path),
                              "report_md": report_md,
                              "appendix_md": appendix_md,
                              "target_points": target_points or {}})


# ---------------------------------------------------------------- S-2 判据


def _result():
    return {"ok": None, "blocking": [], "missing": [], "pending": []}


def _scored(fragments):
    return [f for f in fragments if (f.get("flag") or "").strip()]


def _screenshot_section(raw):
    """取片段中的「截图」节原文（访问证明判定的唯一文本来源）。"""
    m = re.search(r"####\s*截图[^\n]*\n(.*?)(?=\n####\s|\Z)", raw or "", re.S)
    return (m.group(1) if m else "").strip()


def check_vrf01(inp, tools):
    """五要素与元信息（§4.2）：以仓库技能校验器结论为准，并核对 OSID / 版权。"""
    r = _result()
    report = inp["report_md"]
    if not (re.search(r"# OSID:\s*\S+", report) and COPYRIGHT_LINE in report):
        r["ok"] = False
        r["blocking"].append("vrf-01：OSID 或逐字版权声明缺失（§4.2）")
        return r
    errors = tools.validate_skills() or []
    if errors:
        r["ok"] = False
        r["blocking"].append("vrf-01：技能解剖校验未通过 —— %s"
                             % str(errors[0]).splitlines()[0])
    else:
        r["ok"] = True
    return r


def check_vrf02(inp):
    """目标计分清单（§2.2 / §4.3 / ADR-0002）：8 目标键集 + 分值多重集 + 合计 100。"""
    r = _result()
    report = inp["report_md"]
    keys = [k for k in SCORED_TARGETS if k in report]
    points = inp.get("target_points") or {}
    if not points:
        # 无分值表时以「8 个主机键全部出现在报告中」为判据，不依赖章节标题（VG-1）
        absent = [k for k in SCORED_TARGETS if k not in report]
        if absent:
            r["ok"] = False
            r["blocking"].append("vrf-02：目标计分清单缺目标 %s（§2.2）" % "、".join(absent))
            return r
        r["ok"] = True
        r["missing"].append("NOTE-6：未提供目标分值表，分值合计待人工核对（§2.2.1）")
        return r
    absent = [k for k in SCORED_TARGETS if k not in points]
    if absent:
        r["ok"] = False
        r["blocking"].append("vrf-02：分值表缺目标 %s（§2.2）" % "、".join(absent))
        return r
    counts = {}
    for v in points.values():
        counts[v] = counts.get(v, 0) + 1
    total = sum(points.values())
    bad_keys = [k for k, v in points.items()
                if v not in POINT_PATTERN or (k == DC_KEY and v != 5)]
    if total != TOTAL_POINTS or counts != POINT_PATTERN or bad_keys:
        r["ok"] = False
        r["blocking"].append(
            "vrf-02：分值口径不符（合计 %d，期望 %d；15 分 %d 个、10 分 %d 个、5 分 %d 个；"
            "越界目标 %s）（§2.2.1 / ADR-0002）"
            % (total, TOTAL_POINTS, counts.get(15, 0), counts.get(10, 0),
               counts.get(5, 0),
               "、".join(bad_keys) or "无"))
        return r
    r["ok"] = True
    return r


def _pieces(frag):
    """三件套判定：优先用登记簿判据结果（S-1 已算），其次委托其实现，最后回退布尔字段。"""
    if "pieces" in frag:
        return {k: bool(v) for k, v in frag["pieces"].items()}
    raw = frag.get("raw") or ""
    if raw:
        got = _loot_registry().fragment_pieces(raw)
        return {k: bool(got.get(k)) for k in ("command", "output", "screenshot")}
    return {k: bool(frag.get(k)) for k in ("command", "output", "screenshot")}


def check_vrf03(inp):
    """已取分片段三件套（§6.1）；未取分缺失仅记 missing（SKILL 失败与豁免）。"""
    r = _result()
    fragments = inp["fragments"]
    scored_ids = {id(f) for f in _scored(fragments)}
    ok = True
    for f in fragments:
        gap = [k for k, v in _pieces(f).items() if not v]
        if not gap:
            continue
        if id(f) in scored_ids:
            ok = False
            r["blocking"].append("vrf-03：%s 已取分但三件套缺 %s（§6.1）"
                                 % (f.get("step_id", "?"), "、".join(gap)))
        else:
            r["missing"].append("vrf-03：%s 三件套缺 %s（未取分属预期，待补录）"
                                % (f.get("step_id", "?"), "、".join(gap)))
    r["ok"] = ok
    return r


def _access_proof(frag):
    """访问证明（§6.2.2）：同一画面含 whoami/id 与 flag 值。

    判定文本只取「访问证明」原文：显式 `access_proof` 字段优先，其次片段截图中
    的 `#### 截图` 节（`--shot-kind transcript` 的内联记录）；命令块不参与判定，
    避免「命令里写了 whoami」被误判为同屏证据。
    """
    flag = (frag.get("flag") or "").strip()
    text = frag.get("access_proof") or _screenshot_section(frag.get("raw") or "")
    if not text:
        return None, "未提供访问证明文本"
    body = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", text).strip()
    if not body:
        # 纯图片截图（无内联文字记录）：机器无法判定同屏性 → 人工判据
        return None, "截图为图片、无内联访问证明文本"
    if not any(re.search(r"\b%s\b" % t, body) for t in ACCESS_PROOF_TOKENS):
        return False, "截图中无 whoami/id"
    if flag and flag not in body:
        return False, "flag 未与访问证明同屏"
    return True, ""


def check_vrf04(inp):
    """flag 双通道一致（§6.2.1）+ 访问证明（§6.2.2）。"""
    r = _result()
    ok = True
    panel = inp["panel_flags"]
    fragments = inp["fragments"]
    for f in _scored(fragments):
        host = f.get("host", "")
        if host not in panel:
            ok = False
            r["blocking"].append("vrf-04：%s 缺控制面板提交值（§6.2 / §2.4）"
                                 % f.get("step_id", "?"))
        elif panel[host] != f.get("flag"):
            ok = False
            r["blocking"].append("vrf-04：%s 面板值 != 报告值（§6.2 / §2.4）"
                                 % f.get("step_id", "?"))
        proof, reason = _access_proof(f)
        if proof is False:
            ok = False
            r["blocking"].append("vrf-04：%s 访问证明不足 —— %s（§6.2.2）"
                                 % (f.get("step_id", "?"), reason))
        elif proof is None:
            r["missing"].append("NOTE-7：%s 访问证明无法机判（%s），同屏性待人工核对（§6.2.2）"
                                % (f.get("step_id", "?"), reason))
    for h in {f.get("host", "") for f in fragments}:
        if not any(f.get("flag") for f in fragments if f.get("host") == h):
            r["missing"].append("vrf-04：%s 无 flag 双通道证据（未达成，待补录）" % h)
    r["ok"] = ok
    return r


def check_vrf05(inp):
    """AI 交互入附录（§6.3）。"""
    r = _result()
    appendix = inp["appendix_md"]
    with_ai = [f for f in inp["fragments"] if (f.get("ai_log") or "").strip()]
    bad = [f for f in with_ai if f["ai_log"].strip() not in appendix]
    r["ok"] = not bad
    if bad:
        r["blocking"].append("vrf-05：AI 交互日志未全量入 Appendix D（§6.3）")
    if not with_ai and inp["fragments"]:
        r["missing"].append("vrf-05：本次输入无 AI 交互日志（须回溯对应技能按 §6.3 补录）")
    return r


def check_vrf06(inp):
    """报告结构完整可复现（§7.1 / §6.1）。"""
    r = _result()
    gap = [a for a in REQUIRED_ANCHORS if a not in inp["report_md"]]
    r["ok"] = not gap
    for a in gap:
        r["blocking"].append("vrf-06：报告缺锚点 %s（§7.1）" % a)
    return r


def check_naming_and_size(pdf_path, zip_path, osid, tools=None):
    """§6.4：命名、产物存在、≤100MB（无密码由打包侧 `7z a` 不传 `-p` 保证）。"""
    tools = tools or Toolchain()
    problems = []
    exp_pdf = "OSAI-OS-%s-Exam-Report.pdf" % osid
    exp_zip = "OSAI-OS-%s-Exam-Report.7z" % osid
    if os.path.basename(pdf_path or "") != exp_pdf:
        problems.append("PDF 命名不符：期望 %s" % exp_pdf)
    if os.path.basename(zip_path or "") != exp_zip:
        problems.append("归档命名不符：期望 %s" % exp_zip)
    pdf_ok, _ = tools.stat(pdf_path)
    zip_ok, zip_size = tools.stat(zip_path)
    if not pdf_ok:
        problems.append("PDF 产物缺失（§6.4）")
    if not zip_ok:
        problems.append(".7z 归档产物缺失（§6.4）")
    elif zip_size > MAX_ARCHIVE_BYTES:
        problems.append("归档超过 100MB（§6.4）")
    return (len(problems) == 0), problems


def _check_window(exam_end, submit):
    """24h 提交窗口（§6.4.3 / S3 快照 L74）。返回 (ok|None, 说明)。"""
    if exam_end is None or submit is None:
        return None, "NOTE-5：未提供考试结束/提交时间，24h 窗口待人工确认（§6.4）"
    delta = submit - exam_end
    if delta.total_seconds() < 0:
        return False, "提交时间早于考试结束时间，时间戳异常（§6.4.3）"
    if delta > datetime.timedelta(hours=SUBMIT_WINDOW_HOURS):
        return False, ("超出 24h 提交窗口（已过 %.1f 小时）"
                       % (delta.total_seconds() / 3600))
    return True, ""


def check_vrf07(inp, require_artifacts, tools):
    """提交格式与窗口（§6.4）：dry-run 记 None，绝不放宽为 True。"""
    r = _result()
    if not require_artifacts:
        r["ok"] = None
        r["pending"].append("VG-3：pandoc/7z 产物未生成，本次为 dry-run，不可提交")
        return r
    ok, miss = check_naming_and_size(inp["pdf_path"], inp["zip_path"],
                                     inp["osid"], tools)
    for m in miss:
        r["blocking"].append("vrf-07：%s" % m)
    win, why = _check_window(inp["exam_end_at"], inp["submit_at"])
    if win is False:
        ok = False
        r["blocking"].append("vrf-07：%s（§6.4.3）" % why)
    elif win is None:
        r["missing"].append(why)
    encrypted = tools.archive_encrypted(inp["zip_path"])
    if encrypted is True:
        ok = False
        r["blocking"].append("vrf-07：归档设置了密码（§6.4.2 禁止）")
    elif encrypted is None:
        r["missing"].append("NOTE-8：无 7z 工具或归档不可读，密码态待人工确认（§6.4.2）")
    r["ok"] = ok
    return r


def check_vrf08(inp, tools):
    """术语合规（§1.3）：动态取自 GLOSSARY.md；证据区间逐字原文豁免。"""
    r = _result()
    avoid = tools.avoid_terms(inp.get("glossary_path"))
    if avoid is None:
        r["ok"] = False
        r["blocking"].append("vrf-08：术语表不可读，废弃术语无法判定（§1.3）")
        return r
    scan = re.sub(r"<!-- EVIDENCE-FRAGMENT-START -->.*?<!-- EVIDENCE-FRAGMENT-END -->",
                  "", inp["report_md"], flags=re.S)
    hits = [t for t in avoid if t in scan]
    r["ok"] = not hits
    if hits:
        r["blocking"].append("vrf-08：报告叙述正文使用废弃术语 %s（§1.3）" % "、".join(hits))
    return r


def check_proof_single(inp):
    """域控 proof.txt 单次提交（§2.2.3）：按目标键判定，不做 flag 值子串匹配。"""
    r = _result()
    records = [f for f in _scored(inp["fragments"]) if f.get("host") == DC_KEY]
    r["ok"] = len(records) <= 1
    if len(records) > 1:
        r["blocking"].append("proof-single：proof.txt 提交记录 %d 次，违反 §2.2 单次约束"
                             % len(records))
    if not records:
        r["missing"].append("VG-4：域控 proof.txt 尚未取分，单次提交约束待真实取分后闭环（预期）")
    return r


# ---------------------------------------------------------------- S-4 输出


def verify(payload, require_artifacts=True, tools=None):
    """执行八项检查单 + 单次约束，返回 schema 版本化的机读结果。

    兼容既有调用：`payload` 可为原始字典（此处自动归一）。输入非法（时间戳格式
    等）不抛异常：归一化失败按「阻断 + 用法提示」返回，避免调用方拿到半真结果。
    """
    tools = tools or Toolchain()
    try:
        inp = normalize_payload(payload or {})
    except ValueError as exc:
        return {"schema_version": SCHEMA_VERSION,
                "checks": {k: False for k in CHECKS},
                "passed": False,
                "blocking": ["输入非法：%s" % exc],
                "missing": [], "pending": [],
                "failed_checks": list(CHECKS), "submission_ready": False}
    runners = {
        "vrf-01": lambda: check_vrf01(inp, tools),
        "vrf-02": lambda: check_vrf02(inp),
        "vrf-03": lambda: check_vrf03(inp),
        "vrf-04": lambda: check_vrf04(inp),
        "vrf-05": lambda: check_vrf05(inp),
        "vrf-06": lambda: check_vrf06(inp),
        "vrf-07": lambda: check_vrf07(inp, require_artifacts, tools),
        "vrf-08": lambda: check_vrf08(inp, tools),
        "proof-single": lambda: check_proof_single(inp),
    }
    checks, blocking, missing, pending = {}, [], [], []
    for name in CHECKS:
        res = runners[name]()
        checks[name] = res["ok"]
        blocking.extend(res["blocking"])
        missing.extend(res["missing"])
        pending.extend(res["pending"])

    failed = [k for k, v in checks.items() if v is False]
    passed = not failed and not blocking
    submission_ready = passed and not pending and checks.get("vrf-07") is True
    return {"schema_version": SCHEMA_VERSION, "checks": checks, "passed": passed,
            "blocking": blocking, "missing": missing, "pending": pending,
            "failed_checks": failed, "submission_ready": submission_ready}


def render_summary(result):
    """人读摘要：结论 + 三类分级计数 + 逐条明细。"""
    if not result:
        return ""
    head = "结论：%s（阻断 %d / 缺失 %d / 核实闸 %d；可提交：%s）" % (
        "通过" if result.get("passed") else "阻断",
        len(result.get("blocking") or []), len(result.get("missing") or []),
        len(result.get("pending") or []),
        "是" if result.get("submission_ready") else "否")
    lines = [head]
    for tag in ("blocking", "missing", "pending"):
        for item in result.get(tag) or []:
            lines.append("  - [%s] %s" % (tag, item))
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="verify-evidence 八项检查单机读校验")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--payload", help="JSON 载荷文件路径")
    src.add_argument("--from-loot", help="战利品登记簿路径（registry.md）")
    ap.add_argument("--evidence-dir", help="登记簿片段路径的解析根目录")
    ap.add_argument("--report", help="报告 markdown（--from-loot 时用于 vrf-01/02/06）")
    ap.add_argument("--appendix", help="附录 markdown（--from-loot 时用于 vrf-05）")
    ap.add_argument("--no-artifacts", action="store_true",
                    help="dry-run：不要求 PDF/.7z 产物（结果不可提交）")
    ap.add_argument("--summary", action="store_true", help="额外输出人读摘要")
    args = ap.parse_args(argv)

    def _read(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    try:
        if args.payload:
            payload = load_payload(args.payload)
        else:
            payload = from_loot(
                args.from_loot, args.evidence_dir,
                report_md=_read(args.report) if args.report else "",
                appendix_md=_read(args.appendix) if args.appendix else "")
    except (OSError, ValueError) as exc:
        print("ERROR: %s" % exc, file=sys.stderr)
        return 2
    result = verify(payload, require_artifacts=not args.no_artifacts)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.summary:
        print(render_summary(result))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
