#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests 包：分组后统一 sys.path 引导，保证 tests.<skill>.test_* 可导入。

CI 使用 `python -m unittest discover -s tests -t . -q`，top-level 为仓库根，
因此测试模块以 `tests.<group>.<module>` 导入；本文件在首次导入时把仓库根
放入 sys.path，使 `tools.*` / `scripts.*` 与共享 helper 均可解析。
"""
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
