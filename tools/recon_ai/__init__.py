#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""recon-ai：AI 资产侦察与枚举（P0 / D2 / 目标计分单元：通用前置）。

公开接口（深模块，仅两个入口）
  - `run_recon(target, profile=...)` → `RunReport`
  - `cli.main(argv)`                 → 退出码

内部模块职责见 `docs/operations/recon-ai-design.md`；证据格式与件套判定
由共享工具 `tools/collect_evidence.py` 唯一提供（C1 单一事实源）。
"""
from .model import (ASSET_FIELDS, Asset, AssetInventory, Category, Existence,
                    ProbeResult, credential_hint)
from .runner import RunReport, run_recon

__all__ = [
    "ASSET_FIELDS", "Asset", "AssetInventory", "Category", "Existence",
    "ProbeResult", "RunReport", "credential_hint", "run_recon",
]
__version__ = "1.0.0"
