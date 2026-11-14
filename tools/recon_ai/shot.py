#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""访问证明截图（seam S3 的可替换实现）。

官方要求每步附截图证明（§6.1）。本模块提供两种诚实语义：
  - `url`        ：目标页面直截（GET 面）；
  - `transcript` ：请求/响应转录页渲染（POST/SSE 面无法用 GET 截图代表）。

未安装浏览器时返回空路径并在证据中记「截图待补录」，绝不伪造。
"""
import html
import os
import shutil
import subprocess

CANDIDATES = (
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
)


def find_browser():
    """定位无头浏览器；环境变量 RECON_AI_BROWSER 优先。"""
    env = os.environ.get("RECON_AI_BROWSER")
    if env and os.path.isfile(env):
        return env
    for path in CANDIDATES:
        if os.path.isfile(path):
            return path
    for name in ("msedge", "chrome", "chromium", "google-chrome"):
        found = shutil.which(name)
        if found:
            return found
    return ""


def render_transcript(command, response_text, url=""):
    """把「命令 + 原始响应」渲染为可截图的 HTML（POST/SSE 证据的诚实载体）。"""
    return """<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>recon-ai transcript</title><style>
body{background:#0b1020;color:#e6edf3;font:13px/1.55 Consolas,Menlo,monospace;padding:24px}
h1{font-size:15px;color:#7dd3fc;margin:0 0 4px}
.meta{color:#94a3b8;margin-bottom:14px}
pre{background:#111827;border:1px solid #1f2937;border-radius:6px;padding:12px;white-space:pre-wrap;word-break:break-all}
.cmd{color:#a5f3fc}.resp{color:#e5e7eb}
</style></head><body>
<h1>recon-ai 证据转录（POST/SSE 端点）</h1>
<div class="meta">目标：%s</div>
<pre class="cmd">%s</pre>
<pre class="resp">%s</pre>
</body></html>""" % (html.escape(url), html.escape(command), html.escape(response_text))


class ShotCapture:
    """截图协议：子类实现 `capture`。"""

    def capture(self, step_id, url, out_dir, kind="url", command="", response=""):
        raise NotImplementedError

    def describe(self):
        return self.__class__.__name__


class NullShot(ShotCapture):
    """不截图：证据里保留钩子命令，状态标「待补录」。"""

    def capture(self, step_id, url, out_dir, kind="url", command="", response=""):
        return "", ""

    def describe(self):
        return "none"


class FakeShot(ShotCapture):
    """测试替身：写出最小 PNG 头，验证证据链不断裂。"""

    def capture(self, step_id, url, out_dir, kind="url", command="", response=""):
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, "%s-%s.png" % (step_id, kind))
        with open(path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n")
        return path, kind

    def describe(self):
        return "fake"


class HeadlessShot(ShotCapture):
    """无头浏览器截图：url 面直截，POST 面渲染转录页后再截。"""

    def __init__(self, browser_path=None, budget_ms=8000, size="1280,900"):
        self.browser = browser_path or find_browser()
        self.budget_ms = budget_ms
        self.size = size

    def describe(self):
        return "headless:%s" % (os.path.basename(self.browser) if self.browser else "none")

    def capture(self, step_id, url, out_dir, kind="url", command="", response=""):
        if not self.browser:
            return "", ""
        out_dir = os.path.abspath(out_dir)
        os.makedirs(out_dir, exist_ok=True)
        target = url
        tmp_html = ""
        if kind == "transcript":
            tmp_html = os.path.join(out_dir, ".%s-transcript.html" % step_id)
            with open(tmp_html, "w", encoding="utf-8") as f:
                f.write(render_transcript(command, response, url))
            target = "file:///" + tmp_html.replace("\\", "/").lstrip("/")
        out = os.path.abspath(os.path.join(out_dir, "%s-%s.png" % (step_id, kind)))
        cmd = [self.browser, "--headless=new", "--disable-gpu", "--no-sandbox",
               "--hide-scrollbars", "--window-size=%s" % self.size,
               "--virtual-time-budget=%d" % self.budget_ms,
               "--screenshot=%s" % out, target]
        try:
            subprocess.run(cmd, capture_output=True, timeout=120)
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


def make_shot(enabled=True, browser_path=None):
    """工厂：启用且有浏览器 → 真实截图；否则 NullShot（不伪造）。"""
    if not enabled:
        return NullShot()
    shot = HeadlessShot(browser_path=browser_path)
    return shot if shot.browser else NullShot()
