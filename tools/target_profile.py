#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""目标画像（TargetProfile）：把目标相关字面量从代码常量/默认值中解耦的唯一事实源。

设计约束（AGENTS.md C1 / ADR-0005）：
  - 生产代码不再写死具体 IP、实验室 ID、端点路径；默认值一律为显式占位符。
  - 具体目标由「画像」注入：内置 generic（全占位）+ 外部 JSON 画像文件；
    新增同类目标只需增加一份 JSON 画像，核心代码零改动（动态扩展不受绑定目标限制）。
  - 注入通道优先级：显式 profile 参数 > CLI 参数 > 环境变量 > generic。
  - 环境变量：REDTEAM_TARGET_PROFILE（画像名）、REDTEAM_TARGET_PROFILES（画像 JSON 文件或目录）。

边界：画像只描述「目标形态」（主机、实验室角色到 ID 的映射、端点模板），
不含任何攻击载荷、凭据或证据内容；不属于考试格式契约（命名/flag 语法/scored hosts）。
"""
import json
import os
from dataclasses import dataclass, field
from typing import Dict, Mapping, Optional, Tuple

PLACEHOLDER_HOST = "<TARGET>"
PLACEHOLDER_LAB = "<LAB_ID>"
PLACEHOLDER_MODEL = "<MODEL>"

ENV_PROFILE = "REDTEAM_TARGET_PROFILE"
ENV_REGISTRY = "REDTEAM_TARGET_PROFILES"

# 实验室角色：调用方按语义取名，画像把角色映射到任意具体 ID。
LAB_ROLES: Tuple[str, ...] = (
    "chat", "vector", "agent", "mcp", "secret", "mcp_poison",
    "mcp_write", "mcp_inject", "mcp_admin", "mcp_escape", "mcp_chain", "mcp_logs",
)

# 通用端点模板。{lab} 由 build_url / endpoint() 按角色替换；不含具体目标字面量。
GENERIC_ENDPOINTS: Dict[str, str] = {
    "config": "/api/config",
    "models": "/v1/models",
    "runs": "/api/me/runs?limit=1",
    "explore": "/explore",
    "bundle": "/assets/index.js",
    "chat": "/api/labs/{lab}/chat",
    "agent_chat": "/api/agents/{agent}/chat",
    "summary": "/api/labs/{lab}/summary",
    "secret_validate": "/api/secrets/validate",
    "agent_card": "/.well-known/agent.json",
    "agent_card_v2": "/.well-known/agent-card.json",
    "tools_list": "/tools/list",
}


@dataclass(frozen=True)
class TargetProfile:
    """一个目标形态画像。所有默认值均为占位符，绝不携带具体目标字面量。"""

    name: str = "generic"
    host: str = PLACEHOLDER_HOST
    model: str = PLACEHOLDER_MODEL
    labs: Mapping[str, str] = field(default_factory=dict)
    endpoints: Mapping[str, str] = field(default_factory=lambda: dict(GENERIC_ENDPOINTS))
    headers: Mapping[str, str] = field(default_factory=dict)
    extra: Mapping[str, object] = field(default_factory=dict)
    description: str = ""

    def lab(self, role: str = "chat", override: str = "") -> str:
        """按角色取实验室 ID；调用方显式值优先，画像映射次之，最后为占位符。"""
        value = override or self.labs.get(role, "") or self.labs.get("default", "")
        return value or PLACEHOLDER_LAB

    def map_lab(self, label: str) -> str:
        """把步骤内的符号 lab 标签映射为当前目标的 lab ID；未登记则原样返回。

        既有步骤以符号名（如 MCP_01 / DE_01）作默认标签，本方法令同一份步骤
        无需改动即可被任意目标画像重映射；generic 画像无映射时保持向后兼容。
        """
        return str(self.labs.get(label, label)) if label else label

    def extra_list(self, key: str) -> Tuple[str, ...]:
        """取画像中的可选字符串列表（如 smb_hosts）；未登记返回空元组。"""
        value = self.extra.get(key, ())
        return tuple(str(item) for item in value) if isinstance(value, (list, tuple)) else ()

    def endpoint(self, key: str, **subs: str) -> str:
        """取端点模板并替换 {name} 占位符；未知键返回空串（调用方记 ABSENT）。"""
        template = self.endpoints.get(key, "")
        for name, value in subs.items():
            template = template.replace("{%s}" % name, str(value))
        return template

    def merged_headers(self, overrides: Optional[Mapping[str, str]] = None) -> dict:
        """画像请求头与调用方显式头合并；同名时调用方覆盖（目标值不落代码）。"""
        merged = {str(k): str(v) for k, v in self.headers.items()}
        merged.update({str(k): str(v) for k, v in (overrides or {}).items()})
        return merged

    def to_dict(self) -> dict:
        return {
            "name": self.name, "host": self.host, "model": self.model,
            "labs": dict(self.labs), "endpoints": dict(self.endpoints),
            "headers": dict(self.headers),
            "extra": dict(self.extra), "description": self.description,
        }


GENERIC = TargetProfile()


def from_mapping(data: Mapping[str, object]) -> TargetProfile:
    """从字典构造画像（测试注入 / JSON 反序列化的唯一入口）。"""
    if not isinstance(data, Mapping):
        raise ValueError("目标画像必须是映射（dict）")
    endpoints = dict(GENERIC_ENDPOINTS)
    supplied = data.get("endpoints") or {}
    if not isinstance(supplied, Mapping):
        raise ValueError("目标画像 endpoints 必须是映射")
    endpoints.update(supplied)
    raw_headers = data.get("headers") or {}
    if not isinstance(raw_headers, Mapping):
        raise ValueError("目标画像 headers 必须是映射")
    return TargetProfile(
        name=str(data.get("name") or "custom"),
        host=str(data.get("host") or PLACEHOLDER_HOST),
        model=str(data.get("model") or PLACEHOLDER_MODEL),
        labs=dict(data.get("labs") or {}),
        endpoints=endpoints,
        headers={str(k): str(v) for k, v in raw_headers.items()},
        extra=dict(data.get("extra") or {}),
        description=str(data.get("description") or ""),
    )


def registry(path: Optional[str] = None) -> Dict[str, TargetProfile]:
    """加载画像注册表：内置 generic + 外部 JSON 文件/目录（零代码改动扩展）。"""
    result: Dict[str, TargetProfile] = {"generic": GENERIC}
    source = path or os.environ.get(ENV_REGISTRY, "")
    if not source:
        return result
    files = []
    if os.path.isdir(source):
        files = [os.path.join(source, f) for f in sorted(os.listdir(source))
                 if f.endswith(".json")]
    elif os.path.isfile(source):
        files = [source]
    else:
        raise ValueError("目标画像来源不存在：%s" % source)
    for file_path in files:
        with open(file_path, encoding="utf-8") as handle:
            payload = json.load(handle)
        entries = payload.get("profiles", []) if isinstance(payload, dict) else payload
        if not isinstance(entries, list):
            raise ValueError("目标画像文件须为画像数组或含 profiles 数组：%s" % file_path)
        for entry in entries:
            profile = from_mapping(entry)
            result[profile.name] = profile
    return result


def resolve(name: Optional[str] = None, path: Optional[str] = None) -> TargetProfile:
    """按名称解析画像，或直接给画像 JSON 文件/目录路径（路径内须恰一份画像）。

    未指定时读环境变量，仍缺则返回 generic。
    """
    chosen = name or os.environ.get(ENV_PROFILE, "") or "generic"
    if os.path.isdir(chosen) or os.path.isfile(chosen):
        loaded = {k: v for k, v in registry(chosen).items() if k != "generic"}
        if len(loaded) == 1:
            return next(iter(loaded.values()))
        raise ValueError("路径画像须恰含 1 份（当前 %d 份），请改用画像名 + %s" % (
            len(loaded), ENV_REGISTRY))
    profiles = registry(path)
    if chosen not in profiles:
        raise ValueError("未知目标画像 %r；可用：%s" % (
            chosen, ", ".join(sorted(profiles))))
    return profiles[chosen]


def current() -> TargetProfile:
    return resolve()


def role_labs(profile: TargetProfile, chat_override: str = "") -> Dict[str, str]:
    """展开全部实验室角色到具体/占位 ID，供 build_url 逐角色替换。

    ``chat_override`` 仅覆盖 chat 角色（历史 ``lab`` 参数的语义），其余角色
    仍由画像各自映射，避免一个显式聊天 ID 把向量/agent/MCP 角色一并覆盖。
    """
    labs = {role: profile.lab(role) for role in LAB_ROLES}
    if chat_override:
        labs["chat"] = chat_override
    return labs
