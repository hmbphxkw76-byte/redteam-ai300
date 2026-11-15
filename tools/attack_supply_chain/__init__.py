#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""attack-supply-chain 实现包（阶段8 tracer bullet）。

按 spec v2 的 S1–S5 seam 组织：证据契约、投毒引擎、模型扫描、注入器、recon 输入。
外部重依赖（art / modelscan / pyrit）全部惰性导入，测试以假后端注入，保持零依赖可测。
"""
from .recon_input import SupplySurface, load_assets
from .poison_engine import (FakePoisonBackend, ArtPoisonBackend, PoisonBackend,
                            poison_dataset, poison_model)
from .model_scan import ScanResult, scan, is_malicious_detected
from .injector import (InjectionConfig, inject_build, inject_dependency,
                       inject_pipeline)
from .evidence import build_args, emit
from .workflow import STEP_IDS, run

__all__ = [
    "SupplySurface", "load_assets",
    "PoisonBackend", "FakePoisonBackend", "ArtPoisonBackend",
    "poison_dataset", "poison_model",
    "ScanResult", "scan", "is_malicious_detected",
    "InjectionConfig", "inject_dependency", "inject_pipeline", "inject_build",
    "emit", "build_args", "STEP_IDS", "run",
]
