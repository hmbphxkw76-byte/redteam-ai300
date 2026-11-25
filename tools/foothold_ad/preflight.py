#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""无真实环境时的采集前置清单（preflight）。

纯静态生成：不联网、不生成样本、不伪造输出。操作员在真实域按清单采集工件后，
再用 `cli verify` 校验来源与完整性，最后 `cli analyze` 出结论。
"""
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import artifact
from .provenance import MANIFEST_FILE, REQUIRED_FIELDS
from .runner import REQUIRED_ARTIFACTS


@dataclass(frozen=True)
class ArtifactSpec:
    file: str
    purpose: str
    fields: Tuple[str, ...]
    commands: Tuple[str, ...]

    def steps(self) -> Tuple[str, ...]:
        return tuple(sorted(step for step, needs in REQUIRED_ARTIFACTS.items() if self.file in needs))


SPECS: Tuple[ArtifactSpec, ...] = (
    ArtifactSpec(
        artifact.DIRECTORY_FILE,
        "目录导出：用户/组/ACE/委派（BloodHound 或 LDAP 导出）",
        ("domain", "users[].name", "users[].enabled", "users[].spn",
         "users[].preauth_required", "users[].delegation", "users[].member_of", "aces[]"),
        ("bloodhound-python -d <DOMAIN> -u <USER> -p <PASS> -ns <DC> -c All",
         "ldapsearch -H ldap://<DC> -x -b \"<BASE_DN>\" \"(objectClass=user)\""),
    ),
    ArtifactSpec(
        artifact.TEMPLATES_FILE,
        "证书模板导出：ESC1/ESC8 判定字段（Certipy find -json）",
        ("templates[].name", "templates[].enrollee_supplies_subject", "templates[].ekus",
         "templates[].enrollment_rights", "templates[].requires_manager_approval",
         "templates[].authorized_signatures_required", "templates[].http_enrollment",
         "templates[].epa_enabled"),
        ("certipy find -u <USER>@<DOMAIN> -p <PASS> -dc-ip <DC> -json -output certipy",),
    ),
    ArtifactSpec(
        artifact.TRUSTS_FILE,
        "信任列表：方向/SID 过滤/跨域关系",
        ("trusts[].source", "trusts[].target", "trusts[].direction", "trusts[].sid_filtering"),
        ("nltest /domain_trusts /all_trusts /v",
         "Get-ADTrust -Filter * | Select-Object Source,Target,Direction,SIDFilteringQuarantined"),
    ),
)

OPTIONAL_SPECS: Tuple[ArtifactSpec, ...] = (
    ArtifactSpec("tickets.json", "票据获取结果（ad-03）；无实跑即留空",
                 ("[].account", "[].enctype"),
                 ("impacket-GetUserSPNs <DOMAIN>/<USER>:<PASS> -dc-ip <DC> -request",)),
    ArtifactSpec("proof.json", "域控 proof 双通道（ad-07）：value 与面板值须逐字一致",
                 ("value", "panel"),
                 ("whoami; id; type C:\\proof.txt",)),
)


def _status(artifacts_dir: str, name: str) -> str:
    return "present" if os.path.isfile(os.path.join(artifacts_dir, name)) else "missing"


def build(artifacts_dir: str) -> Dict[str, Any]:
    """生成采集清单；缺失项与已存在项分列，便于真实环境按序补采。"""
    plan: List[Dict[str, Any]] = []
    for spec in SPECS + OPTIONAL_SPECS:
        plan.append({
            "file": spec.file,
            "purpose": spec.purpose,
            "required_fields": list(spec.fields),
            "commands": list(spec.commands),
            "steps": list(spec.steps()),
            "status": _status(artifacts_dir, spec.file),
        })
    missing = [item["file"] for item in plan if item["status"] == "missing"]
    return {
        "artifacts_dir": artifacts_dir,
        "missing": missing,
        "present": [item["file"] for item in plan if item["status"] == "present"],
        "provenance": {
            "manifest": MANIFEST_FILE,
            "manifest_present": os.path.isfile(os.path.join(artifacts_dir, MANIFEST_FILE)),
            "required_fields": list(REQUIRED_FIELDS),
        },
        "plan": plan,
        "next": "采集后执行 `cli verify` 校验来源与完整性，再执行 `cli analyze` 出结论",
    }


def render(payload: Dict[str, Any]) -> str:
    """人类可读清单；逐条列出「缺什么 / 用什么命令采 / 采完要有什么字段」。"""
    lines = ["工件目录: %s" % payload["artifacts_dir"],
             "缺失: %s" % (", ".join(payload["missing"]) or "无（可执行 verify）")]
    for item in payload["plan"]:
        if item["status"] == "present" and item["file"] in ("tickets.json", "proof.json"):
            continue
        lines.append("")
        lines.append("- %s [%s] %s" % (item["file"], item["status"], item["purpose"]))
        for command in item["commands"]:
            lines.append("    采集: %s" % command)
        lines.append("    字段: %s" % ", ".join(item["required_fields"]))
        if item["steps"]:
            lines.append("    依赖步骤: %s" % ", ".join(item["steps"]))
    provenance = payload["provenance"]
    lines.append("")
    lines.append("来源登记: %s（%s）" % (provenance["manifest"],
                                        "已存在" if provenance["manifest_present"] else "缺失，须补建"))
    lines.append("登记字段: %s" % ", ".join(provenance["required_fields"]))
    lines.append("下一步: %s" % payload["next"])
    return "\n".join(lines)
