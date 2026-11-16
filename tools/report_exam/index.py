"""证据索引：把 collect_evidence.py 片段解析并聚合为 ReportModel。

Seam-1（唯一外部依赖注入点）即 `EvidenceSource`：默认 `DirEvidenceSource`
从 evidence/<skill>-real/*.md 读取；测试注入内存假后端。
"""
import glob
import os
import re
from typing import Dict, Iterable, Iterator, List

from ._types import Fragment, ReportModel, SCORED_HOSTS, STANDALONE_KEY

# 正式提交仅接受 `-real` 真实证据目录；演练/仿真与实现日志目录一律排除
EXCLUDED_DIR_MARKERS = ("report-exam", "evidence/attack-ai-agent/")


def parse_fragment(text: str, source_path: str = "") -> Fragment:
    """解析单个 collect_evidence.py 片段 markdown 为 Fragment。

    `raw` 保留原文（逐字 include 的唯一渲染源）；结构化字段仅用于校验判据。
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
    """从 evidence/<skill>-real/*.md 读取并解析片段。

    `real_only=True`（默认）时只接受路径含 `-real` 的证据目录，
    防止演练/仿真片段与实现日志混入正式提交（SKILL §4 / F-7.3）。
    测试夹具可显式传 real_only=False。
    """

    def __init__(self, roots, real_only=True):
        self.roots = [roots] if isinstance(roots, str) else list(roots)
        self.real_only = real_only

    def _allowed(self, path: str) -> bool:
        p = path.replace("\\", "/")
        if any(marker in p for marker in EXCLUDED_DIR_MARKERS):
            return False
        if not self.real_only:
            return True
        # 正式提交仅接受路径中带 `-real` 目录段的证据（SKILL §4）
        return any(seg.endswith("-real") for seg in p.split("/"))

    def iter_fragments(self) -> Iterator[Fragment]:
        for root in self.roots:
            for path in sorted(glob.glob(os.path.join(root, "**", "*.md"), recursive=True)):
                if not self._allowed(path):
                    continue
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        text = f.read()
                except OSError:
                    continue
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


def build_index(source: EvidenceSource, expected_hosts=None, osid="XXXXX",
                panel_flags=None) -> ReportModel:
    """聚合证据源为 ReportModel。

    - 按 frag.host 分组；expected_hosts 中缺片段的主机置空（未达成）。
    - dual_channel：面板提交值与报告 flag 值**逐字比对**（§6.2）；无 flag
      记 False（未取分，待补录）。
    """
    model = ReportModel(osid=osid)
    model.expected_hosts = list(expected_hosts or [])
    model.panel_flags = dict(panel_flags or {})

    # 主机键归一化：非规范键（如真实片段的 target URL）按 MAP §C 归入
    # Standalone / AI-vector 计分目标，保证报告不产生额外或重复的主机小节。
    canonical = set(model.expected_hosts or SCORED_HOSTS)
    grouped: Dict[str, List[Fragment]] = {}
    for f in source.iter_fragments():
        if f.host not in canonical:
            f.host = STANDALONE_KEY
        grouped.setdefault(f.host, []).append(f)
    model.hosts = grouped

    for h in model.expected_hosts:
        if h not in model.hosts:
            model.hosts[h] = []

    for h, fs in model.hosts.items():
        report_flags = [f.flag for f in fs if f.flag]
        panel = model.panel_flags.get(h)
        model.dual_channel[h] = bool(
            report_flags and panel is not None
            and all(v == panel for v in report_flags)
        )
    return model
