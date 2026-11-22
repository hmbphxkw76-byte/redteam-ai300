#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 C2：GPU 逃逸条件判定（AC-17）。

一手事实：`attack-infra-ch9-canonical.md` C-9（NVD CVE-2025-23266，
NVIDIA Container Toolkit ≤1.17.7，CWE-426，CVSS 9.0）。
只做条件判定与降级，不编译/执行载荷（R-3：NVD 不提供可复现载荷细节）。
"""
import re
from typing import Any, Tuple

from .ch9_model import (
    ABSENT, BLOCKED, EXPLOITED, Ch9Verdict,
)

AFFECTED_CEILING = (1, 17, 7)  # NVD: all versions up to and including 1.17.7


def _parse_version(text: str) -> Tuple[int, ...]:
    match = re.search(r"(\d+)\.(\d+)\.(\d+)", text or "")
    return tuple(int(x) for x in match.groups()) if match else ()


def gpu_escape_verdict(ctx: Any) -> Ch9Verdict:
    """gpu-01（AC-17）：版本阈值 + 注入面判定；无工具链即 BLOCKED。"""
    toolkit_raw = getattr(ctx, "gpu_toolkit_version", "")
    if not toolkit_raw:
        return Ch9Verdict("ch9-gpu", BLOCKED, "no_tool",
                          "未取得 nvidia-container-toolkit 版本",
                          "dpkg-query -W nvidia-container-toolkit",
                          "判定依据：无 GPU 工具链版本，按缺口记录不伪造")
    version = _parse_version(toolkit_raw)
    if not version:
        return Ch9Verdict("ch9-gpu", BLOCKED, "no_tool",
                          "无法解析工具链版本", "dpkg-query -W nvidia-container-toolkit",
                          toolkit_raw[:400])
    affected = version <= AFFECTED_CEILING
    has_hook = bool(getattr(ctx, "gpu_hook_surface", False))
    env_injection = bool(getattr(ctx, "gpu_env_injection", False))
    command = ("dpkg-query -W nvidia-container-toolkit ; runc --version ; "
               "grep cuda-compat-mode /etc/nvidia-container-runtime/config.toml")
    output = ("toolkit=%s affected(≤1.17.7)=%s\n"
              "hook surface=%s；ENV 注入面=%s\n"
              "依据：NVD CVE-2025-23266（CWE-426，CVSS 9.0）"
              % (toolkit_raw.strip(), affected, has_hook, env_injection))
    if not affected:
        return Ch9Verdict("ch9-gpu", ABSENT, "none_found",
                          "版本高于受影响上限", command, output,
                          {"version": ".".join(map(str, version))})
    if not (has_hook and env_injection):
        return Ch9Verdict("ch9-gpu", BLOCKED, "none_found",
                          "版本受影响但注入面不完整", command, output,
                          {"version": ".".join(map(str, version))})
    return Ch9Verdict("ch9-gpu", EXPLOITED, "",
                      "满足 CVE-2025-23266 逃逸条件（判定，不执行载荷）",
                      command, output,
                      {"version": ".".join(map(str, version)),
                       "cve": "CVE-2025-23266", "cwe": "CWE-426",
                       "note": "技术细节引自课程源 Ch9 L58-63，非 NVD 逐字"})
