#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""C3 下游按 asset_id 引用探针（AC-05，M5-6）。

只做 ID 匹配/消费形态断言；不改 attack-infra/foothold 任何判据。
"""
from typing import Any, Dict, Iterable, List

from . import ch9_identity_chain as chain
from .ch9_c3_model import IAM, K8S_SA


def claim_ids(graph: Dict[str, Any], kind: str = IAM) -> List[str]:
    """下游可认领的稳定 ID 列表（按 ID 引用换资产/主机）。"""
    return list(chain.asset_ids_for(graph, kind))


def compatible_with_iam_ctx(graph: Dict[str, Any],
                            ctx_chain: Iterable[str]) -> bool:
    """attack-infra `ctx.iam_chain` 形态兼容：角色名顺序一致即可引用。"""
    nodes = list(graph.get("nodes") or [])
    return nodes == list(ctx_chain or [])
