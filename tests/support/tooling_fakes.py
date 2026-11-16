"""tooling-automate 测试替身（不被 unittest 自动收集：非 test_* 命名）。"""
from tools.tooling_automate.manifest import Task
from tools.tooling_automate.runner import RunOutcome


class FakeRunner:
    def __init__(self, outcomes=None, default=None):
        self.calls = []
        self._outcomes = dict(outcomes or {})
        self._default = default if default is not None else RunOutcome(0, "", "")

    def run(self, argv):
        argv = list(argv)
        self.calls.append(argv)
        key = argv[1] if len(argv) > 1 else ""
        return self._outcomes.get(key, self._default)


def make_task_dict(step, category="enum", classification="auto", cmd="echo hi",
                   target="h1", out_evidence="-", manual=False, kind=None):
    """返回清单原始 dict（用于写 JSON 文件 / 复现 UsageError）。"""
    inputs = {"cmd": cmd}
    if kind is not None:
        inputs["kind"] = kind
    return {
        "category": category,
        "target": target,
        "step": step,
        "inputs": inputs,
        "outputs": {"evidence": out_evidence},
        "trigger": "manual",
        "classification": "manual" if manual else classification,
    }


def make_task(step, **kwargs):
    """返回与生产同型的 Task 对象，供复用层/证据契约测试直接调用。"""
    raw = make_task_dict(step, **kwargs)
    return Task(
        category=raw["category"], target=raw["target"], step=raw["step"],
        inputs=raw["inputs"], outputs=raw["outputs"], trigger=raw["trigger"],
        classification=raw["classification"], raw=raw,
    )
