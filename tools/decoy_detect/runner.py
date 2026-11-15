#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""诱饵判定编排（纯逻辑，无 IO / 无网络）。

把一台台主机记录穿过「特征提取 → 时间盒 → 判定策略 → 清单 → 质量门」，
产出 RunReport。证据落盘与文件写入由 `cli.py` 负责，使本模块可被纯单测覆盖。
"""
from . import features, listgen, policy, validate
from .model import DecoyJudgment, JudgmentConclusion, now_iso
from .timebox import DEFAULT_LIMIT_SECONDS, TimeBoxTracker


class RunReport:
    """一次判定的结果聚合（人类可读 + 机读）。"""

    def __init__(self, judgments, markdown, violations, expected_decoys,
                 scored_count=0):
        self.judgments = judgments
        self.markdown = markdown
        self.violations = violations
        self.expected_decoys = expected_decoys
        self.scored_count = scored_count

    @property
    def decoy_count(self):
        return sum(1 for j in self.judgments
                   if j.conclusion == JudgmentConclusion.DECOY)

    @property
    def uncertain_count(self):
        return sum(1 for j in self.judgments
                   if j.conclusion == JudgmentConclusion.UNCERTAIN_ABANDONED)

    @property
    def passed(self):
        return not self.violations

    def to_dict(self):
        return {
            "decoy_count": self.decoy_count,
            "uncertain_count": self.uncertain_count,
            "scored_count": self.scored_count,
            "expected_decoys": self.expected_decoys,
            "violations": list(self.violations),
            "passed": self.passed,
            "count_matches": self.decoy_count == self.expected_decoys,
            "judgments": [j.to_dict() for j in self.judgments],
        }


def _is_cross_validated(host):
    """交叉验证信号：显式 cross_validated 或 threat-model 初筛存在。"""
    return bool(host.get("cross_validated")) or host.get("threat_model_decoy") is True


def run_scan(scan, timebox_limit_seconds=DEFAULT_LIMIT_SECONDS,
             timestamp_fn=now_iso):
    """对一组主机记录执行诱饵判定，返回 RunReport。

    `scan` 为 model.ScanInput；`timestamp_fn` 可注入以稳定测试。
    """
    tracker = TimeBoxTracker(limit_seconds=timebox_limit_seconds)
    judgments = []
    scored = 0
    for host in scan.hosts:
        signals = features.extract(host)
        hits = features.classify_dimensions(signals)
        elapsed = host.get("elapsed_seconds", 0)
        tracker.record(signals.host_id, elapsed)
        exceeded = tracker.exceeded(signals.host_id)
        cross = _is_cross_validated(host)
        threat = host.get("threat_model_decoy") is True
        conclusion = policy.decide(hits, cross_validated=cross,
                                   threat_model_decoy=threat)
        if exceeded:
            conclusion = JudgmentConclusion.UNCERTAIN_ABANDONED
        if conclusion == JudgmentConclusion.SCORED:
            scored += 1
            continue
        judgments.append(DecoyJudgment(
            host_id=signals.host_id,
            hit_dimensions=hits,
            evidence=features.explain(signals),
            abandonment_reason=policy.abandonment_reason(conclusion, hits, exceeded),
            conclusion=conclusion,
            timestamp=timestamp_fn(),
            elapsed_seconds=tracker.elapsed(signals.host_id),
            timebox_exceeded=exceeded,
            cross_validated=cross,
        ))
    markdown = listgen.render_markdown(judgments, scan.expected_decoys)
    violations = validate.validate_quality_gate(judgments, timebox_limit_seconds)
    return RunReport(judgments, markdown, violations, scan.expected_decoys, scored)
