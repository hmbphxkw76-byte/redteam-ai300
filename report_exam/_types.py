"""report_exam 数据模型（标准库依赖，无 PyRIT）。

本模块仅承载报告组装器的内部数据契约，不执行任何攻击逻辑、不调用 PyRIT。
"""
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Fragment:
    """单个 collect_evidence.py 证据片段（原子单元）。"""

    step_id: str = ""
    target: str = ""          # 来自片段 `> **目标**：` 的标识（通常为 URL/IP）
    title: str = ""
    command: str = ""         # #### 确切命令
    output: str = ""          # #### 关键输出
    screenshot: str = ""      # #### 截图（访问证明）路径
    ai_log: str = ""          # #### AI 交互日志
    flag: str = ""            # #### flag 取证（双通道一致）
    raw: str = ""             # 原始 markdown 片段（用于逐字 include）
    source_path: str = ""     # 来源文件（证据归属）
    host: str = ""            # 解析后的主机分组键


@dataclass
class ReportModel:
    """组装器的核心数据模型。"""

    hosts: Dict[str, List[Fragment]] = field(default_factory=dict)
    expected_hosts: List[str] = field(default_factory=list)  # 计分目标全集（用于缺失回溯）
    osid: str = "XXXXX"
    email: str = "student@youremailaddress.com"
    # host -> 是否双通道一致（面板值 == 报告值）；缺失为 None（待补录）
    dual_channel: Dict[str, bool] = field(default_factory=dict)
    proof_submitted_once: bool = False
