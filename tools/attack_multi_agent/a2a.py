#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""A2A 攻击客户端：总线/记忆/上下文/编排四类面的可执行动作（深层模块）。

全部构建于 `transport.HttpClient` 缝之上；无真实目标时不发请求（单测注入替身）。
命令渲染为可 copy/paste 的 curl（§6.1）；观测结果封装为 `Observation`。
外部主控（A2ASecBench/a2a-scanner）经 `scanner.py` 适配，不在本模块内硬耦合。
"""
import json
from typing import Optional

from .model import Observation, parse_topology
from .transport import HttpClient


def _curl(method, url, body=None):
    if body is None:
        return "curl -s -X %s '%s'" % (method, url)
    payload = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
    return ("curl -s -X %s '%s' -H 'Content-Type: application/json' -d '%s'"
            % (method, url, payload.replace("'", "'\\''")))


class A2ABusClient:
    """消息总线面：a2a-01 拓扑发现 / a2a-02 消息操纵 / a2a-03 智能体冒充。"""

    def __init__(self, client: HttpClient, bus_url: str):
        self.client = client
        self.bus = bus_url
        self.trusted = ()   # 拓扑发现得到的对端身份；空表示目标未声明

    # 拓扑发现候选端点：不同实现的 A2A 服务把对端清单放在不同路径。
    # 首个能解析出 agent/总线要素的响应即采用；全部失败时如实返回空拓扑。
    TOPOLOGY_PATHS = ("/topics", "/a2a/agents", "/a2a/topology", "/agents", "/info", "/")

    def discover_topology(self):
        attempts = []
        chosen = None
        for path in self.TOPOLOGY_PATHS:
            url = "%s%s" % (self.bus, path)
            resp = self.client.request("GET", url, timeout=15)
            topo = parse_topology(resp.body)
            attempts.append({"url": url, "status": resp.status, "error": resp.error,
                             "agent_count": topo.get("agent_count", 0),
                             "bus_present": bool(topo.get("bus_present"))})
            if topo.get("agent_count", 0) >= 1 or topo.get("bus_present"):
                chosen = (resp, topo, url)
                break
        if chosen is None:
            last = attempts[-1] if attempts else {}
            url = last.get("url", "%s/topics" % self.bus)
            resp = self.client.request("GET", url, timeout=15)
            topo = parse_topology(resp.body)
            return (Observation(raw=resp.body, text=resp.body, error=resp.error,
                                request={"method": "GET", "url": url},
                                telemetry={"topology": topo, "attempts": attempts}),
                    _curl("GET", url), topo)
        resp, topo, url = chosen
        self.trusted = tuple(topo.get("agents") or ())
        return (Observation(raw=resp.body, text=resp.body, error=resp.error,
                            request={"method": "GET", "url": url},
                            telemetry={"topology": topo, "attempts": attempts}),
                _curl("GET", url), topo)

    @staticmethod
    def _failed(resp):
        """端点不存在/未受理：用于决定是否改走下一形态。"""
        if resp.error:
            return True
        body = (resp.body or "").lower()
        return "not found" in body or "404" in body[:40]

    def inject_message(self, from_, to, payload):
        url = "%s/publish" % self.bus
        body = {"from": from_, "to": to, "body": payload}
        resp = self.client.request("POST", url, body=body, timeout=15)
        if self._failed(resp):
            alt = "%s/a2a/message" % self.bus
            body = {"from": from_, "to": to, "type": "task", "content": payload}
            resp = self.client.request("POST", alt, body=body, timeout=15)
            url = alt
        return Observation(raw=resp.body, text=resp.body, error=resp.error,
                           request={"method": "POST", "url": url, "body": body}), _curl("POST", url, body)

    def impersonate(self, spoof, cmd):
        url = "%s/agent/%s/cmd" % (self.bus, spoof)
        body = {"spoof": spoof, "cmd": cmd}
        resp = self.client.request("POST", url, body=body, timeout=15)
        if self._failed(resp):
            alt = "%s/a2a/message" % self.bus
            body = {"from": spoof, "to": "orchestrator", "type": "task", "content": cmd}
            resp = self.client.request("POST", alt, body=body, timeout=15)
            url = alt
        return Observation(raw=resp.body, text=resp.body, error=resp.error,
                           request={"method": "POST", "url": url, "body": body}), _curl("POST", url, body)


class MemoryStoreClient:
    """共享记忆/上下文面：a2a-04 共享记忆投毒 / a2a-05 上下文投毒。"""

    def __init__(self, client: HttpClient, store_url: str):
        self.client = client
        self.store = store_url

    def read_memory(self, key):
        url = "%s/get?key=%s" % (self.store, key)
        resp = self.client.request("GET", url, timeout=15)
        return resp.body, _curl("GET", url)

    def poison_memory(self, key, value):
        url = "%s/set" % (self.store)
        body = {"key": key, "value": value}
        resp = self.client.request("POST", url, body=body, timeout=15)
        return Observation(raw=resp.body, text=resp.body, error=resp.error,
                           request={"method": "POST", "url": url, "body": body}), _curl("POST", url, body)

    def poison_context(self, endpoint, injection):
        url = endpoint
        body = {"inject": injection}
        resp = self.client.request("POST", url, body=body, timeout=15)
        return Observation(raw=resp.body, text=resp.body, error=resp.error,
                           request={"method": "POST", "url": url, "body": body}), _curl("POST", url, body)


class OrchestratorClient:
    """编排面：a2a-06 工作流破坏 / a2a-07 下游决策影响取证。"""

    def __init__(self, client: HttpClient, orchestrator_url: str):
        self.client = client
        self.orch = orchestrator_url

    def disrupt_workflow(self, task):
        url = "%s/task" % self.orch
        body = {"task": task}
        resp = self.client.request("POST", url, body=body, timeout=15)
        return Observation(raw=resp.body, text=resp.body, error=resp.error,
                           request={"method": "POST", "url": url, "body": body}), _curl("POST", url, body)

    def get_trace(self, run_id):
        url = "%s/trace" % self.orch
        body = {"run": run_id}
        resp = self.client.request("POST", url, body=body, timeout=15)
        return Observation(raw=resp.body, text=resp.body, error=resp.error,
                           request={"method": "POST", "url": url, "body": body}), _curl("POST", url, body)
