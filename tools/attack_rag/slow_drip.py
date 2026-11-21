#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""P2-7：慢滴投毒时间线 + 事件疲劳 + PDF 生成注记（Ch5 §5.3 清单9–14、C-25..C-28）。

跨天渐进改写、trigger 关键词、得手后回退良性；底层为提示分解越狱思路；
事件疲劳用大量良性事件掩盖变更。PDF 零宽字符须 DejaVu + canvas.drawString。
纯函数，无 IO、不生成真实恶意附件。
"""
from typing import Dict, List

DEFAULT_DAYS = (1, 2, 5, 7, 10, 10)
_ACTIONS = {
    1: "上传良性的负责任漏洞披露文档",
    2: "上传良性 disclosed_vulnerabilities.txt",
    5: "加入读文件指令（读良性文件）",
    7: "加入关键词 trigger",
    10: "替换为敏感文件路径并编码",
}


def timeline(days=DEFAULT_DAYS) -> List[Dict[str, object]]:
    """生成慢滴时间线；末日 10 追加回退良性步骤（C-26）。"""
    days = tuple(days)
    out = [{"day": d, "action": _ACTIONS.get(d, "渐进修改"), "benign": d in (1, 2)}
           for d in days]
    if days and days[-1] == 10:
        out.append({"day": 10, "action": "回退为良性内容（清除恶意指令）", "benign": True})
    return out


def event_fatigue(n: int = 10) -> List[str]:
    """生成 n 条良性事件描述，用于制造事件疲劳（C-27）。"""
    if n < 0:
        raise ValueError("事件数须非负")
    return ["良性事件 #%d：常规文档更新" % (i + 1) for i in range(n)]


def pdf_note() -> str:
    """PDF 零宽字符生成注记（C-28）：DejaVu TTF + canvas.drawString。"""
    return ("PDF 内嵌零宽字符须用支持 Unicode 的 DejaVu TTF 字体，"
            "并用 reportlab canvas.drawString() 代替 Paragraph，避免 XML 解析器吞掉零宽字符")
