#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 A2：K8s 身份链（AC-05..08）。

一手事实：`attack-infra-ch9-canonical.md` C-6/C-7/C-8。
raw HTTP 调用经 ctx.transport（唯一 seam），JWT 仅 base64 解码不验签。
"""
import base64
import json
from typing import Any, Dict, Tuple

from .ch9_model import (
    ABSENT, AUTH_REQUIRED, BLOCKED, EXPLOITED, EXPOSED_NO_AUTH,
    Capability, CapabilityMatrix, Ch9Verdict,
)

RULES_PATH = "/apis/authorization.k8s.io/v1/selfsubjectrulesreviews"


def token_surface(ctx: Any) -> Ch9Verdict:
    """k8s-01（AC-05）：判定 SA token 三文件与 API 端点，构造 raw API URL。"""
    token_path = getattr(ctx, "sa_token_path",
                         "/var/run/secrets/kubernetes.io/serviceaccount/token")
    ca_path = getattr(ctx, "sa_ca_path",
                      "/var/run/secrets/kubernetes.io/serviceaccount/ca.crt")
    host = getattr(ctx, "k8s_api_host", "")
    port = getattr(ctx, "k8s_api_port", "")
    if not host or not port:
        return Ch9Verdict("ch9-k8s-01", ABSENT, "none_found",
                          "未提供 KUBERNETES_SERVICE_HOST/PORT",
                          "env | grep KUBERNETES_SERVICE",
                          "判定依据：无 API 地址，无法构造 raw 请求")
    api = "https://%s:%s" % (host, port)
    url = api + RULES_PATH
    output = ("token=%s\nca.crt=%s\nKUBERNETES_SERVICE_HOST=%s\n"
              "KUBERNETES_SERVICE_PORT=%s\n构造 URL=%s"
              % (token_path, ca_path, host, port, url))
    return Ch9Verdict("ch9-k8s-01", EXPOSED_NO_AUTH, "",
                      "构造 API URL 成功（raw HTTP，无需 kubectl）",
                      "curl -s --cacert %s -H \"Authorization: Bearer $TOKEN\" %s"
                      % (ca_path, url), output,
                      {"api_url": url, "token_path": token_path, "ca_path": ca_path})


def _rules_to_caps(rules: Any) -> Tuple[Capability, ...]:
    """把 SelfSubjectRulesReview 的 resourceRules 归一为能力集合。"""
    caps = []
    if not isinstance(rules, (list, tuple)):
        return tuple(caps)
    for rule in rules:
        if isinstance(rule, Capability):
            caps.append(rule)
            continue
        if not isinstance(rule, dict):
            continue
        for resource in rule.get("resources") or []:
            for verb in rule.get("verbs") or []:
                caps.append(Capability(resource=str(resource), verb=str(verb)))
    return tuple(caps)


def same_rules_across_ns(ctx: Any) -> Ch9Verdict:
    """k8s-02（AC-06）：比较两个 namespace 的规则集合，判 ClusterRole。"""
    url = getattr(ctx, "k8s_rules_url", "https://k8s" + RULES_PATH)
    namespaces = getattr(ctx, "k8s_namespaces", ()) or ("ml-inference", "monitoring")
    bodies: list = []
    caps_per_ns: Dict[str, Tuple[Capability, ...]] = {}
    for ns in namespaces:
        body = {"apiVersion": "authorization.k8s.io/v1",
                "kind": "SelfSubjectRulesReview",
                "spec": {"namespace": ns}}
        resp = ctx.transport.request("POST", url, json_body=body, timeout=ctx.timeout)
        if not resp.ok:
            return Ch9Verdict("ch9-k8s-02", AUTH_REQUIRED, "forbidden",
                              "namespace %s 规则查询被拒绝" % ns,
                              "curl -X POST %s -d '{...}'" % url,
                              (resp.body or resp.error)[:500])
        try:
            data = json.loads(resp.body)
        except (ValueError, TypeError):
            data = {}
        rules = ((data.get("status") or {}).get("resourceRules")) or []
        caps_per_ns[ns] = _rules_to_caps(rules)
        bodies.append("$ curl -X POST %s  # ns=%s\n%s"
                      % (url, ns, resp.body[:600]))
    sets = [set((c.resource, c.verb) for c in caps) for caps in caps_per_ns.values()]
    same = len(sets) >= 2 and all(s == sets[0] for s in sets[1:])
    summary = ("规则一致 → ClusterRole（跨 namespace 生效）" if same
               else "规则不同 → namespaced Role")
    return Ch9Verdict("ch9-k8s-02", EXPOSED_NO_AUTH if same else BLOCKED,
                      "" if same else "no_difference", summary,
                      "curl -X POST %s -d '{...}'  # 两 namespace" % url,
                      "\n\n".join(bodies),
                      {"same_rules": same,
                       "namespaces": list(namespaces),
                       "caps_count": {k: len(v) for k, v in caps_per_ns.items()}})


def jwt_subject(token: str) -> str:
    """k8s-03（AC-07）：base64 解 JWT 载荷取 sub（不验签）。"""
    parts = token.split(".")
    if len(parts) < 2:
        return ""
    try:
        payload = parts[1] + "=" * (-len(parts[1]) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload).decode("utf-8", "replace"))
    except Exception:
        return ""
    subject = str(data.get("sub", ""))
    if subject.startswith("system:serviceaccount:"):
        return subject
    ns = data.get("kubernetes.io", {}).get("namespace", "")
    name = data.get("kubernetes.io", {}).get("serviceaccount", {}).get("name", "")
    if ns and name:
        return "system:serviceaccount:%s:%s" % (ns, name)
    return subject


def capability_matrix(ctx: Any) -> Ch9Verdict:
    """k8s-04（AC-08）：双身份能力矩阵判读+写互补。"""
    a_name = getattr(ctx, "identity_a", "inference-sa")
    b_name = getattr(ctx, "identity_b", "argo-workflow-controller")
    a_caps = _rules_to_caps(getattr(ctx, "identity_a_rules", []))
    b_caps = _rules_to_caps(getattr(ctx, "identity_b_rules", []))
    matrix = CapabilityMatrix(a_name, b_name, a_caps, b_caps)
    matrix.evaluate()
    output = ("%s: %d 项能力（读 secrets=%s / 建 pods=%s）\n"
              "%s: %d 项能力（读 secrets=%s / 建 pods=%s）\n"
              "互补可接管=%s；缺口=%s"
              % (a_name, len(a_caps), CapabilityMatrix.can_read(a_caps),
                 CapabilityMatrix.can_write(a_caps),
                 b_name, len(b_caps), CapabilityMatrix.can_read(b_caps),
                 CapabilityMatrix.can_write(b_caps),
                 matrix.completes, matrix.gap or "无"))
    outcome = EXPLOITED if matrix.completes else BLOCKED
    reason = "" if matrix.completes else "no_difference"
    return Ch9Verdict("ch9-k8s-04", outcome, reason,
                      "身份链可接管集群" if matrix.completes else "身份链不足以接管（%s）" % matrix.gap,
                      "# SelfSubjectRulesReview × 2 身份", output,
                      {"completes": matrix.completes, "gap": matrix.gap,
                       "identity_a": a_name, "identity_b": b_name})
