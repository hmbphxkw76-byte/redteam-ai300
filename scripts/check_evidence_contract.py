#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S1 静态检查：4 份 EvidenceWriter 适配器符合 tools/_evidence_contract.py 最小契约。

只做结构符合性检查（方法存在 + 可调用），不实例化适配器、不触发子进程，
因此零副作用、零外部依赖。适配器保留各自构造签名与关键字别名。

用法：python scripts/check_evidence_contract.py
退出码：0=全部符合；1=存在不符合；2=用法/内部错误。
"""
from __future__ import annotations

import inspect
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools._evidence_contract import CONTRACT_MEMBERS  # noqa: E402

ADAPTERS = (
    ("recon-ai (公共 seam)", "tools.recon_ai.evidence", "EvidenceWriter"),
    ("attack-infra", "tools.attack_infra.evidence", "EvidenceWriter"),
    ("decoy-detect", "tools.decoy_detect.evidence", "EvidenceWriter"),
    ("capstone-rehearse", "tools.capstone_rehearse.evidence", "EvidenceWriter"),
)


def check() -> int:
    import importlib
    problems = []
    for label, module_name, class_name in ADAPTERS:
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name, None)
        if cls is None:
            problems.append("%s：缺少 %s" % (label, class_name))
            continue
        for member in CONTRACT_MEMBERS:
            attr = getattr(cls, member, None)
            if attr is None or not callable(attr):
                problems.append("%s.%s：缺少可调用成员 %s" % (label, class_name, member))
                continue
            if member == "emit":
                sig = inspect.signature(attr)
                params = list(sig.parameters)
                if len(params) < 4 or params[:3] != ["self", "step_id", "command"]:
                    problems.append("%s.emit 签名不符：%s" % (label, sig))
    if problems:
        print("EvidenceWriter 契约检查：BLOCKED")
        for p in problems:
            print("  - " + p, file=sys.stderr)
        return 1
    print("EvidenceWriter 契约检查：PASS（%d 个适配器符合最小契约）" % len(ADAPTERS))
    return 0


if __name__ == "__main__":
    sys.exit(check())
