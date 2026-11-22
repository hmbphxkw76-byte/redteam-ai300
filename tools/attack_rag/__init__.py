#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-rag：RAG 投毒与检索层操纵（P0 · D5 · AI向量机）。

公开面只有 `run_attack`（唯一入口）、`Runtime`（三缝注入点）与数据模型；
其余模块为实现细节，可自由重构而不影响调用方（深层模块原则）。

顶层零 pyrit 依赖：真实执行才在方法体内延迟导入（ADR-0004）。
"""
from .architecture import from_surface as arch_from_surface, render as arch_render
from .backends import FakeBackend, RealPyRITBackend
from .blend import citation_name, payload_budget, safe_offset
from .capability import dormant_doc, filter_asymmetry, probe, ProbeResult
from .ch5 import CH5_STEP_IDS, CH5_STEP_SPECS, run_ch5
from .ch11 import CH11_STEP_IDS, CH11_STEP_SPECS, run_ch11
from .agent_log import (classify_events, has_periodic_heartbeat, infer_agent_identity,
                        infer_trigger_keyword, key_path_candidates, extract_pem)
from .decision_diff import DecisionDiff, DiffResult
from .extract import hit_rate, multi_topic_collision, one_shot, probe_prompt
from .harness import MALICIOUS_MARKER, RagHarness, RetrievalHit, default_corpus
from .index_tamper import IndexTamper
from .ingest import (FakeIngestChannel, FileIngestChannel, HttpIngestChannel,
                     IngestResult, ReadOnlyChannel, channel_for)
from .model import (LEVELS, AttackReport, AttackRequest, FlagProof, StepVerdict,
                    XpiaOutcome)
from .obfuscation import (homoglyph, indirect_instruction, multimodal_camouflage,
                          rotate, zero_widthify, ZERO_WIDTH_CODEPOINTS, HOMOGLYPHS)
from .poisoned_rag import PoisonedRAGInjector
from .readchain import batch_lines, match_user, parse_uid
from .slow_drip import event_fatigue, pdf_note, timeline
from .retrieval_probe import (BeforeAfter, EmbeddingCollisionCraft, RetrievalProbe,
                              TopKTable)
from .runner import DEFAULT_EVIDENCE_DIR, OBJECT_GRAPH, Runtime, run_attack
from .steps import STEP_IDS, STEP_SPECS, steps_for_paths
from .surface import (RagSurface, from_inventory, surface_from_file, synthetic,
                      validate_flags)
from .xapia import XpiaResult, build_payload, run_xpia

__all__ = [
    "run_attack", "Runtime", "OBJECT_GRAPH", "DEFAULT_EVIDENCE_DIR",
    "AttackRequest", "AttackReport", "StepVerdict", "FlagProof", "XpiaOutcome",
    "LEVELS", "STEP_IDS", "STEP_SPECS", "steps_for_paths",
    "RagHarness", "RetrievalHit", "default_corpus", "MALICIOUS_MARKER",
    "PoisonedRAGInjector", "RetrievalProbe", "BeforeAfter", "TopKTable",
    "EmbeddingCollisionCraft", "DecisionDiff", "DiffResult", "IndexTamper",
    "RagSurface", "surface_from_file", "from_inventory", "synthetic", "validate_flags",
    "IngestResult", "HttpIngestChannel", "FileIngestChannel",
    "FakeIngestChannel", "ReadOnlyChannel", "channel_for",
    "run_xpia", "build_payload", "XpiaResult",
    "FakeBackend", "RealPyRITBackend",
    "run_ch5", "CH5_STEP_IDS", "CH5_STEP_SPECS",
    "run_ch11", "CH11_STEP_IDS", "CH11_STEP_SPECS",
    "classify_events", "has_periodic_heartbeat", "infer_agent_identity",
    "infer_trigger_keyword", "key_path_candidates", "extract_pem",
    "probe", "ProbeResult", "filter_asymmetry", "dormant_doc",
    "parse_uid", "match_user", "batch_lines",
    "zero_widthify", "homoglyph", "indirect_instruction", "rotate",
    "multimodal_camouflage", "ZERO_WIDTH_CODEPOINTS", "HOMOGLYPHS",
    "probe_prompt", "one_shot", "multi_topic_collision", "hit_rate",
    "safe_offset", "payload_budget", "citation_name",
    "arch_from_surface", "arch_render",
    "timeline", "event_fatigue", "pdf_note",
]
