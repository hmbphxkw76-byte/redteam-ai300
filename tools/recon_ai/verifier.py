#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""运行自校验（S5）：C1–C9 布尔门禁，判定报告结论只能由实跑证据推导。

只读 `run.json` / 证据片段 / MANIFEST / 资产清单 / 验证报告；
不重发请求、不改写证据。任何检查不可判定即视为失败（不静默通过）。
"""
import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List

from .evidence import load_manifest
from .model import ASSET_FIELDS

STEP_IDS = tuple("recon-0%d" % i for i in range(1, 8))
FRAGMENT_SECTIONS = ("确切命令", "关键输出", "截图（访问证明）")
REPORT_SECTIONS = ("## 1. 覆盖矩阵", "## 2. 证据核对表", "## 3. 缺口台账",
                   "## 4. 自校验门禁", "## 5. 复现命令", "## 6. 结论")
VERDICT_RE = re.compile(r"\*\*判定\*\*：\s*(PASS|BLOCKED)")


@dataclass
class Check:
    name: str
    ok: bool
    detail: str = ""

    def to_dict(self):
        return {"name": self.name, "ok": bool(self.ok), "detail": self.detail}


@dataclass
class VerificationResult:
    run_id: str
    target: str
    checks: List[Check] = field(default_factory=list)
    generated_at: str = ""

    @property
    def verdict(self):
        return "PASS" if self.checks and all(c.ok for c in self.checks) else "BLOCKED"

    def failed(self):
        return [c for c in self.checks if not c.ok]

    def to_dict(self):
        return {"run_id": self.run_id, "target": self.target,
                "verdict": self.verdict, "checks": [c.to_dict() for c in self.checks],
                "failed": [c.name for c in self.failed()],
                "generated_at": self.generated_at}


def _sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _parse_ts(value):
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def _inside(path, root):
    try:
        return os.path.commonpath([os.path.realpath(path), os.path.realpath(root)]) == \
            os.path.realpath(root)
    except (OSError, ValueError):
        return False


def _read(path):
    if not path or not os.path.isfile(path):
        return ""
    with open(path, encoding="utf-8") as f:
        return f.read()


def _step_ids(steps):
    return [s.get("step_id") for s in steps]


def _check_c1(meta):
    steps = meta.get("steps") or []
    ids = _step_ids(steps)
    done = [s.get("step_id") for s in steps if s.get("status") == "done"]
    ok = len(steps) == 7 and set(ids) == set(STEP_IDS) and len(done) == 7
    return Check("C1 步骤全覆盖", ok,
                 "已完成=%d/7；未完成=%s" % (
                     len(done), ",".join(sorted(set(STEP_IDS) - set(done))) or "无"))


def _check_c2(meta, run_dir):
    start = _parse_ts(meta.get("started"))
    finish = _parse_ts(meta.get("finished"))
    problems = []
    for step in meta.get("steps") or []:
        if step.get("status") != "done":
            continue
        path = step.get("evidence") or ""
        if not path or not os.path.isfile(path):
            problems.append("%s 证据缺失" % step.get("step_id"))
            continue
        if not _inside(path, run_dir):
            problems.append("%s 证据越出运行目录" % step.get("step_id"))
        if os.path.getsize(path) == 0:
            problems.append("%s 证据为空" % step.get("step_id"))
        if start and finish:
            mtime = datetime.fromtimestamp(os.path.getmtime(path), tz=start.tzinfo)
            if mtime + timedelta(seconds=5) < start or mtime > finish + timedelta(seconds=120):
                problems.append("%s 证据不在本次运行窗口" % step.get("step_id"))
    return Check("C2 证据新鲜度", not problems,
                 "；".join(problems) or "全部证据位于本次运行窗口内")


def _check_c3(meta):
    problems = []
    for step in meta.get("steps") or []:
        if step.get("status") != "done":
            continue
        text = _read(step.get("evidence") or "")
        for label in FRAGMENT_SECTIONS:
            if label not in text:
                problems.append("%s 缺「%s」" % (step.get("step_id"), label))
    return Check("C3 三件套结构", not problems,
                 "；".join(problems) or "每个片段含命令/输出/截图三节")


def _check_c4(meta):
    problems = []
    for step in meta.get("steps") or []:
        if step.get("status") != "done":
            continue
        sid = step.get("step_id")
        shot = (meta.get("shots") or {}).get(sid, "")
        if shot and os.path.isfile(shot):
            continue
        text = _read(step.get("evidence") or "")
        if "截图待补录" in text or "--headless" in text:
            problems.append("%s 截图待补录（三件套未齐）" % sid)
        else:
            problems.append("%s 截图缺失且无待补录依据" % sid)
    return Check("C4 截图状态", not problems,
                 "；".join(problems) or "7 份片段截图齐全")


def _in_window(record, start, finish):
    ts = _parse_ts(record.get("timestamp"))
    if ts is None or start is None or finish is None:
        return True
    return start - timedelta(seconds=5) <= ts <= finish + timedelta(seconds=120)


def _check_c5(meta):
    records = load_manifest(meta.get("manifest") or "")
    start, finish = _parse_ts(meta.get("started")), _parse_ts(meta.get("finished"))
    scoped = [r for r in records if _in_window(r, start, finish)]
    by_step = {}
    for record in scoped:
        by_step.setdefault(record.get("step_id"), []).append(record)
    problems = []
    for step in meta.get("steps") or []:
        if step.get("status") != "done":
            continue
        sid = step.get("step_id")
        items = by_step.get(sid, [])
        if len(items) != 1:
            problems.append("%s 清单记录 %d 条（应 1 条）" % (sid, len(items)))
            continue
        if items[0].get("target") not in (meta.get("target"), ""):
            problems.append("%s 清单 target 不一致" % sid)
        if len(items[0].get("sha256") or "") != 64:
            problems.append("%s 清单输出哈希长度非 64" % sid)
    return Check("C5 清单一致性", not problems,
                 "；".join(problems) or "每个已执行步骤恰有 1 条本次运行记录")


def _check_c6(meta):
    problems = []
    for step in meta.get("steps") or []:
        sid = step.get("step_id")
        if not (step.get("basis") or "").strip():
            problems.append("%s 缺判定依据" % sid)
        if step.get("existence") == "不可判定" and not step.get("tried"):
            problems.append("%s 判不可判定但未记录已试端点" % sid)
    return Check("C6 判定可复核", not problems,
                 "；".join(problems) or "每个判定均有依据，不可判定均有已试端点")


def _check_c7(meta):
    problems = list(meta.get("contract_violations") or [])
    path = meta.get("inventory_json") or ""
    if not path or not os.path.isfile(path):
        problems.append("资产清单 JSON 缺失")
    else:
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, ValueError) as exc:
            problems.append("资产清单不可解析：%s" % exc)
            data = {}
        seen = set()
        for asset in data.get("assets", []):
            miss = [name for name in ASSET_FIELDS
                    if not str(asset.get(name) or "").strip()]
            if miss:
                problems.append("%s 缺字段：%s" % (asset.get("asset_id") or "无ID",
                                                  "、".join(miss)))
            if asset.get("asset_id") in seen:
                problems.append("资产ID 重复：%s" % asset.get("asset_id"))
            seen.add(asset.get("asset_id"))
        if not data.get("assets") and not (data.get("undetermined") or data.get("gaps")):
            problems.append("资产清单既无资产也无未决面/缺口台账")
    return Check("C7 清单契约", not problems, "；".join(problems) or "七字段契约通过")


def _check_c8(meta):
    text = _read(meta.get("report_md") or "")
    missing = [section for section in REPORT_SECTIONS if section not in text]
    return Check("C8 报告结构", bool(text) and not missing,
                 "缺章节：%s" % "、".join(missing) if missing else
                 ("报告存在且六节齐全" if text else "验证报告缺失"))


def _check_c12(meta):
    records = load_manifest(meta.get("manifest") or "")
    start, finish = _parse_ts(meta.get("started")), _parse_ts(meta.get("finished"))
    problems = []
    for record in (r for r in records if _in_window(r, start, finish)):
        shot = record.get("screenshot") or ""
        expected = record.get("screenshot_sha256") or ""
        if shot and os.path.isfile(shot):
            if not expected or _sha256_file(shot) != expected:
                problems.append("%s 截图哈希不一致" % record.get("step_id"))
        elif expected:
            problems.append("%s 清单引用的截图已不存在" % record.get("step_id"))
    return Check("C12 证据完整性", not problems,
                 "；".join(problems) or "清单哈希与截图一致")


def verify_run(run_dir):
    """计算 C1–C8、C12；C9 由 `finalize` 在报告定稿后追加。"""
    meta_path = os.path.join(run_dir, "run.json")
    try:
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)
    except (OSError, ValueError) as exc:
        result = VerificationResult(run_id="", target="",
                                    generated_at=datetime.now().astimezone().isoformat(
                                        timespec="seconds"))
        result.checks.append(Check("C1 步骤全覆盖", False,
                                   "无法读取 run.json：%s" % exc))
        return result
    result = VerificationResult(
        run_id=meta.get("run_id", ""), target=meta.get("target", ""),
        generated_at=datetime.now().astimezone().isoformat(timespec="seconds"))
    result.checks.extend([
        _check_c1(meta), _check_c2(meta, run_dir), _check_c3(meta),
        _check_c4(meta), _check_c5(meta), _check_c6(meta), _check_c7(meta),
        _check_c8(meta), _check_c12(meta),
    ])
    return result


def finalize(result, report_path):
    """报告定稿后校验结论一致性（C9），并由调用方落盘 verification.json。"""
    match = VERDICT_RE.search(_read(report_path))
    reported = match.group(1) if match else "缺失"
    expected = result.verdict
    result.checks.append(Check(
        "C9 结论一致性", reported == expected,
        "报告结论=%s；门禁推导=%s" % (reported, expected)))
    return result


def write_verification(run_dir, result):
    path = os.path.join(run_dir, "verification.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
    return path
