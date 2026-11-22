#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 C1 三类只读观察（加固版）。

Listing 29-30：EC2 公网实例 + SG `0.0.0.0/0` ingress；
Listing 31：未鉴权模型端点（无鉴权头 200 + 模型元数据）；
Listing 32：版本号 → CVE 查询建议。

事实源 `docs/research/recon-ai-c1-hardening-canonical.md` C1-1..C1-7。
判定层零网络零命令执行；命令仅为数据字符串（P-2）。
"""
import json
import re
from typing import Any, Dict, List

from .ch9_c1_model import (
    ABSENT, AUTH_REQUIRED, CVE_ANCHOR, EXPOSED_NO_AUTH, C1Verdict,
)

VERSION_RE = re.compile(r"^\d+(\.\d+){1,3}([-+][\w.]+)?$")
META_KEYS = ("model", "version", "engine", "provider")


def _ports(rules) -> List[int]:
    """只判 0.0.0.0/0 ingress；端口有序去重（C1-1）。"""
    found: List[int] = []
    for rule in rules or []:
        if any(str(c) == "0.0.0.0/0" for c in (rule.get("cidrs") or [])):
            port = rule.get("port")
            if isinstance(port, int) and 0 < port <= 65535:
                found.append(port)
    return sorted(set(found))


def analyze_instance(instance: Dict[str, Any],
                     security_group: Dict[str, Any] | None = None) -> C1Verdict:
    """L29-30：公网 IP + 0.0.0.0/0 ingress → EXPOSED_NO_AUTH。"""
    public_ip = str(instance.get("public_ip", "") or "")
    ports = _ports((security_group or {}).get("ingress"))
    command = ("aws ec2 describe-instances --query 'Reservations[].Instances[]' ; "
               "aws ec2 describe-security-groups")
    if public_ip and ports:
        return C1Verdict(
            outcome=EXPOSED_NO_AUTH, public_ip=public_ip,
            exposed_ports=tuple(ports),
            summary="公网实例暴露 %d 个 0.0.0.0/0 端口" % len(ports),
            command=command,
            output="public_ip=%s exposed_ports=%s" % (public_ip, ports),
            shot_cmd="screenshot --region cloud_surface",
            credential_hint="(prefix-only)")
    reason = "no_public_ip" if not public_ip else "private_only"
    return C1Verdict(
        outcome=ABSENT, reason=reason, public_ip=public_ip,
        summary="无公网 IP 或无开放 ingress",
        command=command, output="无公网 IP 或无 0.0.0.0/0 ingress",
        shot_cmd="screenshot --region cloud_surface")


def probe_unauth_endpoint(response: Dict[str, Any], endpoint: str = "") -> C1Verdict:
    """L31：无鉴权头返回 200 + 模型元数据 → EXPOSED_NO_AUTH（只读）。"""
    status = response.get("status") if isinstance(response, dict) else None
    body = response.get("body", "") if isinstance(response, dict) else ""
    command = "curl -sS -D - %s/model-metadata   # 无鉴权头，只读" % (endpoint or "<MODEL_SVC>")
    if status in (401, 403):
        return C1Verdict(outcome=AUTH_REQUIRED, reason="auth_required",
                         summary="端点要求鉴权", command=command,
                         output="status=%s" % status,
                         shot_cmd="screenshot --region unauth_endpoint")
    if status != 200:
        return C1Verdict(outcome=ABSENT, reason="no_response",
                         summary="端点无有效响应", command=command,
                         output="status=%s" % status,
                         shot_cmd="screenshot --region unauth_endpoint")
    text = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
    if not any(k in text.lower() for k in META_KEYS):
        return C1Verdict(outcome=ABSENT, reason="none_found",
                         summary="200 但无模型元数据", command=command,
                         output="status=200（无模型元数据）",
                         shot_cmd="screenshot --region unauth_endpoint")
    return C1Verdict(outcome=EXPOSED_NO_AUTH,
                     summary="未鉴权端点暴露模型元数据", command=command,
                     output="status=200；model-metadata 命中（明文已省略）",
                     shot_cmd="screenshot --region unauth_endpoint",
                     credential_hint="(prefix-only)")


def correlate_version(version_payload: str, endpoint: str = "") -> C1Verdict:
    """L32：版本字符串 → 记录版本 + NVD 查询建议（不生成载荷）。"""
    version = (version_payload or "").strip().strip('"')
    try:
        data = json.loads(version_payload)
        if isinstance(data, dict):
            version = str(data.get("version") or data.get("Version") or version)
    except (ValueError, TypeError):
        pass
    command = "curl -s %s/version" % (endpoint or "<MODEL_SVC>")
    if not VERSION_RE.match(version):
        return C1Verdict(outcome=ABSENT, reason="invalid_version",
                         summary="无有效版本字符串", command=command,
                         output="无有效版本字符串",
                         shot_cmd="screenshot --region version")
    advice = ("按产品+版本查 NIST NVD / 官方安全公告；"
              "已核实锚点 %s（NVIDIA Container Toolkit ≤1.17.7，CNA CVSS 3.1=9.0）"
              % CVE_ANCHOR)
    return C1Verdict(outcome=EXPOSED_NO_AUTH, version=version, cve_advice=advice,
                     summary="记录版本 %s（仅查询建议）" % version,
                     command=command, output="version=%s；%s" % (version, advice),
                     shot_cmd="screenshot --region version")
