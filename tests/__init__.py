#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests 包：分组后统一 sys.path 引导，保证 tests.<skill>.test_* 可导入。

CI 使用 `python -m unittest discover -s tests -t . -q`，top-level 为仓库根，
因此测试模块以 `tests.<group>.<module>` 导入；本文件在首次导入时把仓库根
放入 sys.path，使 `tools.*` / `scripts.*` 与共享 helper 均可解析。
"""
import os
import sys
from pathlib import Path

_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# 既有测试以 AIVP 演练目标为固定夹具；改为经目标画像配置注入，保持既有语义。
# 生产默认仍为 generic 全占位画像（tools/target_profile.py），二者不再硬绑定。
os.environ.setdefault("REDTEAM_TARGET_PROFILES", str(Path(_ROOT) / "tools" / "target_profiles.json"))
os.environ.setdefault("REDTEAM_TARGET_PROFILE", "aivp-rehearsal")
