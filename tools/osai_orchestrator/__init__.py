"""osai-orchestrator：OSAI（AI-300）考试编排与韧性增强层。

纯增量模块：不修改任何既有 skill/tool，不重写判据，不含攻击载荷。
把 PentAGI 迁移清单中的 A/B 类判据实现为可调用、可注入、可测试的纯逻辑：
运行时监督、计划与人在环、上下文与记忆治理、工具治理、报告治理。

设计见 docs/operations/osai-orchestrator-design.md；零第三方依赖、
零 PyRIT 运行时强依赖，外部命令经可注入 CommandRunner。
"""
from __future__ import annotations

from .models import (
    Verdict,
    Decision,
    Record,
    GateResult,
    LimitConfig,
    AnonymizeConfig,
    PromptContext,
)
from .supervision import (
    ExecutionMonitor,
    MonitorVerdict,
    Reflector,
    ReflectVerdict,
    ToolCallBudget,
    Barrier,
    BarrierKind,
)
from .planning import (
    Planner,
    PlanStep,
    Refiner,
    RefineOps,
    HumanInLoop,
    ControlAction,
)
from .governance import (
    SummaryMarker,
    ContextCompactor,
    Anonymizer,
    MemoryWhitelist,
    IndependentReviewer,
    ReviewItem,
    TemplateOverlay,
    Ontology,
)
from .tooling import (
    ToolKind,
    ToolSpec,
    TypedRegistry,
    CallIDNormalizer,
    ErrorKind,
    ErrorClassifier,
    RetryPolicy,
    BoundedRetriever,
)
from .runner import CommandRunner, SubprocessRunner, RunOutcome, Orchestrator
from .cli import main
from .handoff import (
    derive_panel_flags, recon_fragments_for_report,
    check_h1_asset_inventory, check_h2_screenshot, check_h3_dual_channel,
    check_h4_reusable_loot, check_h5_report_enumeration, check_h6_submission,
    ALIGNMENT_CLAIMS, verify_alignment, all_checks,
)
from .d11_gateway import (
    D11Result, CommandRunner, SubprocessRunner, RunOutcome,
    prepare_report_inputs, run_d11_gateway, load_window,
)

__all__ = [
    "Verdict", "Decision", "Record", "GateResult", "LimitConfig", "AnonymizeConfig", "PromptContext",
    "ExecutionMonitor", "MonitorVerdict", "Reflector", "ReflectVerdict", "ToolCallBudget", "Barrier", "BarrierKind",
    "Planner", "PlanStep", "Refiner", "RefineOps", "HumanInLoop", "ControlAction",
    "SummaryMarker", "ContextCompactor", "Anonymizer", "MemoryWhitelist", "IndependentReviewer", "ReviewItem",
    "TemplateOverlay", "Ontology",
    "ToolKind", "ToolSpec", "TypedRegistry", "CallIDNormalizer", "ErrorKind", "ErrorClassifier", "RetryPolicy",
    "BoundedRetriever",
    "CommandRunner", "SubprocessRunner", "RunOutcome", "Orchestrator", "main",
    "derive_panel_flags", "recon_fragments_for_report",
    "check_h1_asset_inventory", "check_h2_screenshot", "check_h3_dual_channel",
    "check_h4_reusable_loot", "check_h5_report_enumeration", "check_h6_submission",
    "ALIGNMENT_CLAIMS", "verify_alignment", "all_checks",
    "D11Result", "prepare_report_inputs", "run_d11_gateway", "load_window",
]
