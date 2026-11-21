#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P0-1：能力探测 / 过滤不对称 / 休眠文档（Ch5 §5.2 图17–20）。

依据一手源 docs/research/attack-rag-ch5-exploitation-canonical.md C-10..C-13：
- 先探测命令执行/建文件/Web 请求/读文件四类能力（C-11）；
- 关键机制：输入过滤只作用于用户输入，不作用于检索上下文（C-12）；
- 休眠文档用与正常查询不碰撞的掩护主题 + 恶意指令（C-10/C-13）。

纯算法模块：不导入 pyrit、不做 IO、不猜未观测能力（缺项记「不可判定」）。
"""
from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple

UNKNOWN = "不可判定"
CAPABILITIES: Tuple[str, ...] = ("命令执行", "文件创建", "Web 请求", "文件读取")


@dataclass
class ProbeResult:
    """一次能力探测的可观察回执。"""

    probed: Tuple[str, ...]
    observed: Dict[str, bool]
    tells: Tuple[str, ...] = ()

    def render(self) -> str:
        lines = ["能力探测（%d 类）：" % len(self.probed)]
        for name in self.probed:
            value = self.observed.get(name)
            state = UNKNOWN if value is None else ("存在" if value else "未发现")
            lines.append("- %s：%s" % (name, state))
        if self.tells:
            lines.append("能力线索：%s" % "；".join(self.tells))
        return "\n".join(lines)

    def as_dict(self):
        return {"probed": list(self.probed), "observed": dict(self.observed),
                "tells": list(self.tells)}


def probe(observed: Optional[Dict[str, bool]] = None,
          tells: Sequence[str] = ()) -> ProbeResult:
    """把探测回执归为可观察结论；未提供某能力即「不可判定」，不臆测。"""
    observed = dict(observed or {})
    clean = {name: observed.get(name) for name in CAPABILITIES if name in observed}
    return ProbeResult(probed=CAPABILITIES, observed=clean, tells=tuple(tells))


def filter_asymmetry(direct_blocked: bool, context_blocked: bool = False) -> str:
    """过滤不对称结论（C-12）：直接输入被拦、检索上下文未拦 → 可绕。"""
    if direct_blocked and not context_blocked:
        return ("输入过滤: 直接输入被拦截\n"
                "检索上下文: 未拦截（恶意指令位于可信上下文）\n"
                "结论: 过滤不对称成立，可经检索上下文绕过输入过滤")
    if direct_blocked and context_blocked:
        return ("输入过滤: 直接输入被拦截\n"
                "检索上下文: 被拦截\n"
                "结论: 未观察到过滤不对称，不可断言可绕")
    return ("输入过滤: 直接输入未拦截\n"
            "检索上下文: %s\n"
            "结论: %s" % ("未拦截" if not context_blocked else "被拦截",
                          "无需绕过" if not context_blocked else "过滤点不在用户输入"))


def dormant_doc(topic: str, instruction: str,
                high_frequency_terms: Sequence[str] = ()) -> str:
    """休眠文档：掩护主题在前、恶意指令在后，且不含高频查询词（C-10/C-13）。"""
    if not (topic or "").strip():
        raise ValueError("掩护主题不能为空（休眠文档须有唯一触发主题）")
    if not (instruction or "").strip():
        raise ValueError("恶意指令不能为空")
    text = "关于%s的说明：\n%s\n%s" % (
        topic.strip(), "本主题用于内部参考，包含常规说明信息。", instruction.strip())
    leaked = [term for term in high_frequency_terms if term and term in text]
    if leaked:
        raise ValueError("休眠文档含高频查询词，会误触发：%s" % "、".join(leaked))
    return text
