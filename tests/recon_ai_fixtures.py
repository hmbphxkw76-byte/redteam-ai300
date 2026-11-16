#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""recon-ai 闭环测试夹具：同构后端与 Streamlit 静态站两套确定性路由。"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tools.recon_ai import evidence, runner, shot  # noqa: E402
from tools.recon_ai.transport import FakeTransport, HttpResponse  # noqa: E402

TARGET_LEGACY = "http://t"
TARGET_STREAMLIT = "http://st.test"
TARGET_DVAA = "http://dvaa.test:9000"
SPA = "<!doctype html><html><body><div id='root'></div></body></html>"
SSE_OK = ('event: meta\ndata: {"request_id": "r-001", "lab_id": "MM_04", '
          '"phase": 3, "control_mode": "off", "artifact_replay": true}\n\n'
          'data: {"content": "RECON-PROBE-OK"}\n\n')
CONFIG = ('{"training_labs_enabled":false,"training_lab_ids":["MM_04"],'
          '"llm_model_default":"LongCat-2.5"}')


def legacy_routes(target=TARGET_LEGACY):
    return {
        ("GET", target + "/api/config"):
            HttpResponse(200, CONFIG, {"Server": "nginx/1.27.5"}, "application/json"),
        ("GET", target + "/v1/models"):
            HttpResponse(200, SPA, {}, "text/html"),
        ("POST", target + "/api/labs/MM_04/chat"):
            HttpResponse(200, SSE_OK, {"set-cookie": "aivp_sid=x"}, "text/event-stream"),
        ("GET", target + "/api/me/runs?limit=1"):
            HttpResponse(200, '{"runs":[]}', {}, "application/json"),
        ("GET", target + "/explore"):
            HttpResponse(200, '<!doctype html><script src="/assets/index-abc.js"></script>',
                         {}, "text/html"),
        ("GET", target + "/assets/index-abc.js"):
            HttpResponse(200, "var retrieved_knowledge=1;", {},
                         "application/javascript"),
        ("GET", target + "/api/labs/MM_05/summary"):
            HttpResponse(422, '{"detail":[{"loc":["query","request_id"]}]}',
                         {}, "application/json"),
        ("GET", target + "/api/labs/DE_01/summary"):
            HttpResponse(422, '{"detail":[{"loc":["query","request_id"],"msg":"required"}]}',
                         {}, "application/json"),
        ("POST", target + "/api/secrets/validate"):
            HttpResponse(200, '{"success":false,"message":"Nope."}', {},
                         "application/json"),
        ("GET", target + "/api/labs/MCP_01/summary"):
            HttpResponse(422, '{"detail":[{"loc":["query","request_id"]}]}',
                         {}, "application/json"),
    }


def streamlit_routes(target=TARGET_STREAMLIT):
    """静态报告站 + Streamlit 1.67.0 应用（基路径 /chat，未知路径 200 SPA 回退）。"""
    routes = {}
    for path in ("/api/config", "/v1/models", "/api/me/runs?limit=1",
                 "/explore", "/assets/index.js", "/api/labs/MM_05/summary",
                 "/api/labs/DE_01/summary", "/api/labs/MCP_01/summary"):
        routes[("GET", target + path)] = HttpResponse(200, SPA, {}, "text/html")
    routes[("POST", target + "/api/labs/MM_04/chat")] = HttpResponse(
        200, SPA, {}, "text/html")
    routes[("POST", target + "/api/secrets/validate")] = HttpResponse(
        200, SPA, {}, "text/html")
    routes.update({
        ("GET", target + "/"): HttpResponse(
            200, '<!doctype html><a href="/chat">AI Weekly</a>'
                 '<a href="/reports/2026-11-15_ai_weekly.html">report</a>',
            {}, "text/html"),
        ("GET", target + "/_stcore/health"): HttpResponse(
            404, '{"detail":"Not Found"}', {}, "application/json"),
        ("GET", target + "/chat/_stcore/health"): HttpResponse(
            200, "ok", {}, "text/plain"),
        ("GET", target + "/chat/"): HttpResponse(
            200, '<!doctype html><script src="./static/js/index.DormvYxC.js"></script>',
            {}, "text/html"),
        ("GET", target + "/chat/static/js/index.DormvYxC.js"): HttpResponse(
            200, "const version:`1.67.0`;", {}, "application/javascript"),
        ("GET", target + "/chat/_stcore/host-config"): HttpResponse(
            200, '{"allowedOrigins":[]}', {}, "application/json"),
        ("GET", target + "/chat/config"): HttpResponse(
            404, '{"detail":"Not Found"}', {}, "application/json"),
        ("GET", target + "/openapi.json"): HttpResponse(
            404, '{"detail":"Not Found"}', {}, "application/json"),
        ("GET", target + "/api/tags"): HttpResponse(
            404, '{"detail":"Not Found"}', {}, "application/json"),
    })
    return routes


def dvaa_routes(target=TARGET_DVAA):
    """DVAA 式多智能体靶场：/agents 清单 + 低门槛 agent 聊天 + MCP 工具面。"""
    agents = (
        '{"id":"securebot","name":"SecureBot","protocol":"api",'
        '"securityLevel":"hardened"},'
        '{"id":"helperbot","name":"HelperBot","protocol":"api",'
        '"securityLevel":"weak"},'
        '{"id":"toolbot","name":"ToolBot","protocol":"mcp",'
        '"securityLevel":"vulnerable","port":7011},'
        '{"id":"proxybot","name":"ProxyBot","protocol":"mcp",'
        '"securityLevel":"vulnerable","port":7012}'
    )
    chat = ('{"id":"chatcmpl-helperbot-1","object":"chat.completion",'
            '"model":"helperbot","choices":[{"index":0,"message":'
            '{"role":"assistant","content":"RECON-PROBE-OK"},'
            '"finish_reason":"stop"}]}')
    tools = '{"tools":[{"name":"exec_shell","vulnerable":true}]}'
    return {
        ("GET", target + "/"):
            HttpResponse(200, SPA, {}, "text/html"),
        ("GET", target + "/health"):
            HttpResponse(200, '{"status":"ok","agents":4}', {},
                         "application/json"),
        ("GET", target + "/agents"):
            HttpResponse(200, "[" + agents + "]", {}, "application/json"),
        ("GET", target + "/api/llm/status"):
            HttpResponse(200, '{"provider":"openai-compatible","model":"dvaa-llm"}',
                         {}, "application/json"),
        ("POST", target + "/api/agents/helperbot/chat"):
            HttpResponse(200, chat, {}, "application/json"),
        ("GET", "http://dvaa.test:7011/mcp/tools"):
            HttpResponse(200, tools,
                         {"Access-Control-Allow-Origin": "*"}, "application/json"),
        ("GET", "http://dvaa.test:7012/mcp/tools"):
            HttpResponse(200, tools,
                         {"Access-Control-Allow-Origin": "*"}, "application/json"),
    }


def run_fake(tmp, routes, target=TARGET_LEGACY, writer=None, shot_impl=None,
             out_dir=None):
    return runner.run_recon(
        target=target, out_dir=out_dir or tmp,
        transport=FakeTransport(routes),
        shot=shot_impl or shot.FakeShot(),
        writer=writer or evidence.EvidenceWriter(
            tmp, manifest=os.path.join(tmp, "MANIFEST.jsonl")),
        capture_shots=True,
    )
