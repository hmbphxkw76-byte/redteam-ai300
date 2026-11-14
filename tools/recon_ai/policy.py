#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""执行分级、诱饵判定、时间盒与失败隔离（OPSEC 纪律的可执行部分）。

分级语义（见设计记录 §4）：
  - passive（默认）：无状态变更的 HTTP 读 + 一次无害回显 POST；
  - active（显式）：追加定向端口探测（上限 8 个），禁止全端口扫描。
"""
TIMEOUT_MINUTES = 30
MAX_ACTIVE_PORTS = 8
PROFILES = ("passive", "active")


def normalize_profile(profile):
    """校验并归一执行分级；非法值抛 ValueError（CLI 转退出码 2）。"""
    value = (profile or "passive").strip().lower()
    if value not in PROFILES:
        raise ValueError("未知执行分级：%r（允许 %s）" % (profile, "/".join(PROFILES)))
    return value


def gate_requests(spec, profile):
    """返回当前分级下实际执行的请求；主动请求仅在 active 档且不超上限时纳入。"""
    from .probes import step_requests
    reqs = step_requests(spec, profile)
    if profile != "active":
        return reqs
    passive = list(spec.requests)
    active = reqs[len(passive):][:MAX_ACTIVE_PORTS]
    return passive + active


def judge_decoy(present_categories, total=7):
    """零组件判定：把疑似诱饵主机降级并给出依据（US-23 / AC-21）。"""
    if present_categories:
        return False, ""
    return True, ("被动面 0/%d 类 AI 组件指纹；按 SKILL.md 失败与豁免降级为轻量枚举，"
                  "%d 分钟内结束，不在 0 分主机空耗" % (total, TIMEOUT_MINUTES))


class FailureBudget:
    """失败隔离：单面失败不阻塞其余枚举（US-24 / AC-22）。"""

    def __init__(self):
        self.failed = []
        self.reasons = {}

    def record(self, step_id, reason):
        if step_id not in self.failed:
            self.failed.append(step_id)
        self.reasons[step_id] = reason

    @property
    def failed_steps(self):
        return list(self.failed)

    def summary(self):
        if not self.failed:
            return "无失败步骤"
        return "；".join("%s: %s" % (s, self.reasons.get(s, "")) for s in self.failed)
