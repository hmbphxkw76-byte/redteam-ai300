#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-embeddings：embedding 反演与信息提取（P1 · D6 · AI向量机）。

公开面只有三项：`run_attack`（唯一入口）、`Runtime`（三缝注入点）、
数据模型（`AttackRequest` / `AttackReport` / `StepVerdict` / `LEVELS`），
外加攻击原语与夹具供直接调用。其余为实现细节，可自由重构（深层模块原则）。
"""
from .attacks import (FakeRagTarget, adversarial_shift, invert,
                      membership_auc, membership_inference, rag_impact,
                      vector_lookup)
from .harness import (DeterministicEmbedder, EmbeddingHarness,
                      InMemoryVectorStore, fixture_corpus)
from .model import (LEVELS, STEP_IDS, AttackReport, AttackRequest, Finding,
                    StepVerdict)
from .runner import OBJECT_GRAPH, Runtime, run_attack

__all__ = [
    "run_attack", "Runtime", "OBJECT_GRAPH",
    "AttackRequest", "AttackReport", "StepVerdict", "Finding",
    "LEVELS", "STEP_IDS",
    "DeterministicEmbedder", "InMemoryVectorStore", "EmbeddingHarness",
    "fixture_corpus", "FakeRagTarget",
    "invert", "membership_inference", "membership_auc", "adversarial_shift",
    "vector_lookup", "rag_impact",
]
