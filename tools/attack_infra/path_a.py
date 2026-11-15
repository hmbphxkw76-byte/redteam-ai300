#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""路径 A（infra-01..03）：基础设施面发现 / 云存储配置错误 / 模型服务器暴露。

判据来源：canonical F-2..F-5、F-8..F-11 与陷阱 P-1（三元组）、P-3（端口只是候选）、
P-4（只读优先）。所有网络动作经 `ctx.transport`，命令经 `ctx.command`。
"""
from typing import List, Tuple

from . import fingerprint as fp
from .command import curl_json
from .inventory import host_ports as inventory_pairs
from .model import Endpoint, Finding, Outcome, RunContext, StepVerdict
from .transport import HttpResponse


def _endpoint(url, port, kind="", resp=None) -> Endpoint:
    return Endpoint(
        url=url, scheme=fp.scheme_for(port), host=fp.normalize_target(url),
        port=port, kind=kind,
        status=getattr(resp, "status", 0),
        content_type=getattr(resp, "content_type", "") or "",
    )


def _curl_sweep(urls) -> str:
    quoted = " ".join('"%s"' % u for u in urls)
    return ("for u in %s; do printf '%%s ' \"$u\"; "
            "curl -s --noproxy '*' -o /dev/null -w "
            "'%%{http_code} %%{content_type}\\n' \"$u\"; done" % quoted)


def _probe_pairs(ctx: RunContext, host: str) -> List[Tuple[str, int]]:
    """目标自身端口 + recon-ai 清单给出的端点（去重保序）。"""
    ports = tuple(ctx.ports) if ctx.ports else fp.ALL_PORTS
    pairs = [(host, port) for port in ports]
    for pair in inventory_pairs(ctx.inventory_endpoints):
        if pair not in pairs:
            pairs.append(pair)
    return pairs


def discover(ctx: RunContext) -> StepVerdict:
    """infra-01：枚举基础设施面并以三元组判定归类（含 recon 清单端点）。"""
    host = fp.normalize_target(ctx.target)
    findings: List[Finding] = []
    lines: List[str] = []
    urls: List[str] = []
    saw_html = saw_network = False

    for host_i, port in _probe_pairs(ctx, host):
        for probe in fp.probes_for_port(port):
            url = fp.endpoint_url(host_i, port, probe.path)
            urls.append(url)
            resp = ctx.transport.request("GET", url, timeout=ctx.timeout)
            shape = fp.shape_of(resp)
            if resp.error:
                saw_network = True
                verdict = "network-error"
            elif fp.is_auth_status(resp):
                verdict = "AUTH_REQUIRED(%d)" % resp.status
                findings.append(Finding(_endpoint(url, port, probe.kind, resp),
                                        Outcome.AUTH_REQUIRED,
                                        reason="http_%d" % resp.status))
            else:
                kind = fp.classify(probe, resp)
                if kind:
                    verdict = "HIT %s" % kind
                    findings.append(Finding(_endpoint(url, port, kind, resp),
                                            Outcome.EXPOSED_NO_AUTH))
                else:
                    verdict = "miss(%s)" % (shape or "unknown")
                    saw_html = saw_html or shape == fp.HTML
            lines.append("%s -> %s %s %s" % (url, resp.status or "-",
                                             resp.content_type or "-", verdict))

    output = "\n".join(lines)
    command = _curl_sweep(sorted(set(urls)))
    exposed = [f for f in findings if f.outcome is Outcome.EXPOSED_NO_AUTH]
    auth = [f for f in findings if f.outcome is Outcome.AUTH_REQUIRED]

    if exposed:
        kinds = sorted({f.endpoint.kind for f in exposed})
        return StepVerdict("infra-01", Outcome.EXPOSED_NO_AUTH, "",
                           summary="发现 %d 个未授权可达端点（%s）"
                                   % (len(exposed), ",".join(kinds)),
                           command=command, output=output, findings=findings)
    if auth:
        kinds = sorted({f.endpoint.kind for f in auth})
        return StepVerdict("infra-01", Outcome.AUTH_REQUIRED,
                           reason="no_credential",
                           summary="基础设施面存在但需凭据（%s）" % ",".join(kinds),
                           command=command, output=output, findings=findings)
    reason = "spa_fallback" if saw_html and not saw_network else "network"
    if not saw_html and not saw_network:
        reason = "none_found"
    return StepVerdict("infra-01", Outcome.ABSENT, reason=reason,
                       summary="未发现可归类的基础设施端点",
                       command=command, output=output, findings=findings)


def cloud_misconfig(ctx: RunContext) -> StepVerdict:
    """infra-02：云存储匿名列举（`--no-sign-request`，canonical F-8）。"""
    if not ctx.buckets:
        return StepVerdict("infra-02", Outcome.ABSENT, reason="none_found",
                           summary="未提供待核云存储桶",
                           output="判定依据：未提供 bucket，未发起匿名列举请求",
                           command="aws s3 ls --no-sign-request")
    argv_all, outs, worst = [], [], None
    for bucket in ctx.buckets:
        argv = ("aws", "s3", "ls", "s3://%s" % bucket, "--no-sign-request",
                "--recursive")
        result = ctx.command.run(argv, timeout=ctx.timeout)
        argv_all.append(" ".join(argv))
        outs.append("$ aws s3 ls s3://%s --no-sign-request --recursive\n"
                    "(exit=%d)\n%s" % (bucket, result.code,
                                       (result.stdout or result.stderr).strip()[:1200]))
        if result.code == 0:
            worst = "EXPOSED"
        elif result.code == 127:
            worst = worst or "NO_TOOL"
        elif "AccessDenied" in (result.stderr or "") or "403" in (result.stderr or ""):
            worst = worst or "DENIED"
        else:
            worst = worst or "NETWORK"
    command = " ; ".join(argv_all)
    output = "\n\n".join(outs)
    if worst == "EXPOSED":
        return StepVerdict("infra-02", Outcome.EXPOSED_NO_AUTH, "",
                           summary="云存储匿名可列举（%d 个桶）" % len(ctx.buckets),
                           command=command, output=output)
    if worst == "DENIED":
        return StepVerdict("infra-02", Outcome.AUTH_REQUIRED, reason="forbidden",
                           summary="桶存在但拒绝匿名访问", command=command,
                           output=output)
    reason = "no_tool" if worst == "NO_TOOL" else "network"
    return StepVerdict("infra-02", Outcome.ABSENT, reason=reason,
                       summary="匿名列举未取得对象清单", command=command,
                       output=output)


def _model_target(ctx: RunContext) -> Tuple[int, "fp.Probe"]:
    """选取第一个有模型清单语义的探测（Ollama 优先，其次 OpenAI 兼容）。"""
    host = fp.normalize_target(ctx.target)
    ports = tuple(ctx.ports) if ctx.ports else (11434, 8000, 4000)
    for port in ports:
        for probe in fp.probes_for_port(port):
            url = fp.endpoint_url(host, port, probe.path)
            resp = ctx.transport.request("GET", url, timeout=ctx.timeout)
            if fp.classify(probe, resp):
                return port, probe
    return 0, fp.PROBES[0]


def _models_from(ctx, port, probe) -> Tuple[List[str], str, HttpResponse]:
    host = fp.normalize_target(ctx.target)
    url = fp.endpoint_url(host, port, probe.path)
    resp = ctx.transport.request("GET", url, timeout=ctx.timeout)
    payload = resp.json() if resp.is_json else None
    names: List[str] = []
    if isinstance(payload, dict):
        for item in payload.get("data") or payload.get("models") or []:
            if isinstance(item, dict):
                name = item.get("id") or item.get("name") or item.get("model")
                if name:
                    names.append(str(name))
    return names, url, resp


def _infer(ctx, port, kind, model) -> Tuple[str, HttpResponse]:
    host = fp.normalize_target(ctx.target)
    if kind == "ollama":
        url = fp.endpoint_url(host, port, "/api/generate")
        body = {"model": model, "prompt": ctx.inference_prompt, "stream": False}
    else:
        url = fp.endpoint_url(host, port, "/v1/completions")
        body = {"model": model, "prompt": ctx.inference_prompt, "max_tokens": 8}
    return curl_json(url, body), ctx.transport.request(
        "POST", url, json_body=body, timeout=max(ctx.timeout, 60))


def _inference_succeeded(kind, resp) -> bool:
    if resp.error or not (200 <= resp.status < 300):
        return False
    payload = resp.json()
    if not isinstance(payload, dict):
        return False
    if kind == "ollama":
        return bool(str(payload.get("response") or "").strip())
    return bool(payload.get("choices"))


def model_server(ctx: RunContext) -> StepVerdict:
    """infra-03：模型服务器未授权列举与单次推理（`--allow-inference`）。"""
    port, probe = _model_target(ctx)
    if not port:
        return StepVerdict(
            "infra-03", Outcome.ABSENT, reason="none_found",
            summary="未发现模型服务器端点（Ollama/OpenAI 兼容）",
            output="判定依据：候选端口 11434/8000/4000 的三元组均未命中",
            command="curl -s --noproxy '*' %s/v1/models"
                    % fp.normalize_target(ctx.target))
    kind = probe.kind
    names, list_url, list_resp = _models_from(ctx, port, probe)
    if fp.is_auth_status(list_resp):
        return StepVerdict("infra-03", Outcome.AUTH_REQUIRED, reason="no_credential",
                           summary="模型服务器存在但需凭据（%s:%d）"
                                   % (fp.normalize_target(ctx.target), port),
                           command="curl -s --noproxy '*' %s" % list_url,
                           output=list_resp.body[:600])
    model = ctx.inference_model or (names[0] if names else "")
    output = ("$ curl -s --noproxy '*' %s\n%s\n\n模型清单（%d）：%s"
              % (list_url, list_resp.body[:800], len(names), ", ".join(names[:5])))
    command = "curl -s --noproxy '*' %s" % list_url

    if ctx.allow_inference and model and kind != "triton":
        hint, resp = _infer(ctx, port, kind, model)
        output += "\n\n$ %s\n%s" % (hint, (resp.body or resp.error)[:600])
        command = command + " ; " + hint
        if _inference_succeeded(kind, resp):
            return StepVerdict("infra-03", Outcome.EXPLOITED, "",
                               summary="未授权列举 + 单次推理成功（%s）" % model,
                               command=command, output=output)
    return StepVerdict("infra-03", Outcome.EXPOSED_NO_AUTH, "",
                       summary="未授权取得模型清单（%d 个）" % len(names),
                       command=command, output=output)

