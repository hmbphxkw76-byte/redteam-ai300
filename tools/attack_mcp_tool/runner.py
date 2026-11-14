#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""编排与唯一公开入口 `run_attack`（深层模块）。

职责：按 SKILL.md 顺序分发步骤 → 经注入的缝执行 → 纯函数定级
→ 每步 1:1 落盘证据片段 → 汇总 AttackReport。

不夸大（对齐 SKILL.md「失败与豁免」）：
  - 能力缺失记「已跳过」并附依据；
  - 被护栏拦截记「未生效」并记录拦截原因，不重试同一动作；
  - 「本地投毒自证」与「目标 agent 被操纵」分开表述。
"""
import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, Optional, Tuple

from . import grade as grading
from . import poison
from .evidence import EvidenceWriter
from .mcp import AgentSseClient, JsonRpcMcpClient, site_base
from .model import (AttackReport, AttackRequest, Observation, Signals, StepVerdict,
                    parse_scope_map, parse_surface_from_text)
from .shot import make_capture
from .steps import PROMPT_ADMIN_LOGS, StepSpec, steps_for_paths
from .transport import HttpClient, UrllibHttpClient

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_EVIDENCE_DIR = os.path.join(ROOT, "evidence", "attack-mcp-tool")

# 对象图（B7 / ADR-0004）：声明式记录，不在运行时导入模型框架
OBJECT_GRAPH: Dict[str, Any] = {
    "framework": "pyrit==1.1.0",
    "target": "HTTPTarget",
    "scorer": "SubStringScorer",
    "strategy": "（MCP 无专用攻击策略，以 HTTPTarget + 回调对接）",
    "memory": "—",
    "notes": "工具面为 HTTP JSON-RPC / SSE；判据为敏感值形态 + 目标侧遥测，无 LLM judge",
}


def _now():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _curl(method, url, body=None):
    """把真实请求渲染为可直接 copy/paste 的命令（§6.1）。"""
    if body is None:
        return "curl -sN -X %s '%s'" % (method, url)
    payload = json.dumps(body, ensure_ascii=False)
    return ("curl -sN -X %s '%s' -H 'Content-Type: application/json' -d '%s'"
            % (method, url, payload.replace("'", "'\\''")))


@dataclass
class Runtime:
    """三缝的注入点集合：默认全为生产实现；单测注入替身即离线（AC-17）。"""

    client: HttpClient = field(default_factory=UrllibHttpClient)
    writer: Any = None
    capture: Any = None
    server: Optional[poison.PoisonedMcpServer] = None
    browser_path: Optional[str] = None
    shot_enabled: bool = True
    prompt_for: Optional[Callable[[StepSpec], str]] = None

    def __post_init__(self):
        if self.capture is None:
            self.capture = make_capture(self.shot_enabled, self.browser_path)


@dataclass
class _StepOutcome:
    """一步的执行结果（进入定级前的原料）。"""

    observation: Observation
    ctx: Dict[str, Any] = field(default_factory=dict)
    command: str = ""
    ai_log: str = ""
    note: str = ""
    flag_panel: str = ""
    flag_shot: str = ""
    response_for_shot: str = ""


class _Session:
    """一次运行的执行上下文（持有客户端与中间结果）。"""

    def __init__(self, request: AttackRequest, runtime: Runtime):
        self.request = request
        self.runtime = runtime
        self.target = request.target
        self.mode = request.mode
        self.agent = AgentSseClient(runtime.client, request.target)
        self.rpc = JsonRpcMcpClient(runtime.client, request.target)
        self.out_dir = request.evidence_dir or DEFAULT_EVIDENCE_DIR
        self.manifest = os.path.join(self.out_dir, "manifest.jsonl")
        self.last_secret = ""
        self.secrets_seen = []   # 同一运行内已实测到的凭据（含来源 step/lab，供 flag 步溯源）
        self.server_started = False
        self.started_server: Optional[poison.PoisonedMcpServer] = None
        self._writer = runtime.writer

    # —— 工具 ——
    def lab(self, spec):
        return spec.lab or (self.request.labs[0] if self.request.labs else "MCP_01")

    def prompt(self, spec):
        if self.runtime.prompt_for is not None:
            return self.runtime.prompt_for(spec)
        return spec.prompt

    def ensure_server(self):
        if self.started_server is not None:
            return self.started_server
        server = self.runtime.server or poison.PoisonedMcpServer()
        server.start()
        self.started_server = server
        self.server_started = True
        return server

    def close(self):
        if self.started_server is not None:
            self.started_server.stop()
            self.started_server = None

    # —— 两种形态的原子动作 ——
    def probe(self, spec):
        """agent 会话形态：发提示词，取回合观测。"""
        lab = self.lab(spec)
        turn = self.agent.probe(lab, self.prompt(spec))
        obs = Observation(
            raw="\n".join(ev.raw for ev in turn.events) or turn.text,
            text=turn.text,
            tool_result=(turn.first_result.tool_result if turn.first_result else ""),
            telemetry=turn.telemetry(),
            request=turn.request_body,
            error=turn.error)
        return obs, _curl("POST", self.agent.url_for(lab), turn.request_body)

    def probe_raw(self, lab, prompt):
        """按显式 lab + 提示词发一次会话（用于「改走其它提权路径」）。"""
        turn = self.agent.probe(lab, prompt)
        obs = Observation(
            raw="\n".join(ev.raw for ev in turn.events) or turn.text,
            text=turn.text,
            tool_result=(turn.first_result.tool_result if turn.first_result else ""),
            telemetry=turn.telemetry(), request=turn.request_body, error=turn.error)
        return obs, _curl("POST", self.agent.url_for(lab), turn.request_body)

    def rpc_call(self, tool, arguments=None, client=None):
        client = client or self.rpc
        obs = client.call_tool(tool, arguments or {})
        return obs, _curl("POST", client.endpoint, obs.request)


def _render(obs):
    """证据「关键输出」：可读的拼接结果 + 原始响应 + 工具结果与遥测。

    原始响应必留（复核锚点）；若为 SSE 分片流，另附拼接后的回答以利阅读，
    两者同源，读者可逐行比对。
    """
    parts = []
    if obs.error:
        parts.append("[错误] %s" % obs.error)
    if obs.text and obs.raw:
        parts.append("[拼接后的回答（由下列原始事件拼接）]\n%s" % obs.text)
    if obs.raw:
        parts.append("[原始响应]\n%s" % obs.raw)
    if obs.tool_result and obs.tool_result not in (obs.raw or ""):
        parts.append("[tool_result]\n%s" % obs.tool_result)
    if obs.telemetry:
        parts.append("[mcp_telemetry]\n%s" % json.dumps(obs.telemetry, ensure_ascii=False, indent=1))
    return "\n\n".join(parts)


def _guardrail_baseline(obs):
    """记录可观察的护栏基线（工具白名单/权限校验/输出审查），供后续对照。"""
    tele = (obs.telemetry or {}) if obs else {}
    if not tele:
        return ""
    return ("策略决定=%s；所需权限=%s；影响半径=%s；需用户同意=%s；"
            "工具白名单=%s" % (
                tele.get("policy_decision", "未声明"),
                ",".join(tele.get("permissions_used") or []) or "未声明",
                tele.get("blast_radius", "未声明"),
                tele.get("user_consent_required", "未声明"),
                "未提供（agent 仅暴露 %s）" % (tele.get("selected_tool") or "—")))


def _ai_log(spec, obs, level, prompted=False):
    """仅在**本步真的向目标模型发过提示**时产出；否则返回空串（禁止跨步臆造）。"""
    if not prompted or not spec.prompt:
        return ""
    tele = obs.telemetry or {}
    return ("prompt: %s\nmodel: 目标部署默认模型（见 /api/config）\n"
            "output: %s\n工具调用: %s\nverdict: %s\n"
            "adoption: 证据如实记录，未夸大效果等级；被护栏拦截时记录原因不重试"
            % (spec.prompt.replace("\n", " | "),
               (obs.text or "").replace("\n", " ")[:400],
               tele.get("selected_tool") or "（无工具调用）", level))


def _step_mcp_01(sess, spec):
    if sess.mode == "jsonrpc":
        surface, obs = sess.rpc.list_tools()
        cmd = _curl("POST", sess.rpc.endpoint,
                    {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        ctx = {"tool_count": len(surface.tools)}
        if not surface.tools and obs.error:
            ctx["capability_missing"] = True
            ctx["missing_reason"] = "tools/list 未返回工具：%s" % obs.error
    else:
        obs, cmd = sess.probe(spec)
        surface = parse_surface_from_text(obs.text)
        ctx = {"tool_count": len(surface.tools)}
        if obs.error:
            ctx["capability_missing"] = True
            ctx["missing_reason"] = "agent 会话不可用：%s" % obs.error
        elif not surface.tools:
            ctx["capability_missing"] = True
            ctx["missing_reason"] = "目标未暴露可识别工具面（回答中无工具声明）"
    ctx["prompted"] = bool(spec.prompt) and not obs.error
    baseline = _guardrail_baseline(obs)
    note = ("护栏基线：%s" % baseline) if baseline else ""
    if ctx.get("capability_missing"):
        note = ("%s\n\n**改走他路判定**：无 MCP 工具面，按 SKILL「失败与豁免」"
                "改走 D3（attack-ai-agent）或 D5（attack-rag）；若连续两台主机均为 0 分"
                "无工具面，判定疑似诱饵机并在 30 分钟内结束，不空耗。" %
                (note or "—"))
    return _StepOutcome(observation=obs, ctx=ctx, command=cmd, note=note,
                        response_for_shot=_render(obs))


def _step_mcp_02(sess, spec):
    try:
        server = sess.ensure_server()
    except OSError as exc:
        return _StepOutcome(observation=Observation(error=str(exc)),
                            ctx={"capability_missing": True,
                                 "missing_reason": "本地端口不可用：%s" % exc},
                            command="python tools/serve_malicious_mcp.py --host 127.0.0.1 --port 0")
    client = JsonRpcMcpClient(sess.runtime.client, server.url)
    surface, obs = client.list_tools()
    poisoned = any(poison.POISON_INSTRUCTION in t.description for t in surface.tools)
    cmd = _curl("POST", client.endpoint,
                {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    note = ("本地恶意 server 已在 %s 提供 %d 个工具（含隐藏指令与放大后的权限声明）。"
            % (server.url, len(surface.tools)))
    local_only = sess.mode != "jsonrpc"
    if local_only:
        note += ("目标 agent 无第三方 server 注册/接入面，故「目标被诱导接入」不可执行；"
                 "效果等级按「仅本地自证」封顶为部分生效，不夸大。")
    return _StepOutcome(observation=obs, command=cmd,
                        ctx={"served": bool(surface.tools), "poisoned": poisoned,
                             "local_only": local_only, "target_integrated": False,
                             "shot_target": server.url},
                        note=note, response_for_shot=_render(obs))


def _step_mcp_03(sess, spec):
    base, poisoned = poison.baseline_surface(), poison.poisoned_surface()
    before = base.by_name("read_file")
    after = poisoned.by_name("read_file")
    changed = bool(before and after and before.description != after.description)
    injection = bool(after and poison.POISON_INSTRUCTION in after.description)
    inflated = bool(before and after and before.scope != after.scope)
    output = json.dumps([t.as_dict() for t in poisoned.tools], ensure_ascii=False, indent=1)
    if sess.mode == "jsonrpc":
        client = JsonRpcMcpClient(sess.runtime.client, (sess.ensure_server().url))
        surface, obs = client.list_tools()
        cmd = _curl("POST", client.endpoint,
                    {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
        output = _render(obs)
    else:
        obs, cmd = sess.probe(spec)
        output += "\n\n[目标侧观测] 工具面 %s 的信任级别：%s\n%s" % (
            sess.lab(spec), (obs.telemetry or {}).get("trust_level", "未声明"),
            (obs.text or "")[:400])
    local_only = sess.mode != "jsonrpc"
    note = ("描述注入隐藏指令 + 权限声明由 read 放大为 admin；"
            "目标侧同类失效点见 MCP_03/MCP_12（untrusted 描述被采纳）。")
    if local_only:
        note += "目标侧未被操纵，等级封顶为部分生效。"
    return _StepOutcome(observation=obs, command=cmd,
                        ctx={"descriptor_changed": changed, "injection_present": injection,
                             "scope_inflated": inflated, "local_only": local_only,
                             "target_integrated": False,
                             "shot_target": (sess.started_server.url
                                             if sess.started_server else sess.target)},
                        note=note, response_for_shot=output)


def _step_mcp_04(sess, spec):
    diff = poison.diff_as_dict(poison.diff_surfaces(
        poison.baseline_surface(), poison.poisoned_surface()))
    output = ("[投毒前]\n%s\n\n[投毒后]\n%s\n\n[差分]\n%s" % (
        json.dumps([t.as_dict() for t in poison.baseline_surface().tools],
                   ensure_ascii=False, indent=1),
        json.dumps([t.as_dict() for t in poison.poisoned_surface().tools],
                   ensure_ascii=False, indent=1),
        json.dumps(diff, ensure_ascii=False, indent=1)))
    cmd = ("python tools/serve_malicious_mcp.py --dump-poison-diff")
    local_only = sess.mode != "jsonrpc"
    note = ("前后对照：新增 %d 个工具，改写 %d 个工具的描述/权限字段。"
            % (len(diff["added"]), len(diff["changed"])))
    if local_only:
        note += ("对照来源为我方 server 的基线与投毒版本；目标会话无可注入 server 面，"
                 "故仅为技术自证，等级封顶为部分生效。")
    return _StepOutcome(observation=Observation(text=output, tool_result=output),
                        command=cmd,
                        ctx={"diff": diff, "local_only": local_only,
                             "target_integrated": False},
                        note=note, response_for_shot=output)


def _step_mcp_05(sess, spec):
    if sess.mode == "jsonrpc":
        obs, cmd = sess.rpc_call(spec.tool, {"cmd": "id; whoami"})
        executed = not obs.error
    else:
        obs, cmd = sess.probe(spec)
        executed = bool((obs.telemetry or {}).get("selected_tool"))
    if obs.secrets:
        sess.last_secret = obs.secrets[0]
    return _StepOutcome(observation=obs, command=cmd,
                        ctx={"tool_executed": executed, "prompted": True,
                             "lab": sess.lab(spec)},
                        note="以合法工具（run_command，scope=write）执行边界外命令；"
                             "回显为空时按「执行未取得回显」记录，不夸大。",
                        response_for_shot=_render(obs))


def _step_mcp_06(sess, spec):
    if sess.mode == "jsonrpc":
        return _StepOutcome(
            observation=Observation(text="裸 JSON-RPC 形态无中间人位置"),
            ctx={"capability_missing": True,
                 "missing_reason": ("裸 JSON-RPC 直连无中间人位置，无法构造「替换返回值」式劫持；"
                                    "劫持验证须在 agent 会话形态（含模型决策环节）进行")},
            command="（不适用：直连调用不构成劫持，改由 agent 形态验证）")
    obs, cmd = sess.probe(spec)
    tele = obs.telemetry or {}
    invoked = tele.get("selected_tool") == spec.tool
    blocked = not invoked
    reason = ""
    if blocked:
        text = (obs.text or "").strip().replace("\n", " ")
        reason = ("目标未执行注入的调用块；agent 回应摘要：%s"
                  % (text[:160] or "（无文本）"))
    return _StepOutcome(observation=obs, command=cmd,
                        ctx={"tool_invoked": invoked, "guard_blocked": blocked,
                             "blocked_reason": reason, "prompted": True,
                             "attacker_args_effective": False},
                        note=("护栏拒绝后按「不重试同一被拦截动作」终止该路径，"
                              "改由 mcp-07 提权路径继续。" if blocked
                              else "注入调用被目标执行，构成调用劫持。"),
                        response_for_shot=_render(obs))


def _step_mcp_07(sess, spec):
    """提权：先试 admin 动作；被 agent 自审拒绝时改走**另一条** admin 工具路径。

    SKILL.md「失败与豁免」：被护栏拦截须记录原因并改走其它提权路径，
    不得反复重试同一被拦截动作。因此备选路径是**不同的 lab 与工具**，
    且首个成功即停。
    """
    if sess.mode == "jsonrpc":
        obs, cmd = sess.rpc_call("admin_action", {"action": "status"})
        admin = '"admin": true' in (obs.tool_result or "").replace("True", "true")
        return _StepOutcome(
            observation=obs, command=cmd,
            ctx={"tool_name": "admin_action", "admin_confirmed": admin,
                 "scope_map": {"admin_action": "admin"}},
            note="本地对照组：scope=admin 的工具在无授权校验下被执行。",
            response_for_shot=_render(obs))

    routes = (
        ("MCP_08", PROMPT_ADMIN_LOGS, "read_logs"),
        ("MCP_02", spec.prompt, "elevated_action"),
    )
    attempts, chosen = [], None
    for lab, prompt, tool in routes:
        obs, cmd = sess.probe_raw(lab, prompt)
        tele = obs.telemetry or {}
        executed = tele.get("selected_tool") == tool
        attempts.append({"lab": lab, "tool": tool, "executed": executed,
                         "policy": tele.get("policy_decision", ""),
                         "text": (obs.text or "")[:300], "obs": obs, "cmd": cmd})
        if executed:
            chosen = attempts[-1]
            break
    rendered = []
    for i, a in enumerate(attempts, 1):
        rendered.append("[尝试 %d] %s → %s（执行=%s，策略=%s）\n命令：%s\n响应：\n%s" % (
            i, a["lab"], a["tool"], a["executed"], a["policy"] or "未返回", a["cmd"],
            _render(a["obs"])))
    output = "\n\n".join(rendered)
    if chosen is None:
        note = ("两条 admin 级路径均被 agent 侧授权校验拒绝（非工具策略放行），"
                "按「不重试同一动作」终止；记录拒绝理由作为负结果。")
        return _StepOutcome(observation=attempts[-1]["obs"],
                            command=attempts[-1]["cmd"],
                            ctx={"tool_name": attempts[-1]["tool"],
                                 "admin_confirmed": False, "prompted": True},
                            note=note, response_for_shot=output)
    obs = chosen["obs"]
    if obs.secrets:
        sess.last_secret = obs.secrets[0]
    note = ("%s 的 %s 被判 allowed 且执行成功（管理员级结果直接回显）；"
            "共尝试 %d 条路径，首个成功即停。" % (chosen["lab"], chosen["tool"],
                                                 len(attempts)))
    return _StepOutcome(observation=obs, command=chosen["cmd"],
                        ctx={"tool_name": chosen["tool"], "admin_confirmed": True,
                             "prompted": True, "lab": chosen["lab"],
                             "scope_map": {chosen["tool"]: "admin"}},
                        note=note, response_for_shot=output)


def _probe_flag_file(sess):
    """实测 flag 文件是否存在：以站根 index.html 尺寸为 SPA 回退基线判据。"""
    base = site_base(sess.target)
    if sess.mode == "jsonrpc":
        return False, "本地对照组无站点根，flag 文件通道不适用"
    root = sess.runtime.client.request("GET", base + "/", timeout=15)
    if root.error:
        return False, ("站根不可达，无法探测 ai_vector.txt / proof.txt，"
                       "flag 文件通道不可判定：%s" % root.error)
    baseline = len(root.body or "")
    for name in ("/ai_vector.txt", "/proof.txt", "/static/ai_vector.txt"):
        resp = sess.runtime.client.request("GET", base + name, timeout=15)
        if resp.error:
            continue
        body = resp.body or ""
        spa_hit = (resp.status == 200 and "html" in (resp.content_type or "")
                   and len(body) == baseline)
        if resp.status == 200 and not spa_hit:
            return True, "命中 %s（%d 字节，非 SPA 回退）" % (name, len(body))
    return False, ("探测 /ai_vector.txt、/proof.txt、/static/ai_vector.txt 均命中 "
                   "SPA 回退（200 + %d 字节 index.html），判定该文件不存在" % baseline)


def _step_mcp_08(sess, spec):
    if sess.mode == "jsonrpc":
        return _StepOutcome(
            observation=Observation(text="本地恶意 server 无 flag 语义"),
            ctx={"capability_missing": True,
                 "missing_reason": "本地对照组不含 flag 交付物，flag 步骤仅对演练目标执行"},
            command="（不适用：本地对照组无 flag 语义）")
    obs, cmd = sess.probe(spec)
    found, file_detail = _probe_flag_file(sess)
    # 优先用本步自己的观测；自身无值时，采用同一运行中先前的实测值并**显式标注来源**
    secret, origin = (obs.secrets[0], "本步") if obs.secrets else ("", "")
    if not secret and sess.secrets_seen:
        prior = sess.secrets_seen[-1]
        secret = prior["value"]
        origin = "%s（lab=%s）" % (prior["step"], prior["lab"])
    if not secret:
        return _StepOutcome(observation=obs, command=cmd,
                            ctx={"capability_missing": True, "prompted": True,
                                 "missing_reason": "本步未取得可验证值，无法构成双通道",
                                 "flag_reason": file_detail},
                            note=("flag 通道不可得：%s。无可用值时不伪造 flag。" % file_detail),
                            response_for_shot=_render(obs))
    origin_lab = sess.lab(spec)
    if origin != "本步":
        origin_lab = origin.split("lab=")[-1].rstrip("）")
    ok, raw = sess.agent.validate(origin_lab, secret)
    obs2 = Observation(raw=raw, text=obs.text, tool_result=obs.tool_result,
                       telemetry=obs.telemetry, request=obs.request)
    if found:
        reason = "目标存在 flag 文件，按官方双通道取证"
    else:
        reason = ("%s；以面板校验预言机 success=%s 作为等价双通道" % (file_detail, ok))
    note = ("flag 通道：%s。面板提交值 == 正文回显值 ==%s" % (reason, secret))
    if origin != "本步":
        note += ("\n\n**值来源**：本步未取得新值，采用同一运行中 `%s` 的实测值，"
                 "并以该来源 lab 的面板校验；未跨运行、未编造。" % origin)
    if not ok:
        note += ("\n\n**注意**：面板校验未通过，本条不构成双通道一致，"
                 "不得作为取分依据，仅记录值为部分生效。")
    return _StepOutcome(
        observation=obs2, command=cmd,
        ctx={"oracle_success": ok, "flag_value": secret, "flag_file_found": found,
             "flag_reason": reason, "prompted": True, "lab": origin_lab},
        note=note,
        flag_panel=secret if ok else "",
        flag_shot=secret if ok else "",
        response_for_shot=_render(obs) + "\n\n[flag 文件探测]\n" + file_detail
                            + "\n\n[面板校验]\n" + raw)


_HANDLERS = {
    "mcp-01": _step_mcp_01,
    "mcp-02": _step_mcp_02,
    "mcp-03": _step_mcp_03,
    "mcp-04": _step_mcp_04,
    "mcp-05": _step_mcp_05,
    "mcp-06": _step_mcp_06,
    "mcp-07": _step_mcp_07,
    "mcp-08": _step_mcp_08,
}


def _emit(sess, spec, outcome, level, reason, timestamp):
    """每步 1:1 落盘证据（B4 / §6.1），严格模式三件套不全即失败。"""
    writer = sess._writer
    if writer is None:
        writer = EvidenceWriter(sess.out_dir, manifest=sess.manifest)
        sess._writer = writer
    shot_target = outcome.ctx.get("shot_target") or sess.target
    shot_path, shot_kind = sess.runtime.capture.capture(
        spec.step_id, shot_target, sess.out_dir, kind="transcript",
        command=outcome.command, response=outcome.response_for_shot, timestamp=timestamp)
    shot_cmd = ("msedge --headless=new --window-size=1280,1000 --screenshot=%s "
                "<转录页 %s.html>" % (os.path.join(sess.out_dir, "%s-transcript.png" % spec.step_id),
                                     spec.step_id))
    note = "**效果等级**：%s　|　**依据**：%s" % (level, reason)
    if shot_target != sess.target:
        note = ("**本步实际端点**：`%s`（本次运行目标：`%s`）\n\n" % (shot_target, sess.target)) + note
    if not shot_path:
        # 未取到截图时显式降级：共享工具只能看到钩子命令，故此处补写状态，避免读者误判（AC-13）
        note = ("**截图待补录**（未检测到可用无头浏览器）：请按下列钩子命令补录，"
                "严禁伪造截图文件。\n\n" + note)
    if outcome.note:
        note += "\n\n" + outcome.note
    ai_log = _ai_log(spec, outcome.observation, level,
                     prompted=bool(outcome.ctx.get("prompted")))
    path, code, err = writer.emit(
        step_id=spec.step_id, command=outcome.command,
        output=outcome.response_for_shot or _render(outcome.observation),
        target=shot_target, title=spec.title, screenshot=shot_path,
        shot_kind=shot_kind, shot_cmd=shot_cmd, profile=sess.mode,
        note=note, ai_log=ai_log, flag_panel=outcome.flag_panel,
        flag_shot=outcome.flag_shot, strict=True)
    if code != 0:
        raise RuntimeError("证据质量门未通过：%s → %s" % (spec.step_id, err))
    return path


def run_attack(request: AttackRequest, runtime: Optional[Runtime] = None,
               paths=None, emit=None) -> AttackReport:
    """唯一公开入口。

    参数：
      request  目标、形态、lab 列表、步骤选择、证据输出目录
      runtime  三缝注入点（默认生产实现；单测注入替身即离线）
      paths    覆盖 request.paths（便捷参数）
      emit     覆盖 request.emit（便捷参数）
    返回 AttackReport。单步异常收敛为「未生效/已跳过」，不中断整轮；
    证据质量门失败则抛出 RuntimeError（证据链断裂不得静默）。
    """
    runtime = runtime or Runtime()
    if paths is not None:
        request = AttackRequest(target=request.target, mode=request.mode,
                                labs=request.labs, paths=tuple(paths),
                                step=request.step, evidence_dir=request.evidence_dir,
                                emit=request.emit)
    do_emit = request.emit if emit is None else emit
    sess = _Session(request, runtime)
    specs = steps_for_paths(request.paths, request.step)
    verdicts = []
    try:
        for spec in specs:
            timestamp = _now()
            try:
                outcome = _HANDLERS[spec.step_id](sess, spec)
            except RuntimeError:
                raise
            except Exception as exc:  # noqa: BLE001 - 单步失败不中断整轮
                outcome = _StepOutcome(
                    observation=Observation(error=str(exc)),
                    ctx={"execution_error": True, "execution_error_detail": str(exc)},
                    command="（执行异常，见注记）")
            for value in outcome.observation.secrets:
                sess.secrets_seen.append({"step": spec.step_id,
                                          "lab": outcome.ctx.get("lab") or sess.lab(spec),
                                          "value": value})
            signals: Signals = grading.derive(spec.step_id, outcome.observation, outcome.ctx)
            level, reason = grading.grade(signals)
            path = ""
            if do_emit:
                path = _emit(sess, spec, outcome, level, reason, timestamp)
            verdicts.append(StepVerdict(
                step_id=spec.step_id, path=spec.path, title=spec.title, level=level,
                reason=reason, command=outcome.command,
                observation=outcome.observation, evidence_path=path))
    finally:
        sess.close()
    return AttackReport(request=request, backend=runtime.client.describe(),
                        verdicts=tuple(verdicts), object_graph=dict(OBJECT_GRAPH))
