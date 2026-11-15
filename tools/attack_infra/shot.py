#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""seam ④：截图计划（只产出计划，不执行截图）。

与 `recon-ai` 的 shot seam 同构：执行截图会把浏览器与网络耦合进单测，而
AC-19 要求测试全程离线，故此处只计算「应当怎么截、落在哪里」，实际捕获由
`collect_evidence.py --screenshot/--shot-cmd` 在证据容器侧完成。
"""
import os
import re
import shlex
from dataclasses import dataclass
from typing import Optional

DEFAULT_DIR = "loot/shots"
# 截图可执行命令：Edge 无头（项目固化方式，见 recon-ai 同构 seam）。
EDGE_HEADLESS = ("msedge --headless=new --disable-gpu --no-first-run "
                 "--virtual-time-budget=8000 --window-size=1280,800")


def _slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", value or "")[:40] or "target"


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

    def plan(self, step_id, url="", region="", target="", timestamp="") -> ShotPlan:
        """计划一张截图（SKILL.md 质量门：访问证明须含目标标识与时间戳）。

        命令为真实可执行的 Edge 无头截图；目标标识与时间戳嵌入文件名，
        保证「截图 + 目标 + 时刻」三者同屏可追溯（§6.2）。
        """
        region = region or step_id
        kind = "url" if _looks_like_url(url) else "transcript"
        stamp = re.sub(r"[^0-9]", "", timestamp or "") or "notime"
        fname = "%s_%s_%s.png" % (step_id, _slug(target), stamp)
        path = os.path.join(self.out_dir, fname)
        if kind == "url":
            cmd = '%s --screenshot="%s" %s' % (EDGE_HEADLESS, path,
                                               shlex.quote(url))
        else:
            # 终端证据截图：由证据容器捕获；此处给可执行的 Edge 占位命令。
            cmd = '%s --screenshot="%s" "about:blank"' % (EDGE_HEADLESS, path)
        return ShotPlan(step_id=step_id, kind=kind, path=path, cmd=cmd,
                        url=url, region=region)


def _looks_like_url(value: Optional[str]) -> bool:
    if not value:
        return False
    return value.startswith("http://") or value.startswith("https://")
