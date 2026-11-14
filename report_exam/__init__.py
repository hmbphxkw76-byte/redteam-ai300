"""report_exam — OSAI / AI-300 官方规范考试报告组装器。

公开入口（Seam-1 唯一注入点）：assemble_report(evidence_source, ...)。
不重新取证、不虚构利用过程、不调用 PyRIT（基线 B7 对本技能不适用）。
"""
# SKILL.md §6 声明的五步执行体（证据契约机读对齐常量，B4）。
# 须定义在任何子模块导入之前，供 assemble.py 无循环引用。
EVIDENCE_STEPS = ("rpt-01", "rpt-02", "rpt-03", "rpt-04", "rpt-05")

from ._types import Fragment, ReportModel
from .index import (EvidenceSource, DirEvidenceSource, MemoryEvidenceSource,
                    build_index, parse_fragment)
from .skeleton import render_skeleton
from .sections import render_host_section, render_all_host_sections
from .ai_appendix import collect_ai_logs
from .bilingual import render_bilingual, extract_facts
from .package import package, verify_report, render_pdf, make_archive
from .assemble import assemble_report

__all__ = [
    "EVIDENCE_STEPS",
    "Fragment", "ReportModel",
    "EvidenceSource", "DirEvidenceSource", "MemoryEvidenceSource",
    "build_index", "parse_fragment",
    "render_skeleton", "render_host_section", "render_all_host_sections",
    "collect_ai_logs", "render_bilingual", "extract_facts",
    "package", "verify_report", "render_pdf", "make_archive",
    "assemble_report",
]
