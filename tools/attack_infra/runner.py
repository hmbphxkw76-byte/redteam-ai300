#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""编排：步骤 → 判定 → 证据 → 汇总。

唯一注入点 `RunContext`（设计记录 §4）。诱饵机判据命中时**零请求**返回（AC-17）。
证据门失败（共享容器退出码非 0）不改变判定，但标记 `evidence_ok=False`，
由报告与退出码视为阻断项（B4 / AC-15）。
"""
import time
from dataclasses import dataclass, replace
from typing import Callable, Dict, List

from . import path_a, path_b, path_c, report as report_mod
from .model import Outcome, RunContext, RunReport, StepVerdict
from .shot import ShotPlanner

STEPS: Dict[str, Callable[[RunContext], StepVerdict]] = {
    "infra-01": path_a.discover,
    "infra-02": path_a.cloud_misconfig,
    "infra-03": path_a.model_server,
    "infra-04": path_b.container,
    "infra-05": path_b.gateway,
    "infra-06": path_c.privesc,
    "infra-07": path_c.impact,
    "infra-08": path_c.flag,
}


def _evidence_kwargs(ctx: RunContext, verdict: StepVerdict) -> dict:
    kwargs = dict(verdict.evidence_extra)
    planner = ctx.shot or ShotPlanner()
    plan = planner.plan(verdict.step_id, url=ctx.target)
    kwargs.setdefault("shot_cmd", plan.cmd)
    kwargs.setdefault("shot_kind", plan.kind)
    return kwargs


def attach_evidence(ctx: RunContext, verdict: StepVerdict) -> StepVerdict:
    """把步骤结论喂给证据 seam；失败只标记，不抛异常。"""
    if ctx.evidence is None:
        return verdict
    kwargs = _evidence_kwargs(ctx, verdict)
    path, code, err = ctx.evidence.emit(
        verdict.step_id, verdict.command, verdict.output,
        target=ctx.target, strict=True, **kwargs)
    verdict.evidence_path = path
    verdict.evidence_ok = code == 0
    if not verdict.evidence_ok:
        verdict.evidence_extra["evidence_error"] = err
    return verdict


def run(ctx: RunContext) -> RunReport:
    """按 `ctx.step_ids` 顺序执行；诱饵机与时间盒判据优先。"""
    if ctx.decoy:
        return RunReport(target=ctx.target, steps=[], notes=[
            "判定为疑似诱饵机：按 SKILL.md「失败与豁免」在 ≤%d 分钟内终止，未发起任何探测请求"
            % ctx.decoy_timebox_minutes,
        ])
    unknown = [sid for sid in ctx.step_ids if sid not in STEPS]
    if unknown:
        raise ValueError("未知步骤：%s" % ", ".join(unknown))
    result = RunReport(target=ctx.target)
    if ctx.inventory_endpoints:
        result.notes.append("复用 recon-ai 资产清单：%d 个候选端点参与 infra-01 探测"
                            % len(ctx.inventory_endpoints))
    started = time.monotonic()
    for step_id in ctx.step_ids:
        elapsed_min = (time.monotonic() - started) / 60.0
        if elapsed_min > ctx.decoy_timebox_minutes:
            result.notes.append("时间盒耗尽（%.1f > %d 分钟）：停止后续步骤，避免在低价值主机空耗"
                                % (elapsed_min, ctx.decoy_timebox_minutes))
            break
        verdict = STEPS[step_id](ctx)
        result.steps.append(attach_evidence(ctx, verdict))
    if any(v.outcome is Outcome.ABSENT for v in result.steps):
        result.notes.append("存在 ABSENT 结局：按 SKILL.md「失败与豁免」评估转技能")
    return result


@dataclass(frozen=True)
class TargetRun:
    """一次目标运行：主目标（AI向量机）或次要目标（独立机）。"""

    target: str
    role: str
    report: RunReport


def run_targets(ctx: RunContext) -> List[TargetRun]:
    """主目标 + 次要目标（独立机）依次运行；诱饵判定只在主目标生效。"""
    runs = [TargetRun(ctx.target, "AI向量机", run(ctx))]
    if ctx.decoy:
        return runs
    for target in ctx.secondary_targets:
        sub = replace(ctx, target=target, secondary_targets=(), decoy=False)
        runs.append(TargetRun(target, "独立机", run(sub)))
    return runs


def run_all(ctx: RunContext) -> RunReport:
    return run(ctx)


def summary(report: RunReport) -> str:
    return report_mod.summary(report)


def render(report: RunReport) -> str:
    return report_mod.render(report)


def exit_code(report: RunReport) -> int:
    return report_mod.exit_code(report)


