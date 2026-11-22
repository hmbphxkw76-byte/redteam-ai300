#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 B2：sidecar/init 共享卷拦截（AC-12..13）。

一手事实：`attack-infra-ch9-canonical.md` C-6；Ch9 Listing 54-55。
请求经 ctx.transport；不修改真实集群，只判定可拦截性与产出对照证据。
"""
import json
from typing import Any, Dict, List, Tuple

from .ch9_model import ABSENT, BLOCKED, EXPOSED_NO_AUTH, Ch9Verdict


def _parse_pod(pod_json: str) -> Tuple[List[Dict[str, Any]], List[str]]:
    """解析 Pod JSON，返回 (容器挂载列表, 卷名列表)。"""
    try:
        data = json.loads(pod_json)
    except (ValueError, TypeError):
        return [], []
    spec = data.get("spec", {}) if isinstance(data, dict) else {}
    containers = list(spec.get("containers") or [])
    volumes = [v.get("name", "") for v in (spec.get("volumes") or [])
               if isinstance(v, dict)]
    return containers, volumes


def writable_shared_volume(ctx: Any) -> Ch9Verdict:
    """ctr-01（AC-12）：判定是否存在可写共享卷且可被 sidecar exec。"""
    pod_json = getattr(ctx, "pod_json", "")
    containers, volumes = _parse_pod(pod_json)
    writable: Dict[str, List[str]] = {}
    for c in containers:
        if not isinstance(c, dict):
            continue
        for mount in c.get("volumeMounts") or []:
            if isinstance(mount, dict) and not mount.get("readOnly", False):
                writable.setdefault(mount.get("name", ""), []).append(c.get("name", ""))
    shared = {name: cs for name, cs in writable.items() if len(cs) >= 2}
    command = "kubectl get pod <pod> -o json | jq '.spec.containers[].volumeMounts'"
    output = "可写共享卷: %s" % (", ".join(sorted(shared)) or "无")
    if not shared:
        return Ch9Verdict("ch9-ctr-01", ABSENT, "none_found",
                          "无可写共享卷", command, output,
                          {"writable_volumes": {}})
    can_exec = bool(getattr(ctx, "can_exec_sidecar", False))
    outcome = EXPOSED_NO_AUTH if can_exec else BLOCKED
    reason = "" if can_exec else "forbidden"
    return Ch9Verdict("ch9-ctr-01", outcome, reason,
                      "可写共享卷 %d 个（sidecar exec=%s）" % (len(shared), can_exec),
                      command, output,
                      {"writable_volumes": shared, "can_exec": can_exec})


def intercept_verdict(ctx: Any) -> Ch9Verdict:
    """ctr-02（AC-13）：请求篡改前后响应对照，产出 AI 交互日志。"""
    before = getattr(ctx, "inference_before", "")
    after = getattr(ctx, "inference_after", "")
    prompt = getattr(ctx, "inference_prompt", "")
    if not before or not after:
        return Ch9Verdict("ch9-ctr-02", BLOCKED, "evidence_incomplete",
                          "缺篡改前后响应，无法取证", "# 两次推理调用",
                          "before=%s / after=%s" % (bool(before), bool(after)))
    changed = before.strip() != after.strip()
    ai_log = ("prompt: %s\n[before] %s\n[after] %s\n"
              "注：请求队列污染导致推理完整性变化（Ch9 L55）"
              % (prompt, before[:300], after[:300]))
    return Ch9Verdict("ch9-ctr-02", EXPOSED_NO_AUTH, "",
                      "下游推理行为发生变化（完整性被破坏）" if changed
                      else "响应一致（无状态服务，篡改未改变输出）",
                      "# 两次推理调用 + 共享请求队列写入",
                      "[before] %s\n[after] %s" % (before[:400], after[:400]),
                      {"changed": changed, "ai_log": ai_log})
