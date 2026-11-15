"""复用串联既有共享工具（切片 C）。

仅构造外部命令 argv 并经注入 runner 调用；不重写判据、零第三方依赖。
"""
from __future__ import annotations

from .manifest import UsageError

VALIDATORS = {
    "anatomy": ["python", "scripts/validate_skill.py"],
    "glossary": ["python", "scripts/check_glossary.py"],
    "budget": ["python", "scripts/check_token_budget.py", "--check"],
}


def build_validator_argv(kind: str) -> list:
    if kind not in VALIDATORS:
        raise UsageError("未知校验器: %s" % kind)
    return list(VALIDATORS[kind])


def build_collect_evidence_argv(task, strict=True) -> list:
    cmd = task.cmd
    if not cmd:
        raise UsageError("证据任务 %s 缺 inputs.cmd（collect_evidence 必需）" % task.step)
    argv = ["python", "tools/collect_evidence.py",
            "--step", task.step, "--cmd", cmd,
            "--out", task.outputs.get("evidence", "-")]
    if strict:
        argv.append("--strict")
    if task.target:
        argv += ["--target", task.target]
    return argv


def build_argv(task, strict=True) -> list:
    """按类别选择复用目标：validate → 校验脚本；其余 → collect_evidence。"""
    if task.category == "validate":
        kind = (task.inputs or {}).get("kind", "anatomy")
        return build_validator_argv(kind)
    return build_collect_evidence_argv(task, strict=strict)
