#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路径 B（infra-04..05）：容器化负载越权 / 推理网关凭据泄露。

判据来源：canonical F-5（LiteLLM 配置存上游密钥）、F-6（`auth can-i --list`
与 `system:serviceaccount:<ns>:<sa>`）、F-7（`list` 可读 secret 的 `data`）、
F-8（`nodes/proxy` 的 `get` 即命令执行）。凭据只产指纹（AC-09）。
"""
import os
import re
from typing import List

from .command import argv_to_text, curl_json
from .model import CredentialHint, Outcome, RunContext, StepVerdict

# 凭据模式：算法前缀 + 长度，仅用于定位；命中值不进入任何输出
CREDENTIAL_PATTERNS = (
    ("sk-", re.compile(r"sk-[A-Za-z0-9_\-]{8,}")),
    ("AKIA", re.compile(r"AKIA[0-9A-Z]{12,}")),
    ("Bearer", re.compile(r"Bearer\s+([A-Za-z0-9._\-]{8,})")),
)
HIGH_PRIV_TOKENS = ("*", "secrets", "pods/exec", "nodes/proxy", "cluster-admin")


def _kubectl_argv(ctx: RunContext) -> tuple:
    argv = ["kubectl", "auth", "can-i", "--list"]
    if ctx.namespace:
        argv += ["-n", ctx.namespace]
        if ctx.service_account:
            argv += ["--as=system:serviceaccount:%s:%s"
                     % (ctx.namespace, ctx.service_account)]
    return tuple(argv)


def container(ctx: RunContext) -> StepVerdict:
    """infra-04：以 `auth can-i --list` 判定容器化负载的授权面。"""
    argv = _kubectl_argv(ctx)
    command = argv_to_text(argv)
    result = ctx.command.run(argv, timeout=ctx.timeout)
    output = "$ %s\n(exit=%d)\n%s" % (command, result.code,
                                      (result.combined or "").strip()[:1500])
    if result.code == 127:
        return StepVerdict("infra-04", Outcome.ABSENT, reason="no_tool",
                           summary="未安装 kubectl，无法枚举授权面",
                           command=command, output=output)
    if result.ok:
        hits = [line.strip() for line in (result.stdout or "").splitlines()
                if any(tok in line for tok in HIGH_PRIV_TOKENS)]
        if hits:
            return StepVerdict("infra-04", Outcome.EXPOSED_NO_AUTH, "",
                               summary="授权面含 %d 条高权项（%d 条样本）"
                                       % (len(hits), min(3, len(hits))),
                               command=command, output=output)
        return StepVerdict("infra-04", Outcome.ABSENT, reason="none_found",
                           summary="授权面可列举但无高权项",
                           command=command, output=output)
    stderr = result.stderr or ""
    if any(tok in stderr for tok in ("Forbidden", "Unauthorized", "logged in",
                                     "must be logged")):
        return StepVerdict("infra-04", Outcome.AUTH_REQUIRED, reason="forbidden",
                           summary="匿名/低权身份被拒绝（RBAC 拦截）",
                           command=command, output=output)
    return StepVerdict("infra-04", Outcome.ABSENT, reason="network",
                       summary="kubectl 未取得可用响应", command=command,
                       output=output)


def _scan_file(path: str) -> List[CredentialHint]:
    hints: List[CredentialHint] = []
    if not os.path.isfile(path):
        return hints
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for lineno, line in enumerate(handle, 1):
                for prefix, pattern in CREDENTIAL_PATTERNS:
                    for match in pattern.finditer(line):
                        value = match.group(0)
                        if prefix == "Bearer":
                            value = match.group(1)
                        loc = "%s:%d" % (os.path.basename(path), lineno)
                        hints.append(CredentialHint(prefix=prefix,
                                                    length=len(value),
                                                    location=loc))
    except OSError:
        return hints
    return hints


def _dedupe(hints: List[CredentialHint]) -> List[CredentialHint]:
    seen, out = set(), []
    for hint in hints:
        if hint.key in seen:
            continue
        seen.add(hint.key)
        out.append(hint)
    return out


def gateway(ctx: RunContext) -> StepVerdict:
    """infra-05：推理网关配置中的凭据线索，只产出指纹。"""
    if not ctx.gateway_configs:
        return StepVerdict("infra-05", Outcome.ABSENT, reason="none_found",
                           summary="未提供待核网关配置文件",
                           output="判定依据：未提供 gateway_config，未执行凭据扫描",
                           command="grep -rEn 'sk-|AKIA|Bearer ' config.yaml")
    hints: List[CredentialHint] = []
    for path in ctx.gateway_configs:
        hints.extend(_scan_file(path))
    hints = _dedupe(hints)
    command = "grep -rEn 'sk-|AKIA|Bearer ' %s" % " ".join(ctx.gateway_configs)
    output = "\n".join("%s" % h.as_text() for h in hints) or "（无命中）"
    if hints:
        extra = {"note": "凭据仅记指纹；合法身份调用仅在显式开关下执行"}
        result = Outcome.EXPOSED_NO_AUTH
        summary = "检出 %d 条凭据指纹（未验证可用性）" % len(hints)
        if ctx.gateway_credential and ctx.gateway_verify_endpoint:
            if ctx.allow_inference:
                body = {"model": ctx.inference_model or "default",
                        "prompt": ctx.inference_prompt, "max_tokens": 8}
                # 命令只引用环境变量名，绝不写入凭据值（AC-09 / AC-18）
                verify_cmd = (curl_json(ctx.gateway_verify_endpoint, body)
                              + ' -H "Authorization: Bearer $GATEWAY_TOKEN"')
                resp = ctx.transport.request(
                    "POST", ctx.gateway_verify_endpoint, json_body=body,
                    headers={"Authorization": "Bearer %s" % ctx.gateway_credential},
                    timeout=ctx.timeout)
                safe_body = (resp.body or "").replace(ctx.gateway_credential,
                                                      "（已脱敏）")[:400]
                output += "\n\n$ %s\n(status=%d)\n%s" % (
                    verify_cmd, resp.status, safe_body or resp.error or "-")
                command = command + " ; " + verify_cmd
                if resp.ok:
                    result = Outcome.EXPLOITED
                    summary = "以合法身份调用推理成功（凭据仅记指纹）"
                else:
                    extra["note"] = "合法身份调用被拒绝（%d），凭据可用性未证实" % resp.status
            else:
                extra["note"] = "未开启 --allow-inference，未执行合法身份调用"
        return StepVerdict("infra-05", result, "", summary=summary,
                           command=command, output=output, evidence_extra=extra)
    return StepVerdict("infra-05", Outcome.ABSENT, reason="none_found",
                       summary="配置文件未命中凭据模式", command=command,
                       output=output)
