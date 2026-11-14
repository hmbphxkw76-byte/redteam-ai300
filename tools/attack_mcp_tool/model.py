#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""值对象与常量（叶节点模块，不依赖包内其它模块）。

设计约束（`docs/operations/attack-mcp-tool-design.md` §2）：
  - 仅数据与纯计算，不做 IO；
  - 效果等级取值固定为四值，供 `grade` 与报告共用；
  - 敏感值识别用正则，不引入第三方库。
"""
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Tuple

# 效果等级：四值互斥，语义见规格 v2 AC-08
LEVELS: Tuple[str, ...] = ("完全生效", "部分生效", "未生效", "已跳过")

# 敏感值形态（目标侧凭据均以 sk- 前缀 + 长随机串出现；源自阶段 1 实测 T-3）
SECRET_PATTERN = re.compile(r"sk-[A-Za-z0-9]{16,}")

# 工具面解析：agent 会话文本中的工具声明（容忍加粗/表格/中英文标签）
_IDENT = re.compile(r"[A-Za-z0-9_.\-]{2,}")
_TOOL_NAME_RE = re.compile(r"(?:tool\s*name|工具名(?:称)?|tool)\s*[:：]\s*([A-Za-z0-9_.\-]+)",
                           re.IGNORECASE)
_SCOPE_RE = re.compile(r"(?:required\s*scope|所需权限范围|所需权限|scope)\s*[:：]\s*([^\s,|]+)",
                       re.IGNORECASE)
_SERVER_RE = re.compile(r"(?:server\s*id|服务器\s*id|服务器)\s*[:：]\s*([A-Za-z0-9_.\-]+)",
                        re.IGNORECASE)
_TABLE_SKIP = {"tool", "name", "tool name", "toolname", "---"}
_TRUST_RE = re.compile(r"\b(trusted|untrusted|shadow)\b", re.IGNORECASE)


def _deemph(text):
    """去掉 Markdown 强调符（`*` 与反引号），保留下划线以免破坏工具名。"""
    return re.sub(r"[*`]+", "", text or "")


def parse_tool_entries(text):
    """从散文体/表格回答中抽取工具条目，返回 [{'name','server','scope'}]。

    只抽取显式声明的字段，缺失即留空（不臆造），由调用方判定效果等级。
    """
    entries = []
    pending_server = ""
    for raw in _deemph(text).splitlines():
        line = raw.strip()
        if not line:
            continue
        name = None
        m = _TOOL_NAME_RE.search(line)
        if m:
            name = m.group(1)
        elif line.startswith("|"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            first = cells[0] if cells else ""
            if first and _IDENT.fullmatch(first) and first.lower() not in _TABLE_SKIP:
                name = first
        if name:
            entries.append({"name": name})
        if not entries:
            # 服务器声明可能出现在工具清单之前（父子结构），先暂存供后续条目继承
            mv0 = _SERVER_RE.search(line)
            if mv0:
                pending_server = mv0.group(1)
            continue
        cur = entries[-1]
        ms = _SCOPE_RE.search(line)
        if ms and "scope" not in cur:
            cur["scope"] = ms.group(1).strip()
        mv = _SERVER_RE.search(line)
        if mv and "server" not in cur:
            cur["server"] = mv.group(1)
        elif "server" not in cur and pending_server:
            cur["server"] = pending_server
        mt = _TRUST_RE.search(line)
        if mt and "trust" not in cur:
            cur["trust"] = mt.group(1).lower()
    return entries


def find_secrets(text):
    """返回文本中出现的敏感值（去重、保持出现顺序）。"""
    seen, out = set(), []
    for m in SECRET_PATTERN.finditer(text or ""):
        value = m.group(0)
        if value not in seen:
            seen.add(value)
            out.append(value)
    return out


def redact(text, keep=6):
    """脱敏：保留前缀与末位，其余替换为固定标记，避免明文散落多份证据。"""
    if not text:
        return text
    if len(text) <= keep + 4:
        return text[:2] + "<REDACTED>"
    return text[:keep] + "<REDACTED>" + text[-2:]


@dataclass(frozen=True)
class ToolDescriptor:
    """工具面中的一条工具（对应 MCP `tools/list` 的单个 tool 对象）。"""

    name: str
    server_id: str = ""
    description: str = ""
    scope: str = ""
    trust: str = ""

    def as_dict(self):
        return {"name": self.name, "server_id": self.server_id,
                "description": self.description, "scope": self.scope,
                "trust": self.trust}


@dataclass(frozen=True)
class ToolSurface:
    """一次枚举得到的工具面。"""

    tools: Tuple[ToolDescriptor, ...] = ()
    source: str = ""

    def names(self):
        return tuple(t.name for t in self.tools)

    def by_name(self, name):
        for t in self.tools:
            if t.name == name:
                return t
        return None

    def as_dict(self):
        return {"source": self.source, "tools": [t.as_dict() for t in self.tools]}


@dataclass(frozen=True)
class SurfaceChange:
    """投毒前后单个工具的差异。"""

    name: str
    kind: str          # added / removed / changed
    fields: Tuple[str, ...] = ()

    def as_dict(self):
        return {"name": self.name, "kind": self.kind, "fields": list(self.fields)}


@dataclass(frozen=True)
class Signals:
    """一步攻击的确定性信号集合（定级唯一输入）。

    字段含义与判据见规格 v2 AC-08/AC-10/AC-11/AC-19：
      - `capability_missing`：目标不具备该能力（含被护栏拒绝且无替代路径）
      - `deterministic`：目标侧确定性信号是否命中（策略放行/利用成功/枚举到工具）
      - `judge`：自有判据是否命中（敏感值回显/面板校验通过/差分非空）
    """

    step_id: str
    deterministic: bool = False
    judge: bool = False
    capability_missing: bool = False
    consent_required: bool = False
    capped_partial: bool = False   # 仅本地自证、目标侧未生效 → 最高只能判「部分生效」
    detail: str = ""

    def as_dict(self):
        return {"step_id": self.step_id, "deterministic": self.deterministic,
                "judge": self.judge, "capability_missing": self.capability_missing,
                "consent_required": self.consent_required,
                "capped_partial": self.capped_partial, "detail": self.detail}


@dataclass(frozen=True)
class Observation:
    """一次工具交互的可观察结果（原始响应 + 解析后的工具结果与遥测）。"""

    raw: str = ""
    text: str = ""
    tool_result: str = ""
    telemetry: Dict[str, Any] = field(default_factory=dict)
    request: Dict[str, Any] = field(default_factory=dict)
    error: str = ""

    @property
    def secrets(self):
        return find_secrets(self.tool_result or self.text or self.raw)

    def as_dict(self):
        return {"text": self.text, "tool_result": self.tool_result,
                "telemetry": dict(self.telemetry), "error": self.error,
                "secrets": [redact(s) for s in self.secrets]}


@dataclass(frozen=True)
class StepVerdict:
    """一个步骤的对外结论（报告单元）。"""

    step_id: str
    path: str
    title: str
    level: str
    reason: str
    command: str
    observation: Observation
    evidence_path: str = ""

    def as_dict(self):
        return {"step_id": self.step_id, "path": self.path, "title": self.title,
                "level": self.level, "reason": self.reason,
                "command": self.command,
                "observation": self.observation.as_dict(),
                "evidence_path": self.evidence_path}


@dataclass(frozen=True)
class AttackRequest:
    """公开入口输入。"""

    target: str
    mode: str = "agent-sse"          # agent-sse | jsonrpc
    labs: Tuple[str, ...] = ("MCP_01",)
    paths: Tuple[str, ...] = ("A", "B", "C")
    step: str = ""
    evidence_dir: str = ""
    emit: bool = True


@dataclass(frozen=True)
class AttackReport:
    """公开入口输出。"""

    request: AttackRequest
    backend: str
    verdicts: Tuple[StepVerdict, ...] = ()
    object_graph: Dict[str, Any] = field(default_factory=dict)

    def levels(self):
        return tuple(v.level for v in self.verdicts)

    def evidence_paths(self):
        return tuple(v.evidence_path for v in self.verdicts)

    def as_dict(self):
        return {"target": self.request.target, "mode": self.request.mode,
                "backend": self.backend,
                "object_graph": dict(self.object_graph),
                "verdicts": [v.as_dict() for v in self.verdicts]}

    def by_step(self, step_id):
        for v in self.verdicts:
            if v.step_id == step_id:
                return v
        return None


def parse_surface_from_text(text, server_id="", trust=""):
    """从 agent 会话文本中抽取工具面（散文体回答，非协议响应）。

    只取可识别的工具声明，不臆造缺失字段；解析不到即返回空工具面，
    由调用方判定「已跳过」而非猜测。
    """
    entries = parse_tool_entries(text)
    tools = [ToolDescriptor(name=e["name"], server_id=e.get("server", server_id),
                            scope=e.get("scope", ""),
                            trust=e.get("trust", trust)) for e in entries]
    return ToolSurface(tools=tuple(tools), source="agent-text")


def parse_scope_map(text):
    """解析「工具名 → 所需权限」映射，用于判定越权（存在 admin/write 即高权限面）。"""
    return {e["name"]: e["scope"] for e in parse_tool_entries(text) if e.get("scope")}


def has_admin_scope(telemetry, scope_map=None, tool_name=""):
    """是否触及管理员/写权限（越权判据之一）。"""
    perms = [str(p).lower() for p in (telemetry or {}).get("permissions_used", []) or []]
    if any(p in ("admin", "write", "root", "superuser") or p.startswith("write:") for p in perms):
        return True
    scope = str((scope_map or {}).get(tool_name, "")).lower()
    return scope in ("admin", "write") or scope.startswith("write:")
