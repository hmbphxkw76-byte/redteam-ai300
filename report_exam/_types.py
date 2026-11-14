"""report_exam 数据模型（标准库依赖，无 PyRIT）。

本模块仅承载报告组装器的内部数据契约，不执行任何攻击逻辑、不调用 PyRIT。
"""
from dataclasses import dataclass, field
from typing import Dict, List

# 8 个计分目标（GOVERNANCE §2.1/§2.2）：报告主机小节的唯一规范键集
SCORED_HOSTS = (
    "chain1-host1", "chain1-host2", "chain1-host3",
    "chain2-host1", "chain2-host2", "chain2-host3",
    "standalone", "domain-controller",
)
STANDALONE_KEY = "standalone"


@dataclass
class Fragment:
    """单个 collect_evidence.py 证据片段（原子单元）。"""

    step_id: str = ""
    target: str = ""
    title: str = ""
    command: str = ""
    output: str = ""
    screenshot: str = ""
    ai_log: str = ""
    flag: str = ""
    raw: str = ""             # 原始 markdown 片段（逐字 include 的唯一渲染源）
    source_path: str = ""     # 来源文件（证据归属）
    host: str = ""            # 解析后的主机分组键


@dataclass
class ReportModel:
    """组装器的核心数据模型。"""

    hosts: Dict[str, List[Fragment]] = field(default_factory=dict)
    expected_hosts: List[str] = field(default_factory=list)
    osid: str = "XXXXX"
    email: str = "student@youremailaddress.com"
    # 控制面板提交值（VG-4 / §6.2 双通道比对的输入，经 Seam-1 注入）
    panel_flags: Dict[str, str] = field(default_factory=dict)
    # host -> 面板值与报告 flag 值是否逐字一致；None 表示未取分（待补录）
    dual_channel: Dict[str, bool] = field(default_factory=dict)
