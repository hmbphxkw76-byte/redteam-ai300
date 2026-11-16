#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""capstone-rehearse：考前演练走查（D11 / P2 / 通用验收）。

公开入口见设计 `docs/operations/capstone-rehearse-design.md` §2；
`rehearse()` 是唯一深层模块入口与对象图构造收敛点。
"""
from .clock import Clock, FixedClock, SystemClock
from .evidence import EvidenceWriter
from .inventory import (MemoryStageInventory, RepoStageInventory, StageInventory,
                        stages_from_specs)
from .model import (BLOCKING, NON_BLOCKING, SCHEMA_VERSION, CoverageRow, Gap,
                    RehearsalResult, Stage, StageEvidence, TimelineSlot)
from .report import render_report, render_summary
from .walk import rehearse

__all__ = [
    "SCHEMA_VERSION", "BLOCKING", "NON_BLOCKING",
    "Stage", "StageEvidence", "CoverageRow", "TimelineSlot", "Gap",
    "RehearsalResult", "StageInventory", "RepoStageInventory",
    "MemoryStageInventory", "stages_from_specs", "Clock", "FixedClock",
    "SystemClock", "EvidenceWriter", "rehearse", "render_report",
    "render_summary",
]
