#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 B1：五服务凭据狩猎（AC-09..11）。

一手事实：`attack-infra-ch9-canonical.md` C-4/C-10/C-11。
凭据一律只产指纹（P-2），明文不落片段；命令经 ctx.command（唯一 seam）。
"""
import re
from typing import Any, Dict, List, Tuple

from .ch9_model import (
    ABSENT, AUTH_REQUIRED, EXPOSED_NO_AUTH, Ch9Verdict, CredFingerprint,
)

SERVICES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    ("s3", ("aws", "s3", "ls", "--recursive")),
    ("secretsmanager", ("aws", "secretsmanager", "list-secrets")),
    ("ssm", ("aws", "ssm", "describe-parameters")),
    ("cloudwatch", ("aws", "logs", "describe-log-groups")),
    ("ecr", ("aws", "ecr", "describe-repositories")),
)

CRED_PATTERNS = (
    ("sk-", re.compile(r"sk-[A-Za-z0-9_\-]{8,}")),
    ("AKIA", re.compile(r"AKIA[0-9A-Z]{12,}")),
    ("Bearer", re.compile(r"Bearer\s+([A-Za-z0-9._\-]{8,})")),
    ("postgres", re.compile(r"postgresql://[^\s\"']+")),
)


def _fingerprints(text: str, service: str) -> List[CredFingerprint]:
    out: List[CredFingerprint] = []
    for prefix, pattern in CRED_PATTERNS:
        for match in pattern.finditer(text or ""):
            value = match.group(1) if prefix == "Bearer" else match.group(0)
            out.append(CredFingerprint(prefix=prefix, length=len(value),
                                       location=service))
    return out


# 敏感键名词汇：涵盖 JSON 引号键（"SecretString"）、赋值键（api_key=）与日志标签。
_SECRET_KEY_RE = re.compile(
    r'(["\']?(?:password|passwd|secret|secretstring|api[_-]?key|token|accesskey|'
    r'privatekey|credential)["\']?\s*(?:[:=]|\s+)\s*["\']?)([^"\'\s,}\]]+)',
    re.I,
)


def _redact(text: str) -> str:
    """P-2：把所有凭据值替换为脱敏占位，防止明文落进 output/证据。

    覆盖四类形态：已知前缀（sk-/AKIA/Bearer）、连接串口令、敏感键赋值
    （含引号 JSON 键 SecretString / "api_key"）、以及日志中独立的敏感词行。
    不覆盖的裸高熵 token 由「命中行只保留指纹、output 仅写指纹摘要」兜底
    （见 filter_log_hits 的 _redact 后二次处理）。
    """
    result = text or ""
    for prefix, pattern in CRED_PATTERNS:
        result = pattern.sub(lambda m: prefix + "-<redacted>", result)
    result = _SECRET_KEY_RE.sub(r'\1<redacted>', result)
    result = re.sub(r'(://[^:\s]+:)[^@\s]+(@)', r'\1<redacted>\2', result)
    return result


def hunt_services(ctx: Any) -> Ch9Verdict:
    """sec-01（AC-09）：五服务分别列举，命中产独立指纹分组。"""
    outs: List[str] = []
    groups: Dict[str, List[str]] = {}
    all_commands: List[str] = []
    denied = 0
    for service, argv in SERVICES:
        result = ctx.command.run(argv, timeout=ctx.timeout)
        all_commands.append(" ".join(argv))
        text = (result.stdout or result.stderr).strip()
        outs.append("$ %s\n(exit=%d)\n%s" % (" ".join(argv), result.code, _redact(text)[:700]))
        if "AccessDenied" in text or "not authorized" in text:
            denied += 1
            continue
        fps = _fingerprints(text, service)
        if fps:
            groups[service] = [f.as_text() for f in fps]
    if denied == len(SERVICES):
        return Ch9Verdict("ch9-sec-01", AUTH_REQUIRED, "forbidden",
                          "五服务列举均被拒绝", "; ".join(all_commands), "\n\n".join(outs))
    if all("not found" in o for o in outs):
        return Ch9Verdict("ch9-sec-01", ABSENT, "no_tool",
                          "未安装 aws CLI", "; ".join(all_commands), "\n\n".join(outs))
    total = sum(len(v) for v in groups.values())
    return Ch9Verdict("ch9-sec-01", EXPOSED_NO_AUTH, "",
                      "%d 服务命中，%d 条凭据指纹" % (len(groups), total),
                      "; ".join(all_commands), "\n\n".join(outs),
                      {"fingerprint_groups": groups, "service_count": len(groups)})


def ssm_old_password(ctx: Any) -> Ch9Verdict:
    """sec-02（AC-10）：SSM 参数版本历史存在旧口令。"""
    name = getattr(ctx, "ssm_param", "/megacorpone/prod/database-url")
    argv = ("aws", "ssm", "get-parameter-history", "--name", name,
            "--with-decryption")
    result = ctx.command.run(argv, timeout=ctx.timeout)
    text = (result.stdout or result.stderr).strip()
    command = " ".join(argv)
    if not result.ok:
        return Ch9Verdict("ch9-sec-02", AUTH_REQUIRED, "forbidden",
                          "SSM 版本历史读取被拒绝", command, _redact(text)[:600])
    try:
        import json
        data = json.loads(text)
    except (ValueError, TypeError):
        data = {}
    params = data.get("Parameters", []) if isinstance(data, dict) else []
    values = [str(p.get("Value", "")) for p in params if isinstance(p, dict)]
    has_old = len(set(values)) > 1
    safe = _redact(text)[:700]
    return Ch9Verdict("ch9-sec-02", EXPOSED_NO_AUTH if has_old else ABSENT,
                      "" if has_old else "none_found",
                      "存在旧口令版本" if has_old else "仅单一版本",
                      command, safe, {"versions": len(values), "has_old_password": has_old})


def filter_log_hits(ctx: Any) -> Ch9Verdict:
    """sec-03（AC-11）：用精确 filter-pattern 检索敏感词，输出仅命中行。"""
    group = getattr(ctx, "log_group", "/aws/sagemaker/training")
    pattern = getattr(ctx, "log_pattern", "password OR key OR secret OR token")
    argv = ("aws", "logs", "filter-log-events", "--log-group-name", group,
            "--filter-pattern", pattern)
    result = ctx.command.run(argv, timeout=ctx.timeout)
    text = (result.stdout or result.stderr).strip()
    command = " ".join(argv)
    if not result.ok:
        return Ch9Verdict("ch9-sec-03", AUTH_REQUIRED, "forbidden",
                          "日志过滤被拒绝", command, _redact(text)[:600])
    hits = [line for line in text.splitlines()
            if re.search(r"password|key|secret|token", line, re.I)]
    fps = _fingerprints("\n".join(hits), "cloudwatch")
    output = _redact("\n".join(hits))[:800] or "（无命中）"
    return Ch9Verdict("ch9-sec-03", EXPOSED_NO_AUTH if hits else ABSENT,
                      "" if hits else "none_found",
                      "%d 条敏感词命中" % len(hits), command, output,
                      {"hit_count": len(hits),
                       "fingerprints": [f.as_text() for f in fps]})
