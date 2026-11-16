#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""证据写入器最小接口契约（C1 单一事实源，S1 静态可检）。

四类 EvidenceWriter 适配层物理上仍留在各自 skill 包内（薄封装，不迁移）：
  tools/recon_ai/evidence.py          跨包共享公共 seam（见其 docstring）
  tools/attack_infra/evidence.py
  tools/decoy_detect/evidence.py
  tools/capstone_rehearse/evidence.py
另有 tools/attack_supply_chain/evidence.py 的函数式 emit() 形态，暂不纳入本契约。

契约本身只约定「最小方法和返回形态」，**不定义证据片段格式**——格式唯一事实源
仍为 tools/collect_evidence.py（本模块不改变它）。各适配器保留既有构造参数与
关键字别名，契约一致不代表签名逐字相同。

校验入口：python scripts/check_evidence_contract.py
"""
from __future__ import annotations

from typing import Protocol, Tuple, runtime_checkable


@runtime_checkable
class EvidenceWriterContract(Protocol):
    """证据写入器最小契约：三方法 + 统一返回形态。"""

    def describe(self) -> str:
        """返回该写入器的可读标识（用于日志/报告）。"""
        ...

    def fragment_path(self, step_id: str) -> str:
        """返回步骤片段的目标路径（不写盘）。"""
        ...

    def emit(self, step_id: str, command: str, output: str = "",
             **options) -> Tuple[str, int, str]:
        """写一份片段，返回 (片段路径, 退出码, 标准错误摘要)。

        退出码语义沿用共享收集器：0 成功；1 严格模式未过质量门；2 用法/运行错误。
        """
        ...


CONTRACT_MEMBERS = ("describe", "fragment_path", "emit")
