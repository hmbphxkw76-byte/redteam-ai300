#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""证据落盘 seam（S2）：委托共享收集器，不重实现格式。

单一事实源：片段结构、件套判定、flag 双通道、证据清单 JSONL 均由
`tools/collect_evidence.py` 定义；本模块只负责「把一次步骤的执行结果喂给它」（C1）。
"""
import os

# 单一事实源（C1）：证据写入与清单解析复用 `tools/recon_ai/evidence.py`，
# 本模块只补一个不写盘的记录型替身，供离线断言证据契约。
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
