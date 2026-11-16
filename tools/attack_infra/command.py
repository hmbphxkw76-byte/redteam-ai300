#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""seam ②：外部命令执行（唯一命令出口）。

命令以**参数列表**传递，`subprocess.run` 固定 `shell=False`（AC-10），避免注入面与引号地狱。
命令不存在返回 `code=127`、`stderr="not found: <argv0>"`，由上层判
`ABSENT(reason=no_tool)`；超时返回 `code=-1`。均不抛异常（设计记录 §2）。
"""
import os
import subprocess
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class CommandResult:
    code: int = 0
    stdout: str = ""
    stderr: str = ""
    elapsed_ms: int = 0
    argv: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return self.code == 0

    @property
    def combined(self) -> str:
        return (self.stdout or "") + (("\n" + self.stderr) if self.stderr else "")


class Command:
    """执行协议（duck typing）。"""

    def run(self, argv, timeout=60, env=None):
        raise NotImplementedError

    def describe(self) -> str:
        return self.__class__.__name__


class SubprocessCommand(Command):
    """生产实现：`subprocess.run` + 参数列表，无 shell。"""

    def __init__(self, base_env: Optional[Dict[str, str]] = None):
        self.base_env = dict(base_env or {})

    def describe(self) -> str:
        return "subprocess(shell=False)"

    def run(self, argv, timeout=60, env=None):
        argv = tuple(str(a) for a in argv)
        if not argv:
            raise ValueError("argv 不能为空")
        merged = dict(os.environ)
        merged.update(self.base_env)
        merged.update(env or {})
        started = time.time()
        try:
            proc = subprocess.run(
                list(argv), capture_output=True, text=True,
                timeout=timeout, env=merged, shell=False,
            )
        except FileNotFoundError:
            return CommandResult(code=127, stderr="not found: %s" % argv[0],
                                 argv=argv)
        except subprocess.TimeoutExpired:
            return CommandResult(code=-1, stderr="timeout after %ss" % timeout,
                                 elapsed_ms=int((time.time() - started) * 1000),
                                 argv=argv)
        except OSError as exc:
            return CommandResult(code=126, stderr=str(exc)[:200], argv=argv)
        return CommandResult(
            code=proc.returncode,
            stdout=proc.stdout or "",
            stderr=proc.stderr or "",
            elapsed_ms=int((time.time() - started) * 1000),
            argv=argv,
        )


class FakeCommand(Command):
    """测试替身：`argv[0]` 或完整 argv 元组 → CommandResult。"""

    def __init__(self, routes: Optional[Dict[str, CommandResult]] = None,
                 default: Optional[CommandResult] = None):
        self.routes = dict(routes or {})
        self.default = default or CommandResult(code=127, stderr="not found: fake")
        self.calls: List[Tuple[str, ...]] = []

    def describe(self) -> str:
        return "fake(%d cmds)" % len(self.routes)

    def run(self, argv, timeout=60, env=None):
        argv = tuple(str(a) for a in argv)
        self.calls.append(argv)
        if argv in self.routes:
            return self.routes[argv]
        if argv and argv[0] in self.routes:
            return self.routes[argv[0]]
        return self.default


def argv_to_text(argv) -> str:
    """把参数列表渲染为可直接 copy/paste 的命令串（AC-18）。"""
    out = []
    for arg in argv:
        text = str(arg)
        if text and all(ch.isalnum() or ch in "-_./:=@%+,[]" for ch in text):
            out.append(text)
        else:
            out.append('"%s"' % text.replace('"', '\\"'))
    return " ".join(out)


def quote_argv(argv) -> str:  # 兼容别名
    return argv_to_text(argv)


def curl_json(url, body) -> str:
    """渲染可直接 copy/paste 的 curl 命令（AC-18）：JSON 单引号包裹 + 转义。"""
    import json as _json
    payload = _json.dumps(body, ensure_ascii=False).replace("'", "'\\''")
    return ("curl -s --noproxy '*' %s -H 'Content-Type: application/json' "
            "-d '%s'" % (url, payload))


