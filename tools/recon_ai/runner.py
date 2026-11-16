#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""编排器：执行序列 → 证据片段 → 资产清单 → 可复核验证报告。

对外唯一入口 `run_recon`。传输、截图、证据写入三者由参数注入（seam S1/S2/S3），
默认装配生产实现；测试注入替身即可离线跑通全部判据。
"""
import json
import os
import re
import shutil
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List
from urllib.parse import urlsplit

from . import discovery as discovery_mod
from . import evidence as evidence_mod
from . import inventory as inventory_mod
from . import policy, probes, shot as shot_mod
from . import transport as transport_mod
from . import verifier as verifier_mod
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
    run_id: str = ""
    run_dir: str = ""
    run_json: str = ""
    verification: object = None
    verification_json: str = ""
    gaps: List[dict] = field(default_factory=list)


def _base_target(target):
    target = (target or "").strip()
    if not target:
        raise ValueError("必须提供目标（如 http://192.168.40.189）")
    target = target.rstrip("/")
    # 目标若是具体文件（如报告页 x.html），端点探测须回到其 origin，
    # 否则会拼出 `/x.html/v1/models` 这类不存在的路径。
    parts = urlsplit(target if "://" in target else "http://" + target)
    if parts.scheme and parts.netloc and re.search(
            r"\.[A-Za-z0-9]{2,5}$", parts.path or ""):
        return "%s://%s" % (parts.scheme, parts.netloc)
    return target


def _make_run_id(target):
    """运行标识：时间戳 + 主机 + 短随机后缀（同一秒内复跑也不互相覆盖）。"""
    stamp = datetime.now().astimezone().strftime("%Y%m%dT%H%M%S")
    slug = re.sub(r"[^A-Za-z0-9.-]+", "-", inventory_mod.host_of(target)).strip("-")
    return "%s-%s-%s" % (stamp, (slug or "target")[:32], os.urandom(2).hex())


def build_url(target, path, lab=""):
    """拼 URL：绝对路径原样，模板占位 {lab}/{host} 替换后再拼。"""
    host = inventory_mod.host_of(target)
    path = (path or "").replace("{lab}", lab).replace("{host}", host)
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return target + path


def _request(transport, spec, req, url, step_id, timeout, body=None):
    """发一次请求并包装为 ProbeResult（不抛异常：网络失败转 error）。"""
    payload = req.json_body if body is None else body
    result = ProbeResult(
        step_id=step_id, url=url, method=req.method,
        command=probes.curl_command(req.method, url, payload),
        request_body=dict(payload or {}),
        note=req.tag,
    )
    t0 = time.time()
    try:
        resp = transport.request(req.method, url, payload,
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
    requested = (target or "").strip().rstrip("/")
    target = _base_target(target)
    profile = policy.normalize_profile(profile)
    out_dir = out_dir or os.path.join("evidence", "recon-ai")
    transport = transport or transport_mod.make_transport()
    shot = shot or shot_mod.make_shot(enabled=capture_shots)
    warnings, quality_failures = [], []

    plan = None
    try:
        # 传原始入口（含报告页路径）：发现阶段按 origin 探测端点，
        # 同时读取入口页本身以识别独立聊天按钮/iframe 等交互入口。
        plan = discovery_mod.discover(requested, transport,
                                      timeout=min(timeout or 15, 20))
    except Exception as exc:  # 发现失败降级为通用端点枚举，不阻塞主线
        warnings.append("发现阶段异常（降级为通用端点）：%s" % exc)

    run_id = _make_run_id(target)
    if writer is None:
        run_dir = os.path.join(out_dir, "runs", run_id)
        manifest = manifest or os.path.join(run_dir, "MANIFEST.jsonl")
        writer = evidence_mod.EvidenceWriter(run_dir, manifest=manifest)
    else:
        run_dir = writer.out_dir
        manifest = writer.manifest or manifest or \
            os.path.join(run_dir, "MANIFEST.jsonl")
    shots_dir = os.path.join(run_dir, "shots")

    timebox = policy.TIMEOUT_MINUTES if timebox_minutes is None else timebox_minutes
    deadline = time.time() + timebox * 60
    started = datetime.now().astimezone().isoformat(timespec="seconds")
    ctx = {"profile": profile, "headers": {}, "lab": lab, "plan": plan}
    budget = policy.FailureBudget()
    judgements, evidence_paths, shots, endpoints = {}, [], {}, {}
    step_results, step_records = {}, []
    present_seen = 0

    for spec in probes.STEP_SPECS:
        if present_seen == 0 and time.time() > deadline:
            warnings.append("时间盒到期（%d 分钟，未见任何 AI 组件）：中止剩余枚举并记录依据"
                            % timebox)
            budget.record(spec.step_id, "时间盒到期，未执行")
            break
        record = {"step_id": spec.step_id, "status": "running", "existence": "不可判定",
                  "product": "", "basis": "", "tried": [], "evidence": "",
                  "evidence_ok": False}
        step_records.append(record)
        try:
            if spec.reuse:
                reused = step_results.get(spec.reuse, [])
                ctx["reuse_chat"] = next(
                    (r for r in reused if r.method == "POST"), None)
                results = []
            else:
                results = []
                for req in policy.gate_requests(spec, profile):
                    if req.when is not None and not req.when(ctx):
                        continue
                    path = req.path_fn(ctx) if req.path_fn else req.path
                    url = build_url(target, path, lab)
                    body = req.body_fn(ctx) if req.body_fn is not None else None
                    result = _request(transport, spec, req, url, spec.step_id,
                                      timeout, body=body)
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
                    fallback = (getattr(plan, "entry_url", "") if plan is not None
                                else "") or build_url(
                                    target, spec.requests[0].path, lab)
                    endpoints[spec.step_id] = fallback
                if plan is not None:
                    results.extend(plan.step_results.get(spec.step_id, []))
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
            note = "判定：%s（%s）\n依据：%s\n证据基底：%s" % (
                judgement.existence.value, judgement.product or "不可判定",
                judgement.note or "无", judgement.basis or judgement.note or "无")
            output, redacted = redact(output)
            if redacted:
                note += "\n脱敏：输出中 %d 处疑似凭据已替换为 <REDACTED>" % redacted
            ai_log = _ai_log(spec, results, ctx)

            kind = ("transcript" if spec.reuse or any(
                r.method in ECHO_PATH_HINT for r in results) else "url")
            shot_url = ((judgement.context or {}).get("endpoint")
                        or endpoints.get(spec.step_id) or (target + "/explore"))
            shot_path, shot_kind = "", ""
            if capture_shots:
                shot_path, shot_kind = shot.capture(
                    spec.step_id, shot_url, shots_dir, kind=kind,
                    command=command, response=output)
            if shot_path:
                shots[spec.step_id] = shot_path

            path, code, err = writer.emit(
                step_id=spec.step_id, command=command, output=output,
                target=requested, title=spec.title, screenshot=shot_path,
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

            tried_src = results or (
                step_results.get(spec.reuse, []) if spec.reuse else [])
            record.update({
                "status": "done",
                "existence": judgement.existence.value,
                "product": judgement.product or "不可判定",
                "basis": judgement.basis or judgement.note or "无",
                "tried": [{"method": r.method, "url": r.url, "status": r.status,
                           "error": r.error} for r in tried_src],
                "evidence": path, "evidence_ok": code == 0,
            })
        except Exception as exc:  # 失败隔离（AC-22）
            budget.record(spec.step_id, "步骤异常：%s" % exc)
            record.update({"status": "failed", "basis": "步骤异常：%s" % exc,
                           "existence": "不可判定"})

    for spec in probes.STEP_SPECS:
        if any(r["step_id"] == spec.step_id for r in step_records):
            continue
        reason = budget.reasons.get(spec.step_id, "未执行")
        step_records.append({
            "step_id": spec.step_id,
            "status": "timeout" if "时间盒" in reason else "failed",
            "existence": "不可判定", "product": "", "basis": reason,
            "tried": [], "evidence": "", "evidence_ok": False,
        })

    phases = {sid: (j.context or {}).get("phase", "")
              for sid, j in judgements.items()}
    hints = _credential_hints(step_results)
    tried_by_step = {r["step_id"]: r.get("tried", []) for r in step_records}
    inventory = inventory_mod.build(
        judgements, requested, profile,
        failed_steps=budget.failed_steps, endpoints=endpoints, phases=phases,
        hints=hints, tried=tried_by_step,
        extra_signals=(len(plan.signals) if plan is not None else 0))
    finished = datetime.now().astimezone().isoformat(timespec="seconds")

    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(run_dir, exist_ok=True)
    inventory_md = os.path.join(out_dir, "ai-assets.md")
    inventory_json = os.path.join(out_dir, "ai-assets.json")
    with open(inventory_md, "w", encoding="utf-8") as f:
        f.write(inventory.to_markdown())
    with open(inventory_json, "w", encoding="utf-8") as f:
        json.dump(inventory.to_dict(), f, ensure_ascii=False, indent=2)
    for path in (inventory_md, inventory_json):
        if os.path.realpath(run_dir) != os.path.realpath(out_dir):
            shutil.copy2(path, os.path.join(run_dir, os.path.basename(path)))

    run_json = os.path.join(run_dir, "run.json")
    report_md = os.path.join(out_dir, "verification-report.md")
    meta = {
        "run_id": run_id, "target": requested, "probe_base": target, "profile": profile,
        "started": started, "finished": finished,
        "run_dir": run_dir,
        "plan": plan.to_dict() if plan is not None else None,
        "steps": step_records, "failed_steps": budget.failed_steps,
        "warnings": warnings, "quality_failures": quality_failures,
        "manifest": manifest, "inventory_json": inventory_json,
        "inventory_md": inventory_md, "report_md": report_md,
        "contract_violations": inventory.contract_violations(),
        "shots": shots, "evidence_paths": evidence_paths,
        "transport": transport.describe(), "shot": shot.describe(),
        "evidence_tool": writer.describe(),
    }
    with open(run_json, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # 报告两段式：先写全结构（结论 PENDING）→ 门禁判定 → 以判定重写结论
    _write_report(report_md, meta, inventory, judgements, budget,
                  writer, shot, transport, None)
    verification = verifier_mod.verify_run(run_dir)
    _write_report(report_md, meta, inventory, judgements, budget,
                  writer, shot, transport, verification)
    verifier_mod.finalize(verification, report_md)
    _write_report(report_md, meta, inventory, judgements, budget,
                  writer, shot, transport, verification)
    verification_json = verifier_mod.write_verification(run_dir, verification)
    meta["verification"] = verification.to_dict()
    with open(run_json, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    if os.path.realpath(run_dir) != os.path.realpath(out_dir):
        shutil.copy2(report_md, os.path.join(run_dir, "verification-report.md"))

    return RunReport(
        target=requested, profile=profile, started=started, finished=finished,
        results=step_results, quality_failures=quality_failures,
        inventory=inventory, judgements=judgements,
        evidence_paths=evidence_paths, shots=shots,
        failed_steps=budget.failed_steps, warnings=warnings, manifest=manifest,
        inventory_md=inventory_md, inventory_json=inventory_json,
        report_md=report_md, transport=transport.describe(),
        shot=shot.describe(), evidence_tool=writer.describe(),
        run_id=run_id, run_dir=run_dir, run_json=run_json,
        verification=verification, verification_json=verification_json,
        gaps=inventory.gaps,
    )


def _write_report(path, meta, inventory, judgements, budget, writer, shot,
                  transport, verification):
    with open(path, "w", encoding="utf-8") as f:
        f.write(_render_report(meta, inventory, judgements, budget, writer,
                               shot, transport, verification))


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
             if r.method == "POST" and _prompt_of(r)]
    reused_from = ""
    if not posts and spec.reuse and ctx.get("reuse_chat") is not None:
        posts = [ctx["reuse_chat"]]
        reused_from = "（复用 %s 的响应）" % spec.reuse
    if not posts:
        return ""
    result = posts[0]
    model = ctx.get("model") or "不可判定"
    prompt = _prompt_of(result) or "（未记录）"
    return "\n".join([
        "通道：%s %s%s" % (result.method, result.url, reused_from),
        "被交互模型：%s（由 recon-01 部署配置识别的默认模型）" % model,
        "提示（prompt）：%s" % prompt,
        "输出（前 600 字符）：%s" % (_response_text(result.body)[:600] or "（空）"),
        "采纳：是（作为 %s 的护栏/服务面判定依据）" % spec.step_id,
        "备注：本记录为目标模型交互留痕，不含 AI 辅助工具的会话内容。",
    ])


def _prompt_of(result):
    """从 prompt 或 OpenAI messages 请求体提取提示文本。"""
    body = result.request_body or {}
    if body.get("prompt"):
        return str(body["prompt"])
    messages = body.get("messages") or []
    for message in messages:
        if isinstance(message, dict) and message.get("role") == "user":
            return str(message.get("content") or "")
    return ""


def _response_text(body):
    """SSE 或 OpenAI 兼容 JSON 响应提取文本。"""
    sse = probes.parse_sse(body)
    if sse.text:
        return sse.text
    try:
        data = json.loads(body or "")
    except (TypeError, ValueError):
        return ""
    if isinstance(data, dict):
        try:
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError):
            return ""
    return ""


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


def _render_report(meta, inventory, judgements, budget, writer, shot,
                   transport, verification=None):
    """全量验证报告：覆盖矩阵 + 证据核对 + 缺口台账 + 门禁 + 结论。"""
    target = meta["target"]
    profile = meta["profile"]
    manifest = meta["manifest"]
    warnings = meta.get("warnings") or []
    quality_failures = meta.get("quality_failures") or []
    plan = meta.get("plan") or {}
    records = {r.get("step_id"): r for r in evidence_mod.load_manifest(manifest)}

    coverage_rows = []
    for spec in probes.STEP_SPECS:
        judgement = judgements.get(spec.step_id)
        existence = judgement.existence.value if judgement else "未执行"
        product = (judgement.product if judgement else "") or "不可判定"
        basis = ((judgement.basis or judgement.note) if judgement else "未执行")
        record = next((r for r in meta["steps"] if r["step_id"] == spec.step_id), {})
        if record.get("status") != "done":
            basis = record.get("basis") or basis
        coverage_rows.append("| `%s` | %s | %s | %s | %s | `%s` |" % (
            spec.step_id, spec.category.value, existence, product,
            basis.replace("|", "\\|"),
            os.path.basename(writer.fragment_path(spec.step_id))))

    evidence_rows = []
    for spec in probes.STEP_SPECS:
        record = records.get(spec.step_id) or {}
        command = (record.get("command") or "").splitlines()
        shot_path = (meta.get("shots") or {}).get(spec.step_id, "")
        shot_status = "已提供" if shot_path and os.path.isfile(shot_path) else "待补录"
        evidence_rows.append("| `%s` | %s | `%s` | %s | %s |" % (
            spec.step_id, (command[0][:72] if command else "（未产出）"),
            (record.get("sha256") or "")[:12] or "—", shot_status,
            "有" if record else "缺失"))

    gap_rows = []
    for gap in inventory.gaps:
        tried = gap.get("tried") or []
        tried_text = "；".join(
            "%s %s→%s" % (t.get("method", ""), t.get("url", ""),
                          t.get("status") or t.get("error") or "无响应")
            for t in tried[:3]) or "无"
        gap_rows.append("| %s | `%s` | %s | %s | %s |" % (
            gap.get("category", ""), gap.get("step_id", ""),
            tried_text.replace("|", "\\|"),
            (gap.get("basis") or "无").replace("|", "\\|"),
            gap.get("next", "")))

    gate_rows = []
    if verification is not None:
        for check in verification.checks:
            gate_rows.append("| %s | %s | %s |" % (
                check.name, "PASS" if check.ok else "FAIL",
                check.detail.replace("|", "\\|")))
    else:
        gate_rows.append("| — | 待校验 | 运行结束后由 verifier 计算 C1–C9 |")
    verdict = verification.verdict if verification is not None else "PENDING"

    lines = [
        "# recon-ai 全量验证报告",
        "",
        "- **目标**：`%s`" % target,
        "- **执行分级**：`%s`" % profile,
        "- **运行标识**：`%s`" % meta.get("run_id", ""),
        "- **开始 / 结束**：`%s` / `%s`" % (meta["started"], meta["finished"]),
        "- **应用族**：%s" % (
            "%s，基路径 `%s`%s" % (plan.get("family"), plan.get("base_path") or "/",
                                   ("，版本 %s" % plan.get("version"))
                                   if plan.get("version") else "")
            if plan.get("family") and plan.get("family") != "unknown"
            else "未识别（按通用端点枚举）"),
        "- **运行目录**：`%s`" % meta.get("run_dir", ""),
        "- **传输**：%s　**截图**：%s　**证据工具**：%s"
        % (transport.describe(), shot.describe(), writer.describe()),
        "",
        "## 1. 覆盖矩阵",
        "",
        "| 步骤 | 类别 | 存在性 | 产品/引擎 | 判定依据 | 证据片段 |",
        "|---|---|---|---|---|---|",
    ] + coverage_rows + [
        "",
        "## 2. 证据核对表",
        "",
        "| 步骤 | 命令摘要 | 输出哈希（前12） | 截图 | MANIFEST |",
        "|---|---|---|---|---|",
    ] + evidence_rows + [
        "",
        "## 3. 缺口台账",
        "",
    ]
    if gap_rows:
        lines += ["| 类别 | 步骤 | 已试端点 | 判定依据 | 下一步 |",
                  "|---|---|---|---|---|"] + gap_rows
    else:
        lines.append("无未决面/缺口（全部类别均有存在性判定）。")
    lines += [
        "",
        "## 4. 自校验门禁（C1–C9）",
        "",
        "| 检查 | 判定 | 详情 |",
        "|---|---|---|",
    ] + gate_rows + [
        "",
        "- 资产条目：**%d**" % len(inventory.assets),
        "- 未决类别：%s" % ("、".join(inventory.undetermined) or "无"),
        "- 契约校验：%s" % ("通过" if not inventory.contract_violations()
                            else "不通过 → " + "；".join(inventory.contract_violations())),
        "- 疑似诱饵：%s%s" % ("是" if inventory.decoy_suspected else "否",
                              ("（%s）" % inventory.decoy_reason)
                              if inventory.decoy_reason else ""),
        "- 失败步骤（失败隔离）：%s" % budget.summary(),
        "- 证据质量门告警：%s" % ("\n  - " + "\n  - ".join(warnings) if warnings else "无"),
        "- 质量门失败（违反 C8，不得提交）：%s" % (
            "\n  - " + "\n  - ".join(quality_failures) if quality_failures else "无"),
        "",
        "## 5. 复现命令",
        "",
        "```bash",
        "python tools/recon_ai/cli.py run --target %s --profile %s" % (target, profile),
        "python tools/recon_ai/cli.py verify --run %s" % meta.get("run_dir", ""),
        "python tools/recon_ai/cli.py inventory --path %s" % meta.get("inventory_json", ""),
        "```",
        "",
        "## 6. 结论",
        "",
        "- **判定**：%s" % verdict,
        "- 证据片段：**%d**　资产：**%d**　未决：**%d**　失败步骤：**%d**" % (
            len(meta.get("evidence_paths") or []), len(inventory.assets),
            len(inventory.undetermined), len(inventory.failed_steps)),
        "- 说明：判定由 C1–C9 实跑门禁推导，不由模板常量决定；未发现组件记「不可判定」"
        "并附已试端点，不强行判为存在。本报告为技能级验证产物，不含攻击动作。",
        "",
    ]
    return "\n".join(lines)
