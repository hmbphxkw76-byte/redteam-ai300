"""结构化告警：JSONL + GitHub Actions 注解，非零退出码由 checker 统一决定。"""
from __future__ import annotations

import json
import os
import sys

from .model import Alert


def emit(alert: Alert, stream=None) -> None:
    stream = stream or sys.stderr
    stream.write(json.dumps(alert.to_dict(), ensure_ascii=False, sort_keys=True) + "\n")
    if os.environ.get("GITHUB_ACTIONS") and alert.file:
        level = {"error": "error", "warn": "warning", "info": "notice"}[alert.severity]
        loc = "%s,%s" % (alert.file, alert.line or 1)
        stream.write("::%s file=%s::%s\n" % (level, loc, alert.message))


def count_errors(alerts: list[Alert]) -> int:
    return sum(1 for a in alerts if a.severity == "error")
