#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 A3 SSRF→env harvest / C2 GPU 立足点（类型化五值结论）。

事实源 `docs/research/foothold-traditional-ch9-hardening-canonical.md`
H-1..H-6、P-1..P-4；上游轻量版 `foothold-traditional-ch9-canonical.md` 保留。
不执行 SSRF 载荷与 CVE-2025-23266 提权本体（P-4）。
"""
import re
from typing import Any, List, Tuple

from .ch9_model import (
    ABSENT, AUTH_REQUIRED, EXPOSED_NO_AUTH, EXPLOITED,
    Fingerprint, TriadVerdict,
)

AWS_KEYS = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN")
# 值域覆盖无引号裸值、单/双引号包裹值（P-1：不能因引号而绕过脱敏）。
_CRED_RE = re.compile(
    r'(AWS_(?:ACCESS_KEY_ID|SECRET_ACCESS_KEY|SESSION_TOKEN))\s*=\s*'
    r'(?:"([^"\x00]*)"|\'([^\'\x00]*)\'|([^\s\x00"\',]+))')
_NOPASSWD_RE = re.compile(r"\(root\)\s*NOPASSWD:\s*([^\n,]+)")


def _cred_value(match) -> str:
    """取三选一值组中的非空者（裸值/双引号/单引号）。"""
    return next((g for g in match.groups()[1:] if g is not None), "")


def _fingerprints(text: str) -> Tuple[Fingerprint, ...]:
    """P-1：只产 (键名, 长度, 位置) 指纹。"""
    out: List[Fingerprint] = []
    for m in _CRED_RE.finditer(text or ""):
        out.append(Fingerprint(key=m.group(1), length=len(_cred_value(m)),
                               location="ssrf-env"))
    return tuple(out)


def _redact(text: str) -> str:
    """P-1：任何 AWS_* 值（含引号包裹）替换为占位后才进 output。"""
    return _CRED_RE.sub(lambda m: "%s=<redacted>" % m.group(1), text or "")


def ssrf_credential_entry(ctx: Any) -> TriadVerdict:
    """trad-09（AC-01..04）：SSRF 响应识别 Lambda env 凭据，仅产指纹。"""
    response = getattr(ctx, "ssrf_response", "") or ""
    fps = _fingerprints(response)
    command = 'curl -s "<PORTAL>/api/export?template_url=file:///proc/self/environ"'
    out = _redact(response)[:800] or "（空响应）"
    shot = "screenshot --step trad-09 --kind transcript"
    if not fps:
        denied = "AccessDenied" in response or "Forbidden" in response
        return TriadVerdict(
            step_id="trad-09",
            outcome=AUTH_REQUIRED if denied else ABSENT,
            reason="forbidden" if denied else "none_found",
            summary="SSRF 响应无 AWS 凭据键名" if not denied else "SSRF 读取被拒绝",
            command=command, output=out, shot_cmd=shot)
    if bool(getattr(ctx, "verify_credential", False)):
        result = ctx.command.run(("aws", "sts", "get-caller-identity"),
                                 timeout=ctx.timeout)
        out += "\n$ aws sts get-caller-identity\n(status=%d)\n%s" % (
            result.code, (result.stdout or result.stderr)[:400])
        if result.ok and "Arn" in (result.stdout or ""):
            return TriadVerdict(
                step_id="trad-09", outcome=EXPLOITED, reason="",
                summary="%d 条凭据指纹，身份已验证" % len(fps),
                command=command + " ; aws sts get-caller-identity",
                output=out, shot_cmd=shot, fingerprints=fps)
    return TriadVerdict(
        step_id="trad-09", outcome=EXPOSED_NO_AUTH, reason="",
        summary="%d 条 AWS 凭据指纹（%s）" % (
            len(fps), "已验证但无 Arn" if getattr(ctx, "verify_credential", False) else "未验证"),
        command=command, output=out, shot_cmd=shot, fingerprints=fps)


def gpu_foothold_entry(ctx: Any) -> TriadVerdict:
    """trad-10（AC-05/06）：sudo -l 识别 NOPASSWD 包装脚本（立足点，非提权）。"""
    sudo_text = getattr(ctx, "sudo_l_output", "") or ""
    command = "sudo -l"
    found = _NOPASSWD_RE.findall(sudo_text)
    shot = "screenshot --step trad-10 --kind transcript"
    if not found:
        no_tool = "not found: sudo" in sudo_text
        return TriadVerdict(
            step_id="trad-10",
            outcome=ABSENT,
            reason="no_tool" if no_tool else "none_found",
            summary="sudo 不可用" if no_tool else "无 NOPASSWD 包装脚本",
            command=command, output=sudo_text[:600] or "（空）", shot_cmd=shot)
    return TriadVerdict(
        step_id="trad-10", outcome=EXPOSED_NO_AUTH, reason="",
        summary="%d 个 NOPASSWD 包装脚本（立足点；提权见 attack-infra ch9-gpu）" % len(found),
        command=command, output=sudo_text[:800], shot_cmd=shot,
        wrappers=tuple(s.strip() for s in found))
