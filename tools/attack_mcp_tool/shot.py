#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""截图缝（S3）：访问证明。无可用浏览器时降级为「待补录」，绝不伪造文件（AC-13）。

诚实语义：
  - `url`        目标页面直截（GET 面可代表）；
  - `transcript` 请求/响应转录页渲染（POST/JSON-RPC/SSE 面无法用 GET 截图代表），
                 页内含目标标识与时间戳，满足「访问证明」要求。
浏览器路径发现复用 `tools/recon_ai/shot.py::find_browser`（C1：同一事实只存一份）。
"""
import html
import os
import subprocess

from tools.recon_ai.shot import find_browser


def render_transcript(command, response_text, url="", timestamp="", title=""):
    """渲染含目标标识与时间戳的转录页（截图载体）。"""
    return """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>attack-mcp-tool transcript</title><style>
body{background:#0b1020;color:#e6edf3;font:13px/1.55 Consolas,Menlo,monospace;padding:24px}
h1{font-size:15px;color:#7dd3fc;margin:0 0 4px}
.meta{color:#94a3b8;margin-bottom:14px}
pre{background:#111827;border:1px solid #1f2937;border-radius:6px;padding:12px;white-space:pre-wrap;word-break:break-all}
.cmd{color:#a5f3fc}
</style></head><body>
<h1>%s</h1>
<div class="meta">目标：%s　|　时间戳：%s　|　MCP 工具面证据转录</div>
<pre class="cmd">%s</pre>
<pre>%s</pre>
</body></html>""" % (html.escape(title or "attack-mcp-tool 证据转录"), html.escape(url),
                     html.escape(timestamp), html.escape(command),
                     html.escape(response_text))


class ShotCapture:
    """截图协议：实现 `capture` 即可替换。"""

    def capture(self, step_id, target, out_dir, kind="transcript", command="",
                response="", timestamp=""):
        raise NotImplementedError

    def describe(self):
        return self.__class__.__name__


class NullCapture(ShotCapture):
    """不截图：证据里保留钩子命令，状态标「待补录」。"""

    def capture(self, step_id, target, out_dir, kind="transcript", command="",
                response="", timestamp=""):
        return "", ""

    def describe(self):
        return "none"


class FakeCapture(ShotCapture):
    """测试替身：写出最小 PNG 头，验证证据链不断裂。"""

    def capture(self, step_id, target, out_dir, kind="transcript", command="",
                response="", timestamp=""):
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, "%s-%s.png" % (step_id, kind))
        with open(path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")
        return path, kind

    def describe(self):
        return "fake"


class HeadlessCapture(ShotCapture):
    """无头浏览器截图：转录页先落盘再截，成功返回路径，失败返回空（不伪造）。"""

    def __init__(self, browser_path=None, budget_ms=8000, size="1280,1000"):
        self.browser = browser_path or find_browser()
        self.budget_ms = budget_ms
        self.size = size

    def describe(self):
        return "headless:%s" % (os.path.basename(self.browser) if self.browser else "none")

    def capture(self, step_id, target, out_dir, kind="transcript", command="",
                response="", timestamp=""):
        if not self.browser:
            return "", ""
        out_dir = os.path.abspath(out_dir)
        os.makedirs(out_dir, exist_ok=True)
        out = os.path.join(out_dir, "%s-%s.png" % (step_id, kind))
        tmp_html = ""
        page = target
        if kind == "transcript":
            tmp_html = os.path.join(out_dir, ".%s-transcript.html" % step_id)
            with open(tmp_html, "w", encoding="utf-8") as f:
                f.write(render_transcript(command, response, target, timestamp, step_id))
            page = "file:///" + tmp_html.replace("\\", "/").lstrip("/")
        argv = [self.browser, "--headless=new", "--disable-gpu", "--no-sandbox",
                "--hide-scrollbars", "--window-size=%s" % self.size,
                "--virtual-time-budget=%d" % self.budget_ms,
                "--screenshot=%s" % out, page]
        try:
            subprocess.run(argv, capture_output=True, timeout=120)
        except (OSError, subprocess.SubprocessError):
            return "", ""
        finally:
            if tmp_html and os.path.isfile(tmp_html):
                try:
                    os.remove(tmp_html)
                except OSError:
                    pass
        if os.path.isfile(out) and os.path.getsize(out) > 0:
            return out, kind
        return "", ""


def make_capture(enabled=True, browser_path=None):
    """工厂：启用且有浏览器 → 真实截图；否则 NullCapture（降级待补录）。"""
    if not enabled:
        return NullCapture()
    capture = HeadlessCapture(browser_path=browser_path)
    return capture if capture.browser else NullCapture()
