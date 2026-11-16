#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试侧统一路径引导（C1 单一事实源）。

tests/ 按 skill 分组后，测试模块处于不同目录深度；任何模块都从这里取
仓库根，不再用 dirname(dirname(__file__)) 这类随深度失效的写法。

ROOT 为 str（与各测试既有 os.path.join(ROOT, ...) / sys.path.insert 用法兼容）；
ROOT_PATH 为等价 pathlib.Path，供 Path 风格测试使用。
"""
from pathlib import Path

ROOT_PATH = Path(__file__).resolve().parent.parent
ROOT = str(ROOT_PATH)
FIXTURES = str(ROOT_PATH / "tests" / "fixtures")
