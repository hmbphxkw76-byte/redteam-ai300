#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 C1：云暴露面与版本关联（只读判定，AC-01..07）。

事实源 `docs/research/recon-ai-ch9-canonical.md` R-1..R-4。
本模块只判定调用方传入的观测数据，不发起网络/命令调用（recon-ai 只读边界）。
"""
import re
from typing import Any, Dict, List

EXPOSED_NO_AUTH, ABSENT = "EXPOSED_NO_AUTH", "ABSENT"
VERSION_RE = re.compile(r"^\d+(\.\d+){1,3}([-+][\w.]+)?$")


def analyze_instance(instance: Dict[str, Any], security_group: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """AC-01/02：公网 IP + 0.0.0.0/0 ingress → 暴露面命中。"""
    public_ip = str(instance.get("public_ip", "") or "")
    sg = security_group or {}
    exposed_ports: List[int] = []
    for rule in sg.get("ingress") or []:
        cidrs = rule.get("cidrs") or []
        if any(str(c) == "0.0.0.0/0" for c in cidrs):
            port = rule.get("port")
            if isinstance(port, int):
                exposed_ports.append(port)
    command = "aws ec2 describe-instances --query 'Reservations[].Instances[]' ; aws ec2 describe-security-groups"
    if public_ip and exposed_ports:
        return {"outcome": EXPOSED_NO_AUTH, "public_ip": public_ip,
                "exposed_ports": sorted(exposed_ports), "command": command,
                "output": "public_ip=%s exposed_ports=%s" % (public_ip, sorted(exposed_ports)),
                "shot_cmd": "screenshot --region cloud_surface"}
    return {"outcome": ABSENT, "reason": "none_found", "public_ip": public_ip,
            "exposed_ports": [], "command": command,
            "output": "无公网 IP 或无 0.0.0.0/0 ingress",
            "shot_cmd": "screenshot --region cloud_surface"}


def correlate_version(version_payload: str, endpoint: str = "") -> Dict[str, Any]:
    """AC-03/04：记录版本 + CVE 查询建议（不生成载荷）。"""
    version = (version_payload or "").strip().strip('"')
    try:
        import json
        data = json.loads(version_payload)
        if isinstance(data, dict):
            version = str(data.get("version") or data.get("Version") or version)
    except (ValueError, TypeError):
        pass
    command = "curl -s %s/version" % (endpoint or "<MODEL_SVC>")
    if not VERSION_RE.match(version):
        return {"outcome": ABSENT, "reason": "none_found", "version": "",
                "command": command, "output": "无有效版本字符串",
                "shot_cmd": "screenshot --region version"}
    advice = "按产品+版本查 NIST NVD / 官方安全公告，确认适用 CVE 后再评估"
    return {"outcome": EXPOSED_NO_AUTH, "version": version, "cve_advice": advice,
            "command": command, "output": "version=%s；%s" % (version, advice),
            "shot_cmd": "screenshot --region version"}
