#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AD 判据纯函数（无 IO、无网络、结果确定）。

每个函数只回答一个布尔问题，并返回 `Finding` 供 runner 组装步骤结论；
字段缺失不推断，交由 `notes` 记录 `UNDETERMINED` 依据。
"""
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from .artifact import Ace, Directory, DirectoryUser, Template, Trust
from .model import (
    ABSENT, AUTH_REQUIRED, BLOCKED, EXPOSED_NO_AUTH, EXPLOITED, UNDETERMINED,
    Finding, StepResult,
)

# krbtgt 天然持有复制权限且不可登录，不计入可攻击账户（课程 §S5 语义）。
EXCLUDED_ACCOUNTS = frozenset(("krbtgt",))

CLIENT_AUTH_EKUS = (
    "client authentication",
    "1.3.6.1.5.5.7.3.2",
    "smart card logon",
    "1.3.6.1.5.5.7.3.4",
)

LOW_PRIV_ENROLL = ("domain users", "authenticated users", "everyone", "users")

PRIVILEGED_GROUP_RE = re.compile(r"domain admins|enterprise admins|administrators|域管理员", re.I)

TRUST_DIRECTIONS = frozenset(("inbound", "outbound", "bidirectional"))

DELEGATION_VALUES = frozenset((
    "none", "", "unconstrained", "constrained", "constrained-with-protocol-transition",
    "resource-based", "rbcd",
))

REPL_ALL = "replication-get-changes-all"
REPL_PARTIAL = "replication-get-changes"


def _norm(text: str) -> str:
    return (text or "").strip().lower()


def _is_priv_group(name: str) -> bool:
    return bool(PRIVILEGED_GROUP_RE.search(name or ""))


def kerberoastable(directory: Directory) -> Tuple[Tuple[Finding, ...], Tuple[str, ...]]:
    """有 SPN 且启用的账户；启用状态未知者单列，不并入命中。"""
    hits: List[Finding] = []
    unknown: List[str] = []
    for user in directory.users:
        if _norm(user.name) in EXCLUDED_ACCOUNTS or not user.spn:
            continue
        if user.enabled is True:
            hits.append(Finding("kerberoast", user.qualified, "spn=%d" % len(user.spn)))
        elif user.enabled is None:
            unknown.append("%s（启用状态缺失）" % user.qualified)
    return tuple(hits), tuple(unknown)


def asrep_roastable(directory: Directory) -> Tuple[Tuple[Finding, ...], Tuple[str, ...]]:
    """关闭预认证的账户；`preauth_required` 缺失不推断为关闭。"""
    hits: List[Finding] = []
    unknown: List[str] = []
    for user in directory.users:
        if _norm(user.name) in EXCLUDED_ACCOUNTS:
            continue
        if user.preauth_required is False:
            hits.append(Finding("asrep", user.qualified, "preauth=disabled"))
        elif user.preauth_required is None:
            unknown.append("%s（preauth 字段缺失）" % user.qualified)
    return tuple(hits), tuple(unknown)


def unconstrained(directory: Directory) -> Tuple[Finding, ...]:
    hits: List[Finding] = []
    for user in directory.users:
        if _norm(user.delegation) == "unconstrained":
            hits.append(Finding("unconstrained-delegation", user.qualified, "delegation=unconstrained"))
    for computer in directory.computers:
        hits.append(Finding("unconstrained-delegation-candidate", computer, "计算机委派需单独核实"))
    return tuple(hits)


def _eku_is_client_auth(ekus: Sequence[str]) -> bool:
    for eku in ekus:
        low = _norm(eku)
        if any(marker in low for marker in CLIENT_AUTH_EKUS):
            return True
    return False


def _has_low_priv_enroll(rights: Sequence[str]) -> bool:
    for right in rights:
        low = _norm(right)
        if any(low == item or low.startswith(item) for item in LOW_PRIV_ENROLL):
            return True
    return False


def unknown_delegation(directory: Directory) -> Tuple[str, ...]:
    """委派取值不在已知集合时记未定，不按「无委派」推断为安全。"""
    unknown: List[str] = []
    for user in directory.users:
        value = _norm(user.delegation)
        if value not in DELEGATION_VALUES:
            unknown.append("%s（委派取值未知: %s）" % (user.qualified, user.delegation))
    return tuple(unknown)


def adcs_risks(templates: Sequence[Template]) -> Tuple[Tuple[Finding, ...], Tuple[str, ...]]:
    """ESC1 / ESC8 判定，判据对齐 SpecterOps Certified Pre-Owned 定义。

    ESC1 = 无签发要求（无审批且无授权签名）+ 可控主体 + 客户端认证 EKU + 低权可注册；
    ESC8 = HTTP 注册端点可 NTLM 中继（EPA 未启用）。
    """
    hits: List[Finding] = []
    unknown: List[str] = []
    for tpl in templates:
        if tpl.enrollee_supplies_subject is True:
            if tpl.requires_manager_approval is None or tpl.authorized_signatures_required is None:
                unknown.append("%s（签发要求字段缺失：审批或授权签名）" % tpl.name)
            elif tpl.requires_manager_approval is False and tpl.authorized_signatures_required is False:
                if _eku_is_client_auth(tpl.ekus) and _has_low_priv_enroll(tpl.enrollment_rights):
                    hits.append(Finding("esc1", tpl.name, "可控主体 + 客户端认证 EKU + 低权可注册 + 无签发要求"))
                elif not tpl.ekus or not tpl.enrollment_rights:
                    unknown.append("%s（EKU 或注册权字段缺失）" % tpl.name)
        if tpl.http_enrollment is True:
            if tpl.epa_enabled is False:
                hits.append(Finding("esc8", tpl.name, "HTTP 注册端点 + EPA 未启用（可 NTLM 中继）"))
            elif tpl.epa_enabled is None:
                unknown.append("%s（HTTP 端点 EPA 状态缺失）" % tpl.name)
        elif tpl.http_enrollment is None:
            unknown.append("%s（HTTP 注册字段缺失）" % tpl.name)
    return tuple(hits), tuple(unknown)


def dcsync_principals(aces: Iterable[Ace]) -> Tuple[Tuple[Finding, ...], Tuple[Finding, ...], Tuple[str, ...]]:
    """返回（完全复制权、仅部分复制权、排除说明）。机器账户默认排除。"""
    full: List[Finding] = []
    partial: List[Finding] = []
    notes: List[str] = []
    skipped = 0
    for ace in aces:
        if ace.principal.endswith("$"):
            skipped += 1
            continue
        right = _norm(ace.right).replace("ds-", "")
        if REPL_ALL in right:
            full.append(Finding("dcsync", ace.principal, "target=%s" % (ace.target or "-")))
        elif REPL_PARTIAL in right:
            partial.append(Finding("dcsync-partial", ace.principal, "target=%s" % (ace.target or "-")))
    if skipped:
        notes.append("已排除机器账户 %d 条复制权限记录" % skipped)
    return tuple(full), tuple(partial), tuple(notes)


def _privileged_users(directory: Directory) -> Tuple[DirectoryUser, ...]:
    return tuple(u for u in directory.users if any(_is_priv_group(g) for g in u.member_of))


def trust_risks(trusts: Sequence[Trust], directory: Optional[Directory] = None) -> Tuple[Tuple[Finding, ...], Tuple[str, ...], Tuple[str, ...]]:
    """返回（风险条目、跨域高权主体、未定说明）。"""
    hits: List[Finding] = []
    cross: List[Finding] = []
    unknown: List[str] = []
    for trust in trusts:
        label = "%s->%s" % (trust.source, trust.target)
        if trust.sid_filtering is False:
            hits.append(Finding("trust-sid-filtering-off", label, "SID 过滤关闭"))
        elif trust.sid_filtering is None:
            unknown.append("%s（SID 过滤字段缺失）" % label)
        if trust.direction == "bidirectional":
            hits.append(Finding("trust-bidirectional", label, "双向可传递"))
        elif trust.direction not in TRUST_DIRECTIONS:
            unknown.append("%s（信任方向缺失或未知: %r）" % (label, trust.direction))
    if directory is not None and directory.domain:
        for user in _privileged_users(directory):
            if user.domain and _norm(user.domain) != _norm(directory.domain):
                cross.append(Finding("cross-domain-privileged", user.qualified, "跨域高权主体"))
    return tuple(hits), tuple(cross), tuple(unknown)


def path_to_domain_admin(directory: Directory, owned: Sequence[str]) -> Tuple[str, ...]:
    """在成员关系与 ACE 上做 BFS，返回可达 Domain Admins 的最短路径（含起点）。"""
    edges: Dict[str, List[str]] = {}

    def link(src: str, dst: str) -> None:
        edges.setdefault(_norm(src), []).append(dst)

    for user in directory.users:
        for group in user.member_of:
            link(user.name, group)
    for ace in directory.aces:
        if ace.target:
            link(ace.principal, ace.target)

    starts = [_norm(x) for x in owned if x]
    queue: List[Tuple[str, ...]] = [(start,) for start in owned if start]
    seen = set(starts)
    while queue:
        path = queue.pop(0)
        node = _norm(path[-1])
        if _is_priv_group(path[-1]):
            return path
        for nxt in edges.get(node, ()):
            key = _norm(nxt)
            if key in seen:
                continue
            seen.add(key)
            queue.append(path + (nxt,))
    return ()


def assess(directory: Optional[Directory] = None,
           templates: Sequence[Template] = (),
           trusts: Sequence[Trust] = (),
           owned: Sequence[str] = (),
           tickets: Optional[Sequence[Dict[str, str]]] = None,
           proof: Optional[Dict[str, str]] = None) -> Dict[str, StepResult]:
    """把工件折叠为八步结论；缺工件的步骤记 `UNDETERMINED` 并写明缺失项。"""
    results: Dict[str, StepResult] = {}

    if directory is None:
        for step in ("ad-01", "ad-02", "ad-05", "ad-06"):
            results[step] = StepResult(step, UNDETERMINED, notes=("directory.json 未提供",))
    else:
        if trusts:
            results["ad-01"] = StepResult("ad-01", EXPLOITED, findings=tuple(
                Finding("trust", "%s->%s" % (t.source, t.target), t.direction or "方向未知")
                for t in trusts))
        elif directory.domain:
            results["ad-01"] = StepResult("ad-01", ABSENT, notes=("信任列表为空",))
        else:
            results["ad-01"] = StepResult("ad-01", UNDETERMINED, notes=("域名为空且无信任列表",))

        krb, krb_unknown = kerberoastable(directory)
        asrep, asrep_unknown = asrep_roastable(directory)
        dele = unconstrained(directory)
        ad02_notes = tuple(krb_unknown) + tuple(asrep_unknown) + unknown_delegation(directory)
        if krb or asrep or dele:
            results["ad-02"] = StepResult("ad-02", EXPLOITED,
                                          findings=krb + asrep + dele, notes=ad02_notes)
        elif ad02_notes:
            results["ad-02"] = StepResult("ad-02", UNDETERMINED, notes=ad02_notes)
        else:
            results["ad-02"] = StepResult("ad-02", ABSENT, notes=("三类面均为空集",))

        full, partial, dc_notes = dcsync_principals(directory.aces)
        if full:
            results["ad-05"] = StepResult("ad-05", EXPLOITED, findings=full, notes=dc_notes)
        elif partial:
            results["ad-05"] = StepResult("ad-05", EXPOSED_NO_AUTH, findings=partial, notes=dc_notes)
        else:
            results["ad-05"] = StepResult("ad-05", ABSENT, notes=dc_notes or ("无复制权限记录",))

        risks, cross, trust_unknown = trust_risks(trusts, directory)
        path = path_to_domain_admin(directory, owned)
        ad06_notes = tuple(trust_unknown) + (("路径: %s" % " -> ".join(path),) if path else ())
        bidirectional = any(f.kind == "trust-bidirectional" for f in risks)
        sid_off = any(f.kind == "trust-sid-filtering-off" for f in risks)
        if (bidirectional and cross) or (sid_off and path):
            results["ad-06"] = StepResult("ad-06", EXPLOITED, findings=risks + cross, notes=ad06_notes)
        elif risks or cross:
            results["ad-06"] = StepResult("ad-06", EXPOSED_NO_AUTH, findings=risks + cross, notes=ad06_notes)
        elif ad06_notes:
            results["ad-06"] = StepResult("ad-06", UNDETERMINED, notes=ad06_notes)
        else:
            results["ad-06"] = StepResult("ad-06", ABSENT, notes=("无风险信任且无跨域高权主体",))

    if templates:
        hits, tpl_unknown = adcs_risks(templates)
        if any(f.kind == "esc1" for f in hits):
            results["ad-04"] = StepResult("ad-04", EXPLOITED, findings=hits, notes=tpl_unknown)
        elif hits:
            results["ad-04"] = StepResult("ad-04", EXPOSED_NO_AUTH, findings=hits, notes=tpl_unknown)
        elif tpl_unknown:
            results["ad-04"] = StepResult("ad-04", UNDETERMINED, notes=tpl_unknown)
        else:
            results["ad-04"] = StepResult("ad-04", ABSENT, notes=("模板均为强约束",))
    else:
        results["ad-04"] = StepResult("ad-04", UNDETERMINED, notes=("templates.json 未提供",))

    if tickets is None:
        results["ad-03"] = StepResult("ad-03", UNDETERMINED, notes=("票据工件未提供（需实跑取证）",))
    elif tickets:
        results["ad-03"] = StepResult("ad-03", EXPLOITED, findings=tuple(
            Finding("ticket", str(t.get("account", "-")), "enctype=%s" % t.get("enctype", "unknown"))
            for t in tickets))
    else:
        results["ad-03"] = StepResult("ad-03", AUTH_REQUIRED, notes=("票据请求被拒，记 NOT_VULNERABLE 依据",))

    if proof is None:
        results["ad-07"] = StepResult("ad-07", UNDETERMINED, notes=("proof 工件未提供",))
    elif proof.get("value") and proof.get("value") == proof.get("panel"):
        results["ad-07"] = StepResult("ad-07", EXPLOITED,
                                      findings=(Finding("proof", "domain-controller", "双通道一致"),))
    else:
        results["ad-07"] = StepResult("ad-07", BLOCKED,
                                      notes=("proof 缺失或面板与截图值不一致",))

    executed = [r for r in results.values() if r.verdict in (EXPLOITED, EXPOSED_NO_AUTH)]
    results["ad-08"] = StepResult(
        "ad-08",
        EXPLOITED if executed else UNDETERMINED,
        findings=tuple(Finding("path", r.step_id, r.verdict) for r in executed),
        notes=() if executed else ("无可沉淀路径",),
    )
    return results
