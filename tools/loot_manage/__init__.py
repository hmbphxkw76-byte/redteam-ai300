#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""loot-manage 包：战利品登记簿解析与校验（框架无关，仅标准库）。"""
from .registry import (  # noqa: F401
    COLUMNS,
    Registry,
    LootRow,
    SKELETON,
    parse_registry,
    validate,
)

__all__ = ["COLUMNS", "Registry", "LootRow", "SKELETON", "parse_registry", "validate"]
