#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""证据落盘 seam（S3）：委托共享收集器，不重实现格式（C1）。

片段结构、件套判定、flag 双通道、证据清单 JSONL 均由
`tools/collect_evidence.py` / `tools/recon_ai/evidence.py` 定义；本模块只负责
「把一次步骤结果喂给它」，并提供不写盘的记录型替身供离线断言。
"""
import os

from tools.recon_ai.evidence import EvidenceWriter, load_manifest  # noqa: F401

DEFAULT_TOOL = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "tools", "collect_evidence.py")


class RecordingWriter:
    """测试替身：只记录调用参数，不写盘（用于断言证据契约）。"""

    def __init__(self):
        self.calls = []

    def describe(self):
        return "recording"

    def fragment_path(self, step_id):
        return "<memory>/%s.md" % step_id

    def emit(self, **kwargs):
        self.calls.append(kwargs)
        return self.fragment_path(kwargs.get("step_id", "")), 0, ""
