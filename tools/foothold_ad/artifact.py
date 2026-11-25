#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""离线工件解析（AD 工件契约的唯一事实源）。

本模块只读文件，不联网、不调用 AD 工具；AD 工具（BloodHound / Certipy /
Impacket）仅作为**工件生产者**。字段缺失一律保留 `None`，由判据层记
`UNDETERMINED`，不按默认值推断（见 `skills/foothold-ad/SKILL.md` 失败与豁免）。

工件 schema（目录 `artifacts/` 下三个文件）：

`directory.json`
    {"domain": str,
     "users":  [{"name","domain","enabled","spn":[...],"preauth_required",
                 "delegation","member_of":[...]}],
     "groups": {name: [member,...]} 或 [{"name","members":[...]}],
     "aces":   [{"principal","right","target"}]}
    另兼容 BloodHound 导出：顶层 `data` 列表，条目含 `Properties` / `Aces`。

`templates.json`
    {"schema_version": "1.1",
     "templates": [{"name","enrollee_supplies_subject","ekus":[...],
                    "enrollment_rights":[...],"requires_manager_approval",
                    "http_enrollment","authorized_signatures_required","epa_enabled"}]}

`trusts.json`
    {"schema_version": "1.1",
     "trusts": [{"source","target","direction","sid_filtering"}]}
    direction ∈ {inbound, outbound, bidirectional}；sid_filtering 为 bool 或 None。

`schema_version` 缺省按 1.x 兼容；主版本不符抛 `UnsupportedSchema`（下游记 `UNDETERMINED`）。
"""
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

DIRECTORY_FILE = "directory.json"
TEMPLATES_FILE = "templates.json"
TRUSTS_FILE = "trusts.json"

# 支持的工件 schema 版本；不在此表内的版本一律 `UNDETERMINED`（不按旧版强解）。
SCHEMA_VERSION = "1.1"
MAX_ARTIFACT_BYTES = 32 * 1024 * 1024


class ArtifactError(ValueError):
    """工件缺失或结构不可解析。"""


class UnsupportedSchema(ArtifactError):
    """schema 版本不受支持；调用方须记 `UNDETERMINED` 而非按旧格式解析。"""


def check_schema(payload: Any, filename: str) -> None:
    """校验 `schema_version`；缺省视为 1.0 兼容，未知主版本抛 `UnsupportedSchema`。"""
    if not isinstance(payload, Mapping):
        return
    raw = payload.get("schema_version")
    if raw is None:
        return
    text = str(raw).strip()
    major = text.split(".", 1)[0]
    supported_major = SCHEMA_VERSION.split(".", 1)[0]
    if major != supported_major:
        raise UnsupportedSchema(
            "%s: 不支持的 schema_version=%s（支持 %s.x）" % (filename, text, supported_major))


@dataclass(frozen=True)
class DirectoryUser:
    name: str
    domain: str = ""
    enabled: Optional[bool] = None
    spn: Tuple[str, ...] = ()
    preauth_required: Optional[bool] = None
    delegation: str = "none"
    member_of: Tuple[str, ...] = ()

    @property
    def qualified(self) -> str:
        return "%s@%s" % (self.name, self.domain) if self.domain else self.name


@dataclass(frozen=True)
class Ace:
    principal: str
    right: str
    target: str = ""


@dataclass(frozen=True)
class Directory:
    domain: str = ""
    users: Tuple[DirectoryUser, ...] = ()
    groups: Mapping[str, Tuple[str, ...]] = field(default_factory=dict)
    aces: Tuple[Ace, ...] = ()
    computers: Tuple[str, ...] = ()

    def user(self, name: str) -> Optional[DirectoryUser]:
        for item in self.users:
            if item.name.lower() == name.lower():
                return item
        return None


@dataclass(frozen=True)
class Template:
    name: str
    enrollee_supplies_subject: Optional[bool] = None
    ekus: Tuple[str, ...] = ()
    enrollment_rights: Tuple[str, ...] = ()
    requires_manager_approval: Optional[bool] = None
    http_enrollment: Optional[bool] = None
    # 以下两项对齐 ESC1/ESC8 官方判据：签发要求与 HTTP 端点 EPA/NTLM 面。
    authorized_signatures_required: Optional[bool] = None
    epa_enabled: Optional[bool] = None


@dataclass(frozen=True)
class Trust:
    source: str
    target: str
    direction: str = ""
    sid_filtering: Optional[bool] = None


def load_json(path: str, max_bytes: int = MAX_ARTIFACT_BYTES) -> Any:
    """读取 JSON；缺失、超限、语法错误或嵌套过深一律抛 `ArtifactError`。"""
    try:
        size = os.path.getsize(path)
    except OSError as exc:
        raise ArtifactError("工件不存在: %s (%s)" % (path, exc))
    if size > max_bytes:
        raise ArtifactError("工件超过上限 %d 字节: %s (%d 字节)" % (max_bytes, path, size))
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        raise ArtifactError("工件不存在: %s" % path)
    except UnicodeDecodeError as exc:
        raise ArtifactError("工件不是 UTF-8 文本: %s (%s)" % (path, exc))
    except RecursionError as exc:
        raise ArtifactError("工件嵌套过深: %s (%s)" % (path, exc))
    except json.JSONDecodeError as exc:
        raise ArtifactError("工件不是合法 JSON: %s (%s)" % (path, exc))


def _as_list(value: Any) -> Tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(value)
    return (value,)


def _as_text_tuple(value: Any) -> Tuple[str, ...]:
    return tuple(str(v) for v in _as_list(value) if v not in (None, ""))


def _as_bool(value: Any) -> Optional[bool]:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        low = value.strip().lower()
        if low in ("true", "yes", "1"):
            return True
        if low in ("false", "no", "0"):
            return False
    return None


def _pick(item: Mapping[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in item and item[name] is not None:
            return item[name]
    return default


def _merge_properties(item: Mapping[str, Any]) -> Dict[str, Any]:
    """BloodHound 条目：属性在 `Properties`，ACE 在同级 `Aces`。"""
    if not isinstance(item, Mapping):
        raise ArtifactError("目录条目不是对象: %r" % (item,))
    merged = dict(item)
    props = item.get("Properties")
    if isinstance(props, Mapping):
        for key, value in props.items():
            merged.setdefault(key, value)
    return merged


def parse_directory(payload: Any) -> Directory:
    """解析目录导出；结构不可识别时抛 `ArtifactError`。"""
    if isinstance(payload, list):
        payload = {"users": payload}
    if not isinstance(payload, Mapping):
        raise ArtifactError("directory.json 顶层须为对象或数组")

    raw_users: Iterable[Any] = payload.get("users") or payload.get("data") or ()
    users: List[DirectoryUser] = []
    for raw in raw_users:
        item = _merge_properties(raw)
        name = _pick(item, "name", "Name")
        if not name:
            continue
        users.append(DirectoryUser(
            name=str(name),
            domain=str(_pick(item, "domain", "Domain", default="") or ""),
            enabled=_as_bool(_pick(item, "enabled", "Enabled")),
            spn=_as_text_tuple(_pick(item, "spn", "SPN", "serviceprincipalnames")),
            preauth_required=_as_bool(_pick(item, "preauth_required", "PreAuthRequired")),
            delegation=str(_pick(item, "delegation", "Delegation", default="none") or "none").lower(),
            member_of=_as_text_tuple(_pick(item, "member_of", "MemberOf")),
        ))

    groups: Dict[str, Tuple[str, ...]] = {}
    raw_groups = payload.get("groups") or ()
    if isinstance(raw_groups, Mapping):
        for key, value in raw_groups.items():
            groups[str(key)] = _as_text_tuple(value)
    else:
        for raw in raw_groups:
            item = _merge_properties(raw)
            name = _pick(item, "name", "Name")
            if name:
                groups[str(name)] = _as_text_tuple(_pick(item, "members", "Members"))

    aces: List[Ace] = []
    raw_aces = payload.get("aces") or ()
    for raw in raw_aces:
        item = _merge_properties(raw)
        principal = _pick(item, "principal", "Principal", "PrincipalName")
        rights = _as_text_tuple(_pick(item, "right", "rights", "Right"))
        if not principal:
            continue
        target = str(_pick(item, "target", "Target", default="") or "")
        for right in rights:
            aces.append(Ace(principal=str(principal), right=right, target=target))
    computers = _as_text_tuple(payload.get("computers"))

    nested_aces: List[Ace] = []
    for raw in raw_users:
        item = _merge_properties(raw)
        target = _pick(item, "name", "Name")
        for ace_raw in _as_list(item.get("Aces")):
            ace_item = _merge_properties(ace_raw) if isinstance(ace_raw, Mapping) else {}
            principal = _pick(ace_item, "principal", "Principal", "PrincipalName")
            right = _pick(ace_item, "right", "Right", "RightName")
            if principal and right:
                nested_aces.append(Ace(principal=str(principal), right=str(right),
                                       target=str(target or "")))

    return Directory(
        domain=str(payload.get("domain", "") or ""),
        users=tuple(users),
        groups=groups,
        aces=tuple(aces + nested_aces),
        computers=computers,
    )


def parse_templates(payload: Any) -> Tuple[Template, ...]:
    """解析证书模板导出。"""
    if isinstance(payload, Mapping):
        payload = payload.get("templates", ())
    if not isinstance(payload, (list, tuple)):
        raise ArtifactError("templates.json 须为数组或含 templates 的对象")
    out: List[Template] = []
    for raw in payload:
        item = _merge_properties(raw)
        name = _pick(item, "name", "Name")
        if not name:
            continue
        out.append(Template(
            name=str(name),
            enrollee_supplies_subject=_as_bool(_pick(item, "enrollee_supplies_subject", "EnrolleeSuppliesSubject")),
            ekus=_as_text_tuple(_pick(item, "ekus", "Ekus", "ExtendedKeyUsage")),
            enrollment_rights=_as_text_tuple(_pick(item, "enrollment_rights", "EnrollmentRights")),
            requires_manager_approval=_as_bool(_pick(item, "requires_manager_approval", "RequiresManagerApproval")),
            http_enrollment=_as_bool(_pick(item, "http_enrollment", "HttpEnrollment")),
            authorized_signatures_required=_as_bool(
                _pick(item, "authorized_signatures_required", "AuthorizedSignaturesRequired")),
            epa_enabled=_as_bool(_pick(item, "epa_enabled", "EpaEnabled")),
        ))
    return tuple(out)


def parse_trusts(payload: Any) -> Tuple[Trust, ...]:
    """解析信任列表。"""
    if isinstance(payload, Mapping):
        payload = payload.get("trusts", ())
    if not isinstance(payload, (list, tuple)):
        raise ArtifactError("trusts.json 须为数组或含 trusts 的对象")
    out: List[Trust] = []
    for raw in payload:
        item = _merge_properties(raw)
        source = _pick(item, "source", "Source")
        target = _pick(item, "target", "Target")
        if not source or not target:
            continue
        out.append(Trust(
            source=str(source),
            target=str(target),
            direction=str(_pick(item, "direction", "Direction", default="") or "").lower(),
            sid_filtering=_as_bool(_pick(item, "sid_filtering", "SidFiltering")),
        ))
    return tuple(out)


def fingerprint_hash(value: str, algorithm: str = "NTLM") -> str:
    """凭据指纹：算法 + 前 8 位 + 长度；完整值绝不进入返回值（P-1）。"""
    cleaned = (value or "").strip()
    if not cleaned:
        raise ArtifactError("哈希为空，无法生成指纹")
    return "%s:%s(len=%d)" % (algorithm.upper(), cleaned[:8].lower(), len(cleaned))
