#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 C3 IAM 角色链 / K8s SA 身份链信任建模（加固版）。

事实源 `docs/research/threat-model-c3-hardening-canonical.md` M5-1..M5-7。
保留轻量版公开函数与 dict 访问；新增类型化资产/边界/路径投影，供
attack-infra / foothold-traditional 按 asset_id 引用（P-2）。
不执行 assume-role / token 提取（P-4）。
"""
from typing import Any, Dict, List, Tuple

from . import boundaries as bd
from .ch9_c3_model import (
    IAM, K8S_SA, IdentityChainVerdict, asset_id_for,
)
from .model import AssetView, TrustBoundary

ANCHOR_IAM = "Ch9 Figure 3 / L215-698"
ANCHOR_K8S = "Ch9 Table 2 / L2274-2279"
SCORE_CLASS = "链式入口"


def iam_chain_graph(roles: List[str], boundary_crossed: bool = False) -> Dict[str, Any]:
    """L5-14/图3：角色链 → 节点/边图 + 跨边界标记（保留公开签名）。"""
    nodes = list(roles or [])
    edges = [{"from": nodes[i], "to": nodes[i + 1], "verb": "sts:AssumeRole"}
             for i in range(len(nodes) - 1)]
    ids = tuple(asset_id_for(IAM, r) for r in nodes)
    return {
        "nodes": nodes, "edges": edges,
        "boundary_crossed": bool(boundary_crossed),
        "anchor": ANCHOR_IAM,
        "asset_ids": ids,
        "summary": "IAM 链 %d 节点 / %d 边；跨边界=%s"
                   % (len(nodes), len(edges), bool(boundary_crossed)),
    }


def k8s_identity_chain(a_caps: List[Dict[str, str]],
                       b_caps: List[Dict[str, str]],
                       sa_names: Tuple[str, ...] = ()) -> Dict[str, Any]:
    """L47-52/T2：双 SA 能力互补 → 可达路径与缺口（保留公开签名）。"""
    def has(caps, resource, verbs):
        return any(c.get("resource") == resource and c.get("verb") in verbs
                   for c in caps or [])
    read = has(a_caps, "secrets", ("get", "list", "watch")) or has(
        b_caps, "secrets", ("get", "list", "watch"))
    write = has(a_caps, "pods", ("create", "patch", "delete")) or has(
        b_caps, "pods", ("create", "patch", "delete"))
    reachable = read and write
    gap = "" if reachable else ("no_secret_read" if not read else "no_pod_create")
    path = ["secrets.read", "credentials.exfil", "pods.create"] if reachable else []
    # SA 名优先取显式参数，其次从能力 dict 的 sa/service_account 字段，最后用 A/B 占位。
    names = tuple(sa_names) if sa_names else tuple(
        str(next((c.get("sa") or c.get("service_account") for c in caps if
                  c.get("sa") or c.get("service_account")), dflt))
        for caps, dflt in ((a_caps, "A"), (b_caps, "B")))
    return {
        "reachable": reachable, "gap": gap, "anchor": ANCHOR_K8S,
        "path": path, "kind": K8S_SA, "service_accounts": names,
        "summary": "双身份链可达" if reachable else "双身份链缺口=%s" % gap,
    }


def to_assets(graph: Dict[str, Any], kind: str = IAM) -> List[AssetView]:
    """链图 → 既有 AssetView 资产（每角色/SA 一个，depends_on 前序）。"""
    names = list(graph.get("nodes") or [])
    if kind == K8S_SA:
        names = list(graph.get("service_accounts") or names)
    assets = []
    for i, name in enumerate(names):
        assets.append(AssetView(
            asset_id=asset_id_for(kind, name),
            category="身份链",
            product=str(name),
            score_class=SCORE_CLASS,
            trust_zone="身份域",
            reachable=bool(graph.get("reachable", True)),
            depends_on=[asset_id_for(kind, names[i - 1])] if i else [],
            evidence_step="tm-c3",
        ))
    return assets


def to_boundaries(graph: Dict[str, Any], kind: str = IAM) -> List[TrustBoundary]:
    """AssumeRole 边 / SA 能力互补 → 既有 TrustBoundary 实体。"""
    out: List[TrustBoundary] = []
    if kind == IAM:
        for i, edge in enumerate(graph.get("edges") or [], 1):
            src, dst = edge.get("from", ""), edge.get("to", "")
            out.append(TrustBoundary(
                id="TB-IAM-%d" % i,
                from_component=asset_id_for(IAM, src),
                to_component=asset_id_for(IAM, dst),
                trust_type="role_assumption",
                enforcement="trust_policy" if graph.get("boundary_crossed") else "",
                is_gap=not bool(graph.get("boundary_crossed")),
                offensive_implication="sts:AssumeRole 凭据链（图3）",
            ))
    else:
        if graph.get("reachable"):
            names = list(graph.get("service_accounts") or ("A", "B"))
            out.append(TrustBoundary(
                id="TB-K8S-SA", from_component=asset_id_for(K8S_SA, names[0]),
                to_component=asset_id_for(K8S_SA, names[-1]),
                trust_type="sa_capability_complement",
                enforcement="rbac", validation_status="UNVALIDATED",
                identity_collapse=True, is_gap=False,
                offensive_implication="secrets 读 + pods 写（Table 2）",
            ))
    return out


def asset_ids_for(graph: Dict[str, Any], kind: str = IAM) -> Tuple[str, ...]:
    """下游按 ID 引用的稳定列表（attack-infra/foothold 可消费）。"""
    return tuple(a.asset_id for a in to_assets(graph, kind))


def shortest_for_chain(graph: Dict[str, Any], kind: str = IAM, top_n: int = 3):
    """复用既有 `boundaries.shortest_paths`，不改其签名/语义（P-3）。"""
    assets = to_assets(graph, kind)
    return bd.shortest_paths(assets, top_n=top_n,
                             boundaries=to_boundaries(graph, kind))


def to_verdict(graph: Dict[str, Any], kind: str = IAM) -> IdentityChainVerdict:
    """链图 → 类型化结论（asset_ids 稳定，outcome 取可达/缺口/无）。"""
    if kind == K8S_SA:
        reachable = bool(graph.get("reachable"))
        return IdentityChainVerdict(
            outcome="REACHABLE" if reachable else "GAP",
            reason="" if reachable else graph.get("gap", "none_found"),
            kind=kind, anchor=graph.get("anchor", ANCHOR_K8S),
            summary=graph.get("summary", ""),
            asset_ids=asset_ids_for(graph, kind),
            path=tuple(graph.get("path") or []), gap=graph.get("gap", ""))
    nodes = graph.get("nodes") or []
    if not nodes:
        return IdentityChainVerdict(outcome="ABSENT", reason="empty_chain",
                                    kind=kind, anchor=ANCHOR_IAM,
                                    summary="空角色链")
    return IdentityChainVerdict(
        outcome="REACHABLE", kind=kind, anchor=graph.get("anchor", ANCHOR_IAM),
        summary=graph.get("summary", ""), asset_ids=asset_ids_for(graph, kind),
        extra={"boundary_crossed": bool(graph.get("boundary_crossed"))})
