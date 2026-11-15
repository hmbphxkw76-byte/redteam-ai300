#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""外部扫描适配 seam（矩阵 §⑩ 主演：A2ASecBench / a2a-scanner）。

框架组合强制对齐：多智能体（MA）攻击由 A2ASecBench + a2a-scanner 主导，PyRIT 仅做
深度补位（见 `pyrit_attack.py`）。本模块把「主控扫描器」抽象为可注入 seam：
  - `BuiltinAnalyzer`：内建轻量 Analyzer，离线可跑，保证无外部依赖时仍能落地证据（AC-11）；
  - `A2ASecBenchAdapter`：把 A2ASecBench 六类攻击/ a2a-scanner 的 Agent Card 分析
    接入同一接口；外部库不可用时显式报错，不静默降级（B9 透明）。
"""
import re
from dataclasses import dataclass, field
from typing import Callable, List, Optional

# 恶意 Agent Card 指示符：权限声明夸大 / 隐藏指令 / 非预期出站
_OVER_BROAD_SCOPE = re.compile(r"(?:scope|权限|范围)\s*[:：]?\s*(admin|write|root|\*)", re.IGNORECASE)
_HIDDEN_INSTRUCTION = re.compile(r"(?:instruction|指令|system)\s*[:：]?\s*(执行|send|exfiltrate|delete)", re.IGNORECASE)
_UNEXPECTED_Egress = re.compile(r"(?:callback|webhook|http[s]?://[^\s]+)", re.IGNORECASE)


@dataclass
class AgentCardFinding:
    """一条 Agent Card / 拓扑发现的可疑发现。"""

    category: str       # malicious-agent-card | over-broad-scope | hidden-instruction | unexpected-egress
    detail: str
    severity: str = "medium"   # low | medium | high

    def as_dict(self):
        return {"category": self.category, "detail": self.detail, "severity": self.severity}


class Scanner:
    """扫描 seam 接口：实现 `analyze` 即可替换。"""

    def analyze(self, text: str) -> List[AgentCardFinding]:
        raise NotImplementedError

    def describe(self):
        return self.__class__.__name__


class BuiltinAnalyzer(Scanner):
    """内建分析仪：纯启发式，基于文本模式识别恶意 Agent Card 指示符（离线可用）。"""

    def analyze(self, text: str) -> List[AgentCardFinding]:
        findings: List[AgentCardFinding] = []
        if _OVER_BROAD_SCOPE.search(text or ""):
            findings.append(AgentCardFinding(
                "over-broad-scope", "检测到过宽权限声明（admin/write/root/*）", "high"))
        if _HIDDEN_INSTRUCTION.search(text or ""):
            findings.append(AgentCardFinding(
                "hidden-instruction", "检测到隐藏指令式措辞", "high"))
        for m in _UNEXPECTED_Egress.finditer(text or ""):
            findings.append(AgentCardFinding(
                "unexpected-egress", "检测到非预期出站地址：%s" % m.group(0), "medium"))
        return findings


class A2ASecBenchAdapter(Scanner):
    """A2ASecBench / a2a-scanner 适配 seam。

    外部库（`a2asecbench` / `a2a_scanner`）为可选依赖，不随本仓库安装。
    生产使用时把真实的运行器以 `runner` 注入（保持可测、可离线断言契约）；
    未注入且外部库不可用时，显式报错而非静默返回空结果（B9 透明）。
    """

    def __init__(self, runner: Optional[Callable[[str], List[dict]]] = None):
        self._runner = runner

    def analyze(self, text: str) -> List[AgentCardFinding]:
        if self._runner is not None:
            raw = self._runner(text)
            return [AgentCardFinding(f.get("category", "unknown"),
                                     f.get("detail", ""), f.get("severity", "medium"))
                    for f in raw]
        # 未注入真实运行器：尝试导入外部库，失败即明确报错
        try:  # pragma: no cover - 依赖外部库，CI 不安装
            import a2asecbench  # type: ignore  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "A2ASecBench 未安装；请 `pip install a2asecbench` 或以 runner= 注入，"
                "或改用 BuiltinAnalyzer（离线可用）。（B9 透明，不静默降级）") from exc
        raise NotImplementedError("已检测到 a2asecbench，但本 seam 仅接受注入式 runner（可测）。")
