#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SKILL.md「示意脚本，须记录来源」的唯一事实源。

infra-02..infra-06 五步在 `SKILL.md` 中标注「示意脚本，须记录来源」。本模块
把每步所用命令的**官方一手源**与**适配说明**集中为一处（C1），由编排层注入
`collect_evidence.py --script-src / --script-note`，使 5 份证据片段都带可追溯
的脚本来源，且不在多处转抄 URL。

来源均已在 `docs/research/attack-infra-canonical.md` 核实（F-1..F-8）。
"""
from typing import Dict, Optional, Tuple

# step_id -> (官方来源 URL, 适配说明)
SCRIPT_SOURCES: Dict[str, Tuple[str, str]] = {
    "infra-02": (
        "https://docs.aws.amazon.com/cli/latest/reference/s3/ls.html",
        "命令取自 AWS CLI s3 ls 官方参考（--no-sign-request 匿名列举）；"
        "本实现只做只读列举，未改动官方脚本，未引入自定义脚本",
    ),
    "infra-03": (
        "https://docs.vllm.ai/en/latest/serving/openai_compatible_server.html",
        "命令取自 vLLM OpenAI 兼容服务官方文档的 /v1/models 与 /v1/completions；"
        "适配为 --noproxy 直连、单次推理、--allow-inference 显式开关",
    ),
    "infra-04": (
        "https://kubernetes.io/docs/reference/kubectl/generated/kubectl_auth/kubectl_auth_can-i/",
        "命令取自 kubectl auth can-i 官方参考（--list 与 --as=serviceaccount）；"
        "只做授权面列举，不执行创建/删除等写动作",
    ),
    "infra-05": (
        "https://docs.litellm.ai/docs/proxy/quick_start",
        "凭据检索模式取自 LiteLLM 官方 quick_start 的 config.yaml api_key 结构；"
        "实现只产出指纹，合法身份调用需显式开关且仅引用环境变量名",
    ),
    "infra-06": (
        "https://kubernetes.io/docs/reference/access-authn-authz/kubelet-authn-authz/",
        "代码执行命令取自 kubelet nodes/proxy 官方说明与 SKILL.md 的 /exec 模板；"
        "增加回显归属校验，避免把本机回显判为目标侧执行",
    ),
}


def provenance(step_id: str) -> Optional[Dict[str, str]]:
    """返回该步骤应注入证据容器的来源字段；非示意脚本步骤返回 None。"""
    entry = SCRIPT_SOURCES.get(step_id)
    if not entry:
        return None
    url, note = entry
    return {"script_src": url, "script_note": note}
