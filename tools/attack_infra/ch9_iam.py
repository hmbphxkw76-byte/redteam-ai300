#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Ch9 A1：IAM 策略枚举 / trust policy 判定 / 角色链提权（AC-01..04）。

一手事实：`docs/research/attack-infra-ch9-canonical.md` C-1/C-2/C-3/C-5。
所有云 CLI 命令经 ctx.command（唯一 seam），凭据仅产指纹（P-2）。
"""
import json
import re
from typing import Any, Dict, List, Tuple

from .ch9_model import (
    ABSENT, AUTH_REQUIRED, BLOCKED, EXPLOITED, EXPOSED_NO_AUTH,
    Ch9Verdict, CredFingerprint,
)


def _argv_to_text(argv: Tuple[str, ...]) -> str:
    return " ".join(str(a) for a in argv)


def enumerate_policies(policy_json: str) -> List[Dict[str, Any]]:
    """AC-01：解析策略 JSON 为 Statement 列表（Sid/Action/Resource/Condition）。

    只读解析，不执行命令；调用方负责把命令输出传入。
    """
    try:
        doc = json.loads(policy_json)
    except (ValueError, TypeError):
        return []
    raw = doc.get("PolicyDocument", doc) if isinstance(doc, dict) else None
    statements = raw.get("Statement", []) if isinstance(raw, dict) else []
    if isinstance(statements, dict):
        statements = [statements]
    result = []
    for statement in statements:
        if not isinstance(statement, dict):
            continue
        actions = statement.get("Action", [])
        if isinstance(actions, str):
            actions = [actions]
        resources = statement.get("Resource", [])
        if isinstance(resources, str):
            resources = [resources]
        result.append({
            "sid": statement.get("Sid", ""),
            "effect": statement.get("Effect", ""),
            "actions": list(actions),
            "resources": list(resources),
            "condition": statement.get("Condition", {}),
        })
    return result


def _has_assume_role(statements: List[Dict[str, Any]], role_arn: str = "") -> bool:
    for s in statements:
        if s.get("effect") != "Allow":
            continue
        if any(a == "sts:AssumeRole" or a == "sts:*" or a == "*"
               for a in s.get("actions", [])):
            if not role_arn or role_arn in s.get("resources", []) or "*" in s.get("resources", []):
                return True
    return False


def trust_allows(trust_json: str, principal_arn: str) -> bool:
    """AC-02：trust policy 的 Principal 含账户 root 或显式 principal 且 Action 为 AssumeRole。"""
    return trust_allows_raw(trust_json, principal_arn)


def trust_allows_raw(trust_json: str, principal_arn: str) -> bool:
    """直接解析原始 Principal 字段（含 AWS/root/*）。"""
    try:
        doc = json.loads(trust_json)
    except (ValueError, TypeError):
        return False
    raw = doc.get("AssumeRolePolicyDocument", doc)
    statements = raw.get("Statement", []) if isinstance(raw, dict) else []
    if isinstance(statements, dict):
        statements = [statements]
    for s in statements:
        if not isinstance(s, dict) or s.get("Effect") != "Allow":
            continue
        action = s.get("Action", "")
        actions = [action] if isinstance(action, str) else list(action)
        if not any(a in ("sts:AssumeRole", "sts:*", "*") for a in actions):
            continue
        principal = s.get("Principal", {})
        if principal == "*":
            return True
        blob = json.dumps(principal)
        if ":root" in blob or principal_arn in blob:
            return True
    return False


def _fingerprint_credentials(output: str, location: str) -> List[CredFingerprint]:
    """从 assume-role 输出抽取临时凭据指纹（不落明文）。"""
    import re
    out: List[CredFingerprint] = []
    for match in re.finditer(r'"(AccessKeyId|SecretAccessKey|SessionToken)"\s*:\s*"([^"]+)"', output or ""):
        value = match.group(2)
        out.append(CredFingerprint(prefix=value[:4], length=len(value),
                                   location="%s:%s" % (location, match.group(1))))
    return out


def _project_tags(text: str) -> set:
    """从 ARN / 标签文本中抽项目名（role/<project>-* 或 Project=<value>）。"""
    found = set()
    for m in re.finditer(r"role/([A-Za-z0-9_-]+?)(?:Role|$)", text or ""):
        found.add(m.group(1))
    for m in re.finditer(r"Project[\"']?\s*[:=]\s*[\"']([A-Za-z0-9_-]+)", text or "", re.I):
        found.add(m.group(1))
    return found


def _redact_credentials(text: str) -> str:
    """P-2：把 assume-role 响应中的凭据值替换为脱敏占位，防止明文落片段。"""
    import re
    return re.sub(r'("(?:AccessKeyId|SecretAccessKey|SessionToken)"\s*:\s*")[^"]+(")',
                  r'\1<redacted>\2', text or "")


def enumerate_policies_step(ctx: Any) -> Ch9Verdict:
    """iam-01（AC-01）：调用 iam 列举 inline/attached 策略。"""
    role = getattr(ctx, "iam_role", "") or "DataScientistRole"
    argv_inline_list = ("aws", "iam", "list-role-policies", "--role-name", role)
    argv_inline_get = ("aws", "iam", "get-role-policy", "--role-name", role,
                       "--policy-name", getattr(ctx, "iam_policy", "") or "DataScientistPolicy")
    argv_attached = ("aws", "iam", "list-attached-role-policies", "--role-name", role)
    commands = [_argv_to_text(argv_inline_list), _argv_to_text(argv_attached)]
    outs: List[str] = []
    parsed: List[Dict[str, Any]] = []
    for argv in (argv_inline_list, argv_attached, argv_inline_get):
        result = ctx.command.run(argv, timeout=ctx.timeout)
        outs.append("$ %s\n(exit=%d)\n%s" % (_argv_to_text(argv), result.code,
                                             (result.stdout or result.stderr).strip()[:900]))
        if argv == argv_inline_get and result.ok:
            parsed = enumerate_policies(result.stdout)
    if all("AccessDenied" in o or "not authorized" in o for o in outs):
        return Ch9Verdict("ch9-iam-01", AUTH_REQUIRED, "forbidden",
                          "IAM 策略读取被拒绝", "; ".join(commands), "\n\n".join(outs))
    if getattr(ctx, "command", None) and all("127" in o or "not found" in o for o in outs):
        return Ch9Verdict("ch9-iam-01", ABSENT, "no_tool",
                          "未安装 aws CLI", "; ".join(commands), "\n\n".join(outs))
    return Ch9Verdict("ch9-iam-01", EXPOSED_NO_AUTH, "",
                      "解析 %d 条策略声明" % len(parsed), "; ".join(commands),
                      "\n\n".join(outs),
                      {"statements": parsed})


def trust_step(ctx: Any) -> Ch9Verdict:
    """iam-02（AC-02）：读取 trust policy 并判定当前身份是否可扮演。"""
    role = getattr(ctx, "iam_role", "") or "MLOpsRole"
    principal = getattr(ctx, "iam_principal", "") or "arn:aws:iam::533267328750:root"
    argv = ("aws", "iam", "get-role", "--role-name", role,
            "--query", "Role.AssumeRolePolicyDocument")
    result = ctx.command.run(argv, timeout=ctx.timeout)
    text = (result.stdout or result.stderr).strip()
    command = _argv_to_text(argv)
    if not result.ok:
        reason = "forbidden" if ("AccessDenied" in text or "not authorized" in text) else "no_tool"
        return Ch9Verdict("ch9-iam-02", AUTH_REQUIRED if reason == "forbidden" else ABSENT,
                          reason, "trust policy 读取失败", command, text[:700])
    allows = trust_allows(text, principal)
    output = "$ %s\n(exit=%d)\n%s\n判定 Principal=%s 可扮演=%s" % (
        command, result.code, text[:800], principal, allows)
    return Ch9Verdict("ch9-iam-02", EXPOSED_NO_AUTH if allows else BLOCKED,
                      "" if allows else "guardrail",
                      "trust policy 允许当前身份扮演" if allows
                      else "trust policy 不允许（显式拒绝或主体不匹配）",
                      command, output,
                      {"trust_allows": allows, "role": role, "principal": principal})


def chain_verdict(ctx: Any) -> Ch9Verdict:
    """iam-03（AC-03/04）：沿 assume-role 链逐跳判定，末端跨项目即提权成功。"""
    chain: Tuple[str, ...] = getattr(ctx, "iam_chain", ())
    if not chain:
        return Ch9Verdict("ch9-iam-03", ABSENT, "none_found",
                          "未提供角色链", "aws sts assume-role --role-arn <ARN>",
                          "判定依据：ctx.iam_chain 为空")
    outs: List[str] = []
    fps: List[CredFingerprint] = []
    all_commands: List[str] = []
    crossed = False
    for i, role_arn in enumerate(chain):
        session = "ch9-hop-%d" % (i + 1)
        argv = ("aws", "sts", "assume-role", "--role-arn", role_arn,
                "--role-session-name", session)
        all_commands.append(_argv_to_text(argv))
        result = ctx.command.run(argv, timeout=ctx.timeout)
        output = (result.stdout or result.stderr).strip()
        safe_output = _redact_credentials(output)
        outs.append("$ %s\n(exit=%d)\n%s" % (_argv_to_text(argv), result.code, safe_output[:800]))
        if not result.ok:
            return Ch9Verdict("ch9-iam-03", BLOCKED, "guardrail",
                              "角色链在第 %d 跳被拒绝" % (i + 1),
                              "; ".join(all_commands), "\n\n".join(outs))
        fps.extend(_fingerprint_credentials(output, "hop-%d" % (i + 1)))
        # AC-04：跨项目边界判定基于策略语义，而非硬编码某一项目名。
        # 命中任一即判越界：通配符动作(*:* / s3:*) + Resource:*，
        # 或末端策略引用的项目标识不同于链首角色所属项目（ARN 中的项目名提取）。
        if i == len(chain) - 1:
            blob = safe_output
            wildcard_action = bool(re.search(
                r'"Action"\s*:\s*"(\*|[^\"]*\*[^\"]*)"', blob))
            resource_star = bool(re.search(
                r'"Resource"\s*:\s*"\*"', blob))
            crossed = wildcard_action and resource_star
            if not crossed:
                projects = _project_tags(blob)
                first_project = _project_tags(chain[0]) if chain else set()
                crossed = bool(projects - first_project - {"*", ""}) and bool(projects)
    summary = "完成 %d 跳角色链，%d 条凭据指纹" % (len(chain), len(fps))
    if crossed:
        summary += "；链末端策略打破项目边界"
    return Ch9Verdict("ch9-iam-03", EXPLOITED if crossed else EXPOSED_NO_AUTH, "",
                      summary, "; ".join(all_commands), "\n\n".join(outs),
                      {"fingerprints": [f.as_text() for f in fps],
                       "hop_count": len(chain), "crossed_boundary": crossed})
