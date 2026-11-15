#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""seam ④：截图计划（只产出计划，不执行截图）。

与 `recon-ai` 的 shot seam 同构：执行截图会把浏览器与网络耦合进单测，而
AC-19 要求测试全程离线，故此处只计算「应当怎么截、落在哪里」，实际捕获由
`collect_evidence.py --screenshot/--shot-cmd` 在证据容器侧完成。
"""
import os
from dataclasses import dataclass
from typing import Optional

DEFAULT_DIR = "loot/shots"


@dataclass(frozen=True)
class ShotPlan:
    step_id: str
    kind: str
    path: str
    cmd: str
    url: str = ""
    region: str = ""


class ShotPlanner:
    """纯函数式计划器：相同输入恒得相同计划。"""

    def __init__(self, out_dir=DEFAULT_DIR):
        self.out_dir = out_dir

    def describe(self) -> str:
        return "shot-planner(%s)" % self.out_dir

    def plan(self, step_id, url="", region="") -> ShotPlan:
        region = region or step_id
        kind = "url" if _looks_like_url(url) else "transcript"
        path = os.path.join(self.out_dir, "%s.png" % step_id)
        cmd = 'screenshot --region %s --out "%s"' % (region, path)
        return ShotPlan(step_id=step_id, kind=kind, path=path, cmd=cmd,
                        url=url, region=region)


def _looks_like_url(value: Optional[str]) -> bool:
    if not value:
        return False
    return value.startswith("http://") or value.startswith("https://")
