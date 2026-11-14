"""证据索引：把 collect_evidence.py 片段解析并聚合为 ReportModel。

Seam-1（唯一外部依赖注入点）即 `EvidenceSource`：默认 `DirEvidenceSource`
从 evidence/<skill>/*.md 读取；测试注入内存假后端。
"""
import os
import re
import glob
from typing import Iterable, Iterator

from ._types import Fragment, ReportModel


def parse_fragment(text: str, source_path: str = "") -> Fragment:
    """解析单个 collect_evidence.py 片段 markdown 为 Fragment。

    字段定位依赖固定标题（`#### 确切命令` 等），对缺失字段返回空串。
    """
    frag = Fragment(raw=text, source_path=source_path)

    m = re.search(r"^###\s+步骤\s+(.+?)(?:\s*：\s*(.+))?\s*$", text, re.M)
    if m:
        frag.step_id = m.group(1).strip()
        frag.title = (m.group(2) or "").strip()

    m = re.search(r"\*\*目标\*\*\s*[：:]\s*`([^`]+)`", text)
    if m:
        frag.target = m.group(1).strip()

    def block(header: str) -> str:
        pat = re.compile(
            r"####\s+" + re.escape(header) + r"\s*\n+(?:```[^\n]*\n(.*?)```|([^\n]*))",
            re.S,
        )
        mm = pat.search(text)
        if not mm:
            return ""
        return (mm.group(1) if mm.group(1) is not None else mm.group(2) or "").strip()

    frag.command = block("确切命令")
    frag.output = block("关键输出")
    frag.ai_log = block("AI 交互日志")
    frag.flag = block("flag 取证（双通道一致）")

    m = re.search(r"!\[[^\]]*\]\(([^)]+)\)", text)
    if m:
        frag.screenshot = m.group(1).strip()

    frag.host = frag.target or os.path.splitext(os.path.basename(source_path))[0]
    return frag


class EvidenceSource:
    """证据源协议（Seam-1 注入点）。子类实现 iter_fragments。"""

    def iter_fragments(self) -> Iterator[Fragment]:
        raise NotImplementedError


class DirEvidenceSource(EvidenceSource):
    """从 evidence/<skill>/*.md 读取并解析片段。"""

    def __init__(self, roots):
        # roots: 目录列表或单目录；递归匹配 **/*.md
        self.roots = [roots] if isinstance(roots, str) else list(roots)

    def iter_fragments(self) -> Iterator[Fragment]:
        for root in self.roots:
            for path in sorted(glob.glob(os.path.join(root, "**", "*.md"), recursive=True)):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        text = f.read()
                except OSError:
                    continue
                # 一个文件可能含多个 `### 步骤` 片段
                parts = re.split(r"(?=^###\s+步骤\s+)", text, flags=re.M)
                for part in parts:
                    if part.strip().startswith("### 步骤"):
                        yield parse_fragment(part, source_path=path)


class MemoryEvidenceSource(EvidenceSource):
    """内存假后端（测试注入）。"""

    def __init__(self, fragments: Iterable[Fragment]):
        self._frags = list(fragments)

    def iter_fragments(self) -> Iterator[Fragment]:
        for f in self._frags:
            yield f


def build_index(source: EvidenceSource, expected_hosts=None, osid="XXXXX") -> ReportModel:
    """聚合证据源为 ReportModel。

    - 按 frag.host 分组；
    - expected_hosts 中存在但无片段的主机标记为「未达成」（hosts 中置空列表）；
    - dual_channel 默认按 flag 是否非空占位（真实双通道一致需运行时比对面板值）。
    """
    model = ReportModel(osid=osid)
    model.expected_hosts = list(expected_hosts or [])

    grouped: Dict[str, List[Fragment]] = {}
    for f in source.iter_fragments():
        grouped.setdefault(f.host, []).append(f)

    model.hosts = grouped

    # 缺失主机回溯（AC-02）
    for h in model.expected_hosts:
        if h not in model.hosts:
            model.hosts[h] = []  # 空列表 = 未达成

    # 双通道占位覆盖**全部**主机（含未在 expected_hosts 中的真实片段主机）；
    # 仅记录是否已提供 flag 文本，真实一致性比对在运行时由面板值驱动（VG-4）。
    for h, fs in model.hosts.items():
        model.dual_channel[h] = bool(any(f.flag for f in fs))

    model.proof_submitted_once = sum(
        1 for f in (ff for fs in model.hosts.values() for ff in fs)
        if "proof.txt" in (f.flag or "")
    ) <= 1
    return model
