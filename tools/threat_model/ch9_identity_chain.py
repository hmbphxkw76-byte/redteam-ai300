#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 C3：IAM 角色链 / K8s 身份链信任建模（纯分析，AC-01..06）。

事实源 `docs/research/threat-model-ch9-canonical.md` M-1..M-4。
不执行 assume-role/token 提取；只把上游观测归一为图与可达性结论。
"""
from typing import Any, Dict, List

ANCHOR_IAM = "Ch9 Figure 3 / L215-698"
ANCHOR_K8S = "Ch9 Table 2 / L2274-2279"


def iam_chain_graph(roles: List[str], boundary_crossed: bool = False) -> Dict[str, Any]:
    """AC-01/02：角色链 → 节点/边图 + 跨边界标记。"""
    nodes = list(roles)
    edges = [{"from": roles[i], "to": roles[i + 1], "verb": "sts:AssumeRole"}
             for i in range(len(roles) - 1)]
    return {"nodes": nodes, "edges": edges, "boundary_crossed": bool(boundary_crossed),
            "anchor": ANCHOR_IAM,
            "summary": "IAM 链 %d 节点 / %d 边；跨边界=%s"
                       % (len(nodes), len(edges), bool(boundary_crossed))}


def k8s_identity_chain(a_caps: List[Dict[str, str]],
                       b_caps: List[Dict[str, str]]) -> Dict[str, Any]:
    """AC-03/04：双身份能力互补 → 可达路径与缺口。"""
    def has(caps, resource, verbs):
        return any(c.get("resource") == resource and c.get("verb") in verbs for c in caps)
    read = has(a_caps, "secrets", ("get", "list", "watch")) or has(b_caps, "secrets", ("get", "list", "watch"))
    write = has(a_caps, "pods", ("create", "patch", "delete")) or has(b_caps, "pods", ("create", "patch", "delete"))
    reachable = read and write
    gap = "" if reachable else ("no_secret_read" if not read else "no_pod_create")
    return {"reachable": reachable, "gap": gap, "anchor": ANCHOR_K8S,
            "path": ["secrets.read", "credentials.exfil", "pods.create"] if reachable else [],
            "summary": "双身份链可达" if reachable else "双身份链缺口=%s" % gap}
