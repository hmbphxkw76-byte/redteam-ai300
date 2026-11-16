"""任务清单解析层（切片 A）。

声明式清单：逐条登记 类别/目标/step/输入/输出/触发/分类 七字段。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

MANUAL = "manual"
EXPECTED_FIELDS = ("category", "target", "step", "inputs", "outputs", "trigger", "classification")
STEP_RE = re.compile(r"^[\w-]+-\d{2}$")


class ManifestError(Exception):
    """任务清单结构性错误。"""


class UsageError(ManifestError):
    """非法输入 / step 标识冲突 → 退出码 2。"""


@dataclass
class Task:
    category: str
    target: str
    step: str
    inputs: dict
    outputs: dict
    trigger: str
    classification: str
    raw: dict = field(default_factory=dict, repr=False)

    @property
    def is_manual(self) -> bool:
        return self.classification == MANUAL

    @property
    def cmd(self) -> str:
        return (self.inputs or {}).get("cmd", "") or ""


@dataclass
class Manifest:
    tasks: list

    @property
    def scriptable(self):
        return [t for t in self.tasks if not t.is_manual]

    @property
    def manual(self):
        return [t for t in self.tasks if t.is_manual]


def parse_step(step: str):
    if not STEP_RE.match(step or ""):
        raise UsageError("非法 step 标识（须 <prefix>-NN）: %s" % step)
    prefix, _, idx = step.rpartition("-")
    return prefix, int(idx)


def load_manifest(path):
    from pathlib import Path

    text = Path(path).read_text(encoding="utf-8")
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise UsageError("清单非合法 JSON: %s" % exc) from exc
    if not isinstance(data, dict) or "tasks" not in data:
        raise ManifestError("清单须为含 tasks 数组的对象")
    tasks = []
    seen = set()
    for i, raw in enumerate(data.get("tasks", [])):
        if not isinstance(raw, dict):
            raise UsageError("任务 #%d 须为对象" % i)
        missing = [f for f in EXPECTED_FIELDS if f not in raw]
        if missing:
            raise UsageError("任务 #%d 缺字段: %s" % (i, ",".join(missing)))
        step = raw["step"]
        if step in seen:
            raise UsageError("step 标识冲突: %s" % step)
        seen.add(step)
        parse_step(step)  # 非法格式 → UsageError → exit 2
        tasks.append(Task(
            category=raw.get("category", ""),
            target=raw.get("target", ""),
            step=step,
            inputs=raw.get("inputs") or {},
            outputs=raw.get("outputs") or {},
            trigger=raw.get("trigger", ""),
            classification=raw.get("classification", ""),
            raw=raw,
        ))
    return Manifest(tasks=tasks)
