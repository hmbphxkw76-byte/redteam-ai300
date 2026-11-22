#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 扩展编排：独立入口，不改动既有 infra-01..08 的 STEPS 表（AC-20）。

消费 `RunContext`（唯一 seam）；每个子步骤的结论可经 runner.attach_evidence
落盘证据（三件套），保持与既有证据契约兼容。
"""
from typing import Callable, Dict, List

from . import ch9_container, ch9_gpu, ch9_iam, ch9_k8s, ch9_scope, ch9_secrets
from .ch9_model import Ch9Verdict
from .evidence import EvidenceWriter
from .model import RunContext
from .runner import attach_evidence
from .shot import ShotPlanner

CH9_STEPS: Dict[str, Callable[[RunContext], Ch9Verdict]] = {
    "ch9-iam-01": ch9_iam.enumerate_policies_step,
    "ch9-iam-02": ch9_iam.trust_step,
    "ch9-iam-03": ch9_iam.chain_verdict,
    "ch9-k8s-01": ch9_k8s.token_surface,
    "ch9-k8s-02": ch9_k8s.same_rules_across_ns,
    "ch9-k8s-04": ch9_k8s.capability_matrix,
    "ch9-sec-01": ch9_secrets.hunt_services,
    "ch9-sec-02": ch9_secrets.ssm_old_password,
    "ch9-sec-03": ch9_secrets.filter_log_hits,
    "ch9-ctr-01": ch9_container.writable_shared_volume,
    "ch9-ctr-02": ch9_container.intercept_verdict,
    "ch9-scope": ch9_scope.scope_gate,
    "ch9-opsec": ch9_scope.opsec_advice,
    "ch9-gpu": ch9_gpu.gpu_escape_verdict,
}


def _attach_ch9_evidence(ctx: RunContext, verdict: Ch9Verdict) -> Ch9Verdict:
    """把 Ch9 结论喂给既有证据 seam（三件套 + 截图计划 + flag 双通道）。

    复用 `runner.attach_evidence`：其读取 verdict.evidence_extra / command / output
    并调用 ctx.evidence.emit(strict=True)，与 infra-01..08 同一契约（B4/AC-18）。
    """
    if ctx.evidence is None:
        return verdict
    if ctx.shot is None:
        ctx.shot = ShotPlanner()
    attached = attach_evidence(ctx, verdict)  # type: ignore[arg-type]
    verdict.evidence_path = attached.evidence_path
    verdict.evidence_ok = attached.evidence_ok
    for key, value in attached.evidence_extra.items():
        verdict.evidence_extra.setdefault(key, value)
    return verdict


def run_ch9(ctx: RunContext, attach=None) -> List[Ch9Verdict]:
    """按 `ctx.ch9_step_ids` 过滤执行；未知 step 直接报错（与既有 runner 一致）。

    `attach` 缺省为 `_attach_ch9_evidence`（证据契约 B4）；显式传 `attach=False`
    可关闭（仅测试用），便于离线验证纯判定逻辑。
    """
    requested = tuple(getattr(ctx, "ch9_step_ids", ())) or tuple(CH9_STEPS)
    unknown = [s for s in requested if s not in CH9_STEPS]
    if unknown:
        raise ValueError("未知 Ch9 步骤：%s" % ", ".join(unknown))
    do_attach = _attach_ch9_evidence if attach is None else attach
    verdicts: List[Ch9Verdict] = []
    for step_id in requested:
        verdict = CH9_STEPS[step_id](ctx)
        if callable(do_attach):
            verdict = do_attach(ctx, verdict)
        verdicts.append(verdict)
    return verdicts
