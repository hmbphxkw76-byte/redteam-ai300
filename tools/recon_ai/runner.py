#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""编排器：执行序列 → 证据片段 → 资产清单 → 可复核验证报告。

对外唯一入口 `run_recon`。传输、截图、证据写入三者由参数注入（seam S1/S2/S3），
默认装配生产实现；测试注入替身即可离线跑通全部判据。
"""
import json
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List

from . import evidence as evidence_mod
from . import inventory as inventory_mod
from . import policy, probes, shot as shot_mod
from . import transport as transport_mod
from .model import Existence, ProbeResult

ECHO_PATH_HINT = ("POST",)

# 证据脱敏（SKILL.md OPSEC「不写盘凭据明文」）：命中即替换为不可逆占位
SECRET_PATTERNS = (
    re.compile(r"(?i)(bearer\s+)([A-Za-z0-9\-._~+/]{12,})"),
    re.compile(r"(?i)(aivp_sid=)([^\s;\",}]+)"),
    re.compile(r"\b(sk-[A-Za-z0-9\-_]{12,})\b"),
)


def redact(text):
    """把疑似凭据替换为占位串，返回 (脱敏后文本, 命中次数)。"""
    hits = 0
    for pattern in SECRET_PATTERNS:
        def _sub(match):
            nonlocal hits
            hits += 1
            return (match.group(1) if match.lastindex and match.lastindex >= 2 else "") + \
                "<REDACTED>"
        text = pattern.sub(_sub, text)
    return text, hits


@dataclass
class RunReport:
    """一次侦察运行的可复核结果（供 CLI 打印与报告消费）。"""

    target: str
    profile: str
    started: str
    finished: str
    inventory: object
    judgements: Dict[str, object] = field(default_factory=dict)
    evidence_paths: List[str] = field(default_factory=list)
    shots: Dict[str, str] = field(default_factory=dict)
    failed_steps: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    manifest: str = ""
    inventory_md: str = ""
    inventory_json: str = ""
    report_md: str = ""
    transport: str = ""
    shot: str = ""
    evidence_tool: str = ""
    results: Dict[str, List] = field(default_factory=dict)
    quality_failures: List[str] = field(default_factory=list)


def _base_target(target):
    target = (target or "").strip()
    if not target:
        raise ValueError("必须提供目标（如 http://192.168.40.189）")
    return target.rstrip("/")


def build_url(target, path, lab=""):
    """拼 URL：绝对路径原样，模板占位 {lab}/{host} 替换后再拼。"""
    host = inventory_mod.host_of(target)
    path = (path or "").replace("{lab}", lab).replace("{host}", host)
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return target + path


def _request(transport, spec, req, url, step_id, timeout):
    """发一次请求并包装为 ProbeResult（不抛异常：网络失败转 error）。"""
    result = ProbeResult(
        step_id=step_id, url=url, method=req.method,
        command=probes.curl_command(req.method, url, req.json_body),
        request_body=dict(req.json_body or {}),
        note=req.tag,
    )
    t0 = time.time()
    try:
        resp = transport.request(req.method, url, req.json_body,
                                 timeout=timeout or req.timeout)
    except Exception as exc:  # 传输层异常一律归「不可判定」，不中断整轮
        result.error = "传输异常：%s" % exc
        result.elapsed_ms = int((time.time() - t0) * 1000)
        return result
    result.status = resp.status
    result.body = resp.body or ""
    result.headers = resp.headers or {}
    result.content_type = resp.content_type or ""
    result.error = resp.error or ""
    result.elapsed_ms = resp.elapsed_ms or int((time.time() - t0) * 1000)
    # 单次探测的存在性三值（AC-04）：回退页 → 不存在；2xx → 存在；其余 → 不可判定
    if result.error:
        result.existence = Existence.UNDETERMINED
    elif probes.is_spa_fallback(result):
        result.existence = Existence.ABSENT
    elif result.ok:
        result.existence = Existence.PRESENT
    else:
        result.existence = Existence.UNDETERMINED
    return result


def run_recon(target, profile="passive", lab="MM_04", out_dir=None,
              transport=None, shot=None, writer=None, capture_shots=True,
              manifest=None, timeout=120, timebox_minutes=None):
    """执行一次完整侦察，返回 RunReport（AC-24 的端到端入口）。"""
    target = _base_target(target)
    profile = policy.normalize_profile(profile)
    out_dir = out_dir or os.path.join("evidence", "recon-ai")
    shots_dir = os.path.join(out_dir, "shots")
    manifest = manifest or os.path.join(out_dir, "MANIFEST.jsonl")
    transport = transport or transport_mod.make_transport()
    shot = shot or shot_mod.make_shot(enabled=capture_shots)
    writer = writer or evidence_mod.EvidenceWriter(out_dir, manifest=manifest)

    timebox = policy.TIMEOUT_MINUTES if timebox_minutes is None else timebox_minutes
    deadline = time.time() + timebox * 60
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    ctx = {"profile": profile, "headers": {}, "lab": lab}
    budget = policy.FailureBudget()
    judgements, evidence_paths, shots, endpoints = {}, [], {}, {}
    warnings, quality_failures = [], []
    step_results = {}
    present_seen = 0

    for spec in probes.STEP_SPECS:
        if present_seen == 0 and time.time() > deadline:
            warnings.append("时间盒到期（%d 分钟，未见任何 AI 组件）：中止剩余枚举并记录依据"
                            % timebox)
            budget.record(spec.step_id, "时间盒到期，未执行")
            break
        try:
            if spec.reuse:
                reused = step_results.get(spec.reuse, [])
                ctx["reuse_chat"] = next(
                    (r for r in reused if r.method == "POST"), None)
                results = []
            else:
                results = []
                for req in policy.gate_requests(spec, profile):
                    path = req.path_fn(ctx) if req.path_fn else req.path
                    url = build_url(target, path, lab)
                    result = _request(transport, spec, req, url, spec.step_id, timeout)
                    results.append(result)
                    if req.collect and not result.error:
                        try:
                            ctx.update(req.collect(result) or {})
                        except Exception as exc:  # 解析失败不影响证据，但须留痕
                            warnings.append("%s 解析器异常：%s" % (spec.step_id, exc))
                    if spec.requests and req is spec.requests[0]:
                        endpoints[spec.step_id] = url
                        ctx["headers"] = result.headers or ctx.get("headers", {})
                if spec.requests and spec.step_id not in endpoints:
                    endpoints[spec.step_id] = build_url(
                        target, spec.requests[0].path, lab)
                step_results[spec.step_id] = results

            judgement = probes.JUDGES[spec.judge](results, ctx)
            judgements[spec.step_id] = judgement
            if judgement.existence == Existence.PRESENT:
                present_seen += 1
            for key, value in (judgement.context or {}).items():
                ctx[key] = value
            if judgement.context.get("chat") is not None:
                ctx["reuse_chat"] = judgement.context["chat"]

            command = "\n".join(r.command for r in results) or \
                "# 本步骤复用 %s 的响应，无新增请求" % (spec.reuse or "-")
            output = "\n\n---\n\n".join(r.brief() for r in results) or \
                "复用响应：%s" % _reuse_brief(ctx.get("reuse_chat"))
            note = "判定：%s（%s）\n依据：%s" % (
                judgement.existence.value, judgement.product or "不可判定",
                judgement.note or "无")
            output, redacted = redact(output)
            if redacted:
                note += "\n脱敏：输出中 %d 处疑似凭据已替换为 <REDACTED>" % redacted
            ai_log = _ai_log(spec, results, ctx)

            kind = ("transcript" if spec.reuse or any(
                r.method in ECHO_PATH_HINT for r in results) else "url")
            shot_url = endpoints.get(spec.step_id) or (target + "/explore")
            shot_path, shot_kind = "", ""
            if capture_shots:
                shot_path, shot_kind = shot.capture(
                    spec.step_id, shot_url, shots_dir, kind=kind,
                    command=command, response=output)
            if shot_path:
                shots[spec.step_id] = shot_path

            path, code, err = writer.emit(
                step_id=spec.step_id, command=command, output=output,
                target=target, title=spec.title, screenshot=shot_path,
                shot_kind=shot_kind, profile=profile,
                shot_cmd=("" if shot_path else _shot_hint(shot, shot_url, spec.step_id)
                          if getattr(shot, "browser", "") else ""),
                note=note, ai_log=ai_log, strict=True,
            )
            evidence_paths.append(path)
            if code != 0:
                detail = err.splitlines()[-1][:120] if err else "退出码 %d" % code
                warnings.append("%s 证据质量门未过：%s" % (spec.step_id, detail))
                quality_failures.append("%s：%s" % (spec.step_id, detail))
        except Exception as exc:  # 失败隔离（AC-22）
            budget.record(spec.step_id, "步骤异常：%s" % exc)

    phases = {sid: (j.context or {}).get("phase", "")
              for sid, j in judgements.items()}
    hints = _credential_hints(step_results)
    inventory = inventory_mod.build(judgements, target, profile,
                                    failed_steps=budget.failed_steps,
                                    endpoints=endpoints, phases=phases,
                                    hints=hints)
    finished = datetime.now().astimezone().isoformat(timespec="seconds")

    os.makedirs(out_dir, exist_ok=True)
    inventory_md = os.path.join(out_dir, "ai-assets.md")
    inventory_json = os.path.join(out_dir, "ai-assets.json")
    with open(inventory_md, "w", encoding="utf-8") as f:
        f.write(inventory.to_markdown())
    with open(inventory_json, "w", encoding="utf-8") as f:
        json.dump(inventory.to_dict(), f, ensure_ascii=False, indent=2)

    report_md = os.path.join(out_dir, "verification-report.md")
    with open(report_md, "w", encoding="utf-8") as f:
        f.write(_render_report(target, profile, started, finished,
                               judgements, evidence_paths, shots, inventory,
                               budget, writer, shot, transport, manifest, warnings,
                               quality_failures))

    return RunReport(
        target=target, profile=profile, started=started, finished=finished,
        results=step_results, quality_failures=quality_failures,
        inventory=inventory, judgements=judgements,
        evidence_paths=evidence_paths, shots=shots,
        failed_steps=budget.failed_steps, warnings=warnings, manifest=manifest,
        inventory_md=inventory_md, inventory_json=inventory_json,
        report_md=report_md, transport=transport.describe(),
        shot=shot.describe(), evidence_tool=writer.describe(),
    )


def _credential_hints(step_results):
    """从响应头提取凭据线索并压缩为指纹（SKILL.md：仅记指纹，不落明文）。"""
    from .model import credential_hint
    hints = {}
    for step_id, results in step_results.items():
        for result in results:
            for key, value in (result.headers or {}).items():
                if key.lower() in ("set-cookie", "authorization", "x-api-key"):
                    hint = credential_hint(value)
                    if hint:
                        hints[step_id] = hint
                        break
            if step_id in hints:
                break
    return hints


def _ai_log(spec, results, ctx):
    """记录对目标模型的交互留痕（GOVERNANCE §6.3 / S3 §7 的「查询须入正文」）。

    仅对「向目标 AI 系统发送提示」的步骤产出；无提示交互时返回空串。
    """
    # 仅对「真的向目标模型发送了提示」的步骤产出；否则不臆造交互留痕（§6.3 真实性）
    posts = [r for r in results
             if r.method == "POST" and (r.request_body or {}).get("prompt")]
    reused_from = ""
    if not posts and spec.reuse and ctx.get("reuse_chat") is not None:
        posts = [ctx["reuse_chat"]]
        reused_from = "（复用 %s 的响应）" % spec.reuse
    if not posts:
        return ""
    result = posts[0]
    sse = probes.parse_sse(result.body)
    model = ctx.get("model") or "不可判定"
    prompt = (result.request_body or {}).get("prompt", "（未记录）")
    return "\n".join([
        "通道：%s %s%s" % (result.method, result.url, reused_from),
        "被交互模型：%s（由 recon-01 部署配置识别的默认模型）" % model,
        "提示（prompt）：%s" % prompt,
        "输出（前 600 字符）：%s" % (sse.text[:600] or "（空）"),
        "采纳：是（作为 %s 的护栏/服务面判定依据）" % spec.step_id,
        "备注：本记录为目标模型交互留痕，不含 AI 辅助工具的会话内容。",
    ])


def _reuse_brief(result):
    if result is None:
        return "（无复用响应）"
    return "%s %s → HTTP %d" % (result.method, result.url, result.status)


def _shot_hint(shot, url, step_id):
    """无截图能力时给出可执行钩子（诚实标注待补录，不伪造）。"""
    browser = getattr(shot, "browser", "")
    if browser:
        return '%s --headless=new --screenshot=%s.png "%s"' % (browser, step_id, url)
    return "截图待补录：本环境未检出无头浏览器（可设 RECON_AI_BROWSER 指定路径）"


def _render_report(target, profile, started, finished, judgements,
                   evidence_paths, shots, inventory, budget, writer, shot,
                   transport, manifest, warnings=(), quality_failures=()):
    """可复核验证报告：逐步判定 + 证据引用 + 复核命令（AC-24）。"""
    rows = []
    for spec in probes.STEP_SPECS:
        judgement = judgements.get(spec.step_id)
        existence = judgement.existence.value if judgement else "未执行"
        product = (judgement.product if judgement else "") or "不可判定"
        rows.append("| `%s` | %s | %s | `%s` | %s |" % (
            spec.step_id, existence, product,
            os.path.basename(shots.get(spec.step_id, "")) or "待补录",
            os.path.basename(writer.fragment_path(spec.step_id))))
    violations = inventory.contract_violations()
    lines = [
        "# recon-ai 端到端验证报告",
        "",
        "- **目标**：`%s`" % target,
        "- **执行分级**：`%s`" % profile,
        "- **开始 / 结束**：`%s` / `%s`" % (started, finished),
        "- **传输**：%s　**截图**：%s　**证据工具**：%s"
        % (transport.describe(), shot.describe(), writer.describe()),
        "",
        "## 1. 逐步判定",
        "",
        "| 步骤 | 存在性 | 产品/引擎 | 访问证明截图 | 证据片段 |",
        "|---|---|---|---|---|",
    ] + rows + [
        "",
        "## 2. 资产清单契约",
        "",
        "- 资产条目：**%d**" % len(inventory.assets),
        "- 不可判定类别：%s" % ("、".join(inventory.undetermined) or "无"),
        "- 契约校验：%s" % ("通过" if not violations else "不通过 → " + "；".join(violations)),
        "- 疑似诱饵：%s%s" % ("是" if inventory.decoy_suspected else "否",
                              ("（%s）" % inventory.decoy_reason) if inventory.decoy_reason else ""),
        "- 失败步骤（失败隔离）：%s" % (budget.summary()),
        "- 证据质量门告警：%s" % ("\n  - " + "\n  - ".join(warnings) if warnings else "无"),
        "- 质量门失败（违反 C8，不得提交）：%s" % (
            "\n  - " + "\n  - ".join(quality_failures) if quality_failures else "无"),
        "",
        "## 3. 证据清单",
        "",
        "- 证据清单（JSONL）：`%s`" % manifest,
        "- 片段数：**%d**" % len(evidence_paths),
        "",
        "## 4. 复核命令（copy/paste）",
        "",
        "```bash",
        "python tools/recon_ai/cli.py run --target %s --profile %s" % (target, profile),
        "python tools/collect_evidence.py --step recon-01 --cmd 'curl -s %s/api/config' "
        "--output-file - --out /tmp/check.md < <(curl -s %s/api/config)" % (target, target),
        "python tools/recon_ai/cli.py inventory --path %s" % os.path.join(
            os.path.dirname(manifest), "ai-assets.json"),
        "```",
        "",
        "## 5. 结论",
        "",
        "- 端到端闭环：%s" % ("是（执行 → 取证 → 结果产出 全部落盘）"
                              if evidence_paths else "否（无证据片段）"),
        "- 契约合规：%s" % ("是" if not violations else "否"),
        "- 说明：本报告为技能级验证产物，不含攻击动作；flag 双通道与报告提交"
        "属 `report-exam` / `verify-evidence` 职责。",
        "",
    ]
    return "\n".join(lines)
