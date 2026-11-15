#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S3 模型扫描 seam：封装 ModelScan CLI/JSON（AC-04 反向证据）。

默认 runner 调 `modelscan -p <path> -r json`；`runner` 注入点供测试返回预置 JSON。
干净结果 != 可证明安全：`is_malicious_detected` 仅在严重度 >= MEDIUM 时判真，
其余须由调用方显式记录「未检出原因」（AC-04 分支）。
"""
import json
import shutil
import subprocess
from dataclasses import dataclass, field

SEVERITY_ORDER = {"NONE": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
MALICIOUS_THRESHOLD = {"MEDIUM", "HIGH", "CRITICAL"}


@dataclass
class ScanResult:
    findings: list = field(default_factory=list)
    severity_max: str = "NONE"
    exit_code: int = 0
    skipped: list = field(default_factory=list)

    def is_clean(self):
        return not self.findings


def _default_runner(path):
    exe = shutil.which("modelscan")
    if not exe:
        raise FileNotFoundError("未找到 modelscan（pip install modelscan）")
    proc = subprocess.run([exe, "-p", path, "-r", "json"],
                          capture_output=True, text=True)
    return proc.returncode, proc.stdout


def _max_severity(findings):
    best = "NONE"
    for f in findings:
        sev = str(f.get("severity", "NONE")).upper()
        if SEVERITY_ORDER.get(sev, 0) > SEVERITY_ORDER.get(best, 0):
            best = sev
    return best


def scan(path, runner=None):
    """执行扫描；`runner(path)->(exit_code, stdout)`. 返回 ScanResult。"""
    runner = runner or _default_runner
    code, out = runner(path)
    data = {}
    if out and out.strip():
        try:
            data = json.loads(out)
        except json.JSONDecodeError:
            data = {}
    findings = data.get("issues") or data.get("findings") or []
    skipped = data.get("skipped") or []
    return ScanResult(findings=list(findings),
                      severity_max=_max_severity(findings),
                      exit_code=code, skipped=list(skipped))


def is_malicious_detected(result):
    """严重度 >= MEDIUM 视为检出恶意；否则须显式记录未检出原因（AC-04）。"""
    return result.severity_max in MALICIOUS_THRESHOLD
