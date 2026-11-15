#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-rag：RAG 投毒与检索层操纵（P0 · D5 · AI向量机）。

公开面只有 `run_attack`（唯一入口）、`Runtime`（三缝注入点）与数据模型；
其余模块为实现细节，可自由重构而不影响调用方（深层模块原则）。

顶层零 pyrit 依赖：真实执行才在方法体内延迟导入（ADR-0004）。
"""
from .backends import FakeBackend, RealPyRITBackend
from .decision_diff import DecisionDiff, DiffResult
from .harness import MALICIOUS_MARKER, RagHarness, RetrievalHit, default_corpus
from .model import (LEVELS, AttackReport, AttackRequest, FlagProof, StepVerdict,
                    XpiaOutcome)
from .poisoned_rag import PoisonedRAGInjector
from .retrieval_probe import (BeforeAfter, EmbeddingCollisionCraft, RetrievalProbe,
                              TopKTable)
from .runner import DEFAULT_EVIDENCE_DIR, OBJECT_GRAPH, Runtime, run_attack
from .steps import STEP_IDS, STEP_SPECS, steps_for_paths
from .xapia import XpiaResult, build_payload, run_xpia

__all__ = [
    "run_attack", "Runtime", "OBJECT_GRAPH", "DEFAULT_EVIDENCE_DIR",
    "AttackRequest", "AttackReport", "StepVerdict", "FlagProof", "XpiaOutcome",
    "LEVELS", "STEP_IDS", "STEP_SPECS", "steps_for_paths",
    "RagHarness", "RetrievalHit", "default_corpus", "MALICIOUS_MARKER",
    "PoisonedRAGInjector", "RetrievalProbe", "BeforeAfter", "TopKTable",
    "EmbeddingCollisionCraft", "DecisionDiff", "DiffResult",
    "run_xpia", "build_payload", "XpiaResult",
    "FakeBackend", "RealPyRITBackend",
]
