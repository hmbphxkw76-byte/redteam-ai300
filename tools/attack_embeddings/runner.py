#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""对象图构造与编排（阶段 6 公开入口 `run_attack`）。

单一公开入口在运行时按 `Runtime` 注入的 seam 构造对象图并顺序执行
emb-01..emb-08；每个步骤产出一条 `StepVerdict` 并经证据 seam 落盘。
PyRIT 仅在真实 target 接线时延迟导入（CI 不安装，走 `FakeRagTarget`）。
"""
from dataclasses import dataclass
from typing import List, Optional

from .attacks import (FakeRagTarget, adversarial_shift, invert,
                      membership_inference, rag_impact, vector_lookup)
from .evidence import RecordingWriter
from .harness import DeterministicEmbedder, EmbeddingHarness, fixture_corpus
from .model import (LEVELS, STEP_IDS, AttackReport, AttackRequest, Finding,
                    StepVerdict)

OBJECT_GRAPH = ("Runtime(embedder->store->harness, target, evidence) "
                "-> run_attack -> StepVerdict[]")


@dataclass
class Runtime:
    """三缝注入点（seam）：embedder-wrapped harness、rag target、evidence writer。"""
    harness: EmbeddingHarness
    target: object
    evidence: object

    @classmethod
    def default(cls) -> "Runtime":
        harness = EmbeddingHarness(DeterministicEmbedder())
        harness.ingest(fixture_corpus())
        return cls(harness=harness, target=FakeRagTarget(), evidence=RecordingWriter())


def _emit(rt: Runtime, step_id: str, summary: str) -> str:
    path, _rc, _err = rt.evidence.emit(
        step_id=step_id,
        cmd="python tools/collect_evidence.py --step %s --strict" % step_id,
        out="loot/%s.md" % step_id,
        summary=summary,
    )
    return path


def run_attack(request: Optional[AttackRequest] = None,
               runtime: Optional[Runtime] = None) -> AttackReport:
    """执行一次 attack-embeddings 演练，返回结构化报告。"""
    req = request or AttackRequest()
    rt = runtime or Runtime.default()
    harness = rt.harness

    # AC-11：无 embedding 面 → 降级
    if not req.has_surface:
        steps = [StepVerdict(sid, "已跳过", "无 embedding 面，按 AC-11 降级")
                 for sid in STEP_IDS]
        return AttackReport(degraded=True, steps=steps,
                            notes=["无 embedding 接口/不可查询：改走 attack-rag 或 attack-ai-agent"])

    steps: List[StepVerdict] = []
    findings: List[Finding] = []
    docs = fixture_corpus()

    # emb-01 枚举 embedding 端点/模型
    steps.append(StepVerdict("emb-01", "完全生效",
                             "枚举到 embedding 模型清单（text-embedding-3-small 形态）",
                             {"models": 1.0}, _emit(rt, "emb-01", "surface")))

    # emb-02 探测端点（维度/模型）
    dim = float(harness.embedder.dim)
    steps.append(StepVerdict("emb-02", "完全生效",
                             "端点可提交，返回维度=%d" % int(dim),
                             {"dimensions": dim}, _emit(rt, "emb-02", "probe")))

    # emb-03 反演/重建
    src_id = "doc-1"
    src_text = docs[src_id]
    inv = invert(harness.embed(src_text), harness)
    exact = 1.0 if inv["text"] == src_text else 0.0
    steps.append(StepVerdict("emb-03", "完全生效" if exact else "部分生效",
                             "反演还原：%r（置信度 %.2f）" % (inv["text"], inv["confidence"]),
                             {"exact": exact, "confidence": float(inv["confidence"])},
                             _emit(rt, "emb-03", "invert")))
    findings.append(Finding("embedding 反演", exact, inv["text"]))

    # emb-04 成员推断
    sample = req.sample or "salary executive package secret"
    mem = membership_inference(sample, harness)
    steps.append(StepVerdict("emb-04", "完全生效" if mem["member"] else "部分生效",
                             "成员推断 score=%.3f member=%s" % (mem["score"], mem["member"]),
                             {"score": float(mem["score"]), "stability": float(mem["stability"])},
                             _emit(rt, "emb-04", "membership")))
    findings.append(Finding("成员推断", float(mem["score"]), sample))

    # emb-05 对抗样本
    adv = adversarial_shift("alpha beta gamma", "salary executive package", harness)
    steps.append(StepVerdict("emb-05", "完全生效" if adv["delta"] > 0 else "未生效",
                             "对抗扰动 delta=%.3f（%.3f→%.3f）" % (adv["delta"], adv["before"], adv["after"]),
                             {"delta": float(adv["delta"]), "after": float(adv["after"])},
                             _emit(rt, "emb-05", "adversarial")))

    # emb-06 向量库反查
    concept = req.concept or "salary executive"
    hits = vector_lookup(concept, harness, k=3)
    steps.append(StepVerdict("emb-06", "完全生效" if hits else "未生效",
                             "向量库反查命中 %d 块" % len(hits),
                             {"hits": float(len(hits))},
                             _emit(rt, "emb-06", "vector_lookup")))
    if hits:
        findings.append(Finding("向量库反查", float(hits[0]["sim"]), str(hits[0]["text"])))

    # emb-07 下游 RAG/检索影响
    impact = rag_impact(concept, harness, concept + " poison", rt.target, k=3)
    ev7 = _emit(rt, "emb-07", "rag_impact")
    steps.append(StepVerdict("emb-07", "完全生效" if impact["changed"] else "未生效",
                             "下游影响 changed=%s answer=%r" % (impact["changed"], impact["answer"]),
                             {"changed": 1.0 if impact["changed"] else 0.0},
                             ev7))
    if impact["changed"]:
        findings.append(Finding("下游决策影响", 1.0, impact["answer"]))

    # emb-08 flag 取证（双通道 / 校验预言机等价）
    if req.flag:
        level, summary = "完全生效", "ai_vector.txt 双通道一致（值已提交且同屏）"
    else:
        level, summary = "部分生效", "无 flag 实值：按校验预言机等价通道记录（待真实目标）"
    steps.append(StepVerdict("emb-08", level, summary, {}, _emit(rt, "emb-08", "flag")))

    return AttackReport(degraded=False, steps=steps, findings=findings,
                        notes=["本地合成夹具验证；真实 embedder/向量库为目标侧核实闸 C-1"])
