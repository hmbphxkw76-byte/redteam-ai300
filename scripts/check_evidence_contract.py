#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""S1 静态检查：4 份 EvidenceWriter 适配器符合 tools/_evidence_contract.py 最小契约。

三项校验，全部静态、零副作用（不实例化适配器、不触发子进程）：
  1. 适配器显式继承 EvidenceWriterContract —— 契约不得只是 docstring 里的装饰符号；
  2. emit 最小签名统一为 self, step_id, command, output，output 及其后参数均有默认值
     （或为 **kwargs），保证 emit(step_id, command) 在四者上都可调用；
  3. describe / fragment_path / emit 的返回标注与 Protocol 一致，
     emit 返回形态为 (片段路径, 退出码, 错误摘要)。

各适配器构造签名与关键字别名保持不变；期望返回形态从 Protocol 读取，不在此重复定义（C1）。

用法：python scripts/check_evidence_contract.py
退出码：0=全部符合；1=存在不符合；2=用法/内部错误。
"""
from __future__ import annotations

import importlib
import inspect
import os
import sys
from typing import get_args, get_origin, get_type_hints

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools._evidence_contract import CONTRACT_MEMBERS, EvidenceWriterContract  # noqa: E402

ADAPTERS = (
    ("recon-ai (公共 seam)", "tools.recon_ai.evidence", "EvidenceWriter"),
    ("attack-infra", "tools.attack_infra.evidence", "EvidenceWriter"),
    ("decoy-detect", "tools.decoy_detect.evidence", "EvidenceWriter"),
    ("capstone-rehearse", "tools.capstone_rehearse.evidence", "EvidenceWriter"),
)

_EXPECTED_RETURN = get_type_hints(EvidenceWriterContract.emit)["return"]


def _shape_ok(annotation) -> bool:
    """返回标注是否与 Protocol 的 (str, int, str) 一致。"""
    return get_origin(annotation) is tuple and get_args(annotation) == (str, int, str)


def check() -> int:
    problems = []
    for label, module_name, class_name in ADAPTERS:
        module = importlib.import_module(module_name)
        cls = getattr(module, class_name, None)
        if cls is None:
            problems.append("%s：缺少 %s" % (label, class_name))
            continue
        if EvidenceWriterContract not in getattr(cls, "__mro__", ()):
            problems.append("%s：未显式继承 EvidenceWriterContract（仅 docstring 引用不算）" % label)
        for member in CONTRACT_MEMBERS:
            attr = getattr(cls, member, None)
            if attr is None or not callable(attr):
                problems.append("%s.%s：缺少可调用成员 %s" % (label, class_name, member))
                continue
            try:
                ret = get_type_hints(attr).get("return")
            except Exception as exc:  # 标注引用了未定义符号
                problems.append("%s.%s 返回标注不可解析：%s" % (label, member, exc))
                continue
            if member == "emit":
                if not _shape_ok(ret):
                    problems.append("%s.emit 返回形态不符：%r（应为 %r）"
                                    % (label, ret, _EXPECTED_RETURN))
            elif ret is not str:
                problems.append("%s.%s 返回标注应为 str，实际 %r" % (label, member, ret))
        emit = getattr(cls, "emit", None)
        if callable(emit):
            params = list(inspect.signature(emit).parameters.values())
            names = [p.name for p in params]
            if names[:4] != ["self", "step_id", "command", "output"]:
                problems.append("%s.emit 最小签名不符：%s" % (label, names[:4]))
            else:
                if params[3].default is inspect.Parameter.empty:
                    problems.append("%s.emit.output 必须可选（当前必填）" % label)
                for p in params[4:]:
                    if p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD):
                        continue
                    if p.default is inspect.Parameter.empty:
                        problems.append("%s.emit 存在必填的可选参数 %s" % (label, p.name))
    if problems:
        print("EvidenceWriter 契约检查：BLOCKED")
        for p in problems:
            print("  - " + p, file=sys.stderr)
        return 1
    print("EvidenceWriter 契约检查：PASS（%d 个适配器：继承 + 最小签名 + 返回形态）" % len(ADAPTERS))
    return 0


if __name__ == "__main__":
    sys.exit(check())
