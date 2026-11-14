"""打包、命名合规与 verify-evidence 提交前置衔接（§6.4 / §7.3 / §8.2）。

判据**委托**仓库级共享校验器 `tools/verify_evidence.py`（`skills/verify-evidence`
的执行体），本模块不重实现八项检查单，避免门禁被下游放宽（阶段 10 修复项）。

pandoc / 7z 以 subprocess 惰性调用：导入本模块不触发外部工具；
CI/沙箱缺工具时显式失败并转 VG-3 核实闸，不静默跳过。
"""
import importlib.util
import os
import shutil
import subprocess

from ._types import ReportModel

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAX_ARCHIVE_BYTES = 100 * 1024 * 1024  # §6.4
PDF_NAME = "OSAI-OS-{osid}-Exam-Report.pdf"
ZIP_NAME = "OSAI-OS-{osid}-Exam-Report.7z"


def _shared():
    """加载仓库级 verify-evidence 校验器（单一判据源）。"""
    path = os.path.join(ROOT, "tools", "verify_evidence.py")
    spec = importlib.util.spec_from_file_location("_verify_evidence_shared", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# pandoc 输出 PDF 必须经 --pdf-engine；其默认 pdflatex 在无 LaTeX 的 CI/沙箱不存在
# （实测 pandoc 3.14 报 "'pdflatex' not found" 退出码 47，VG-PANDOC-1）。故显式解析
# 可用引擎：PANDOC_PDF_ENGINE 环境变量优先（便于 CI 固定版本），否则按序探测。
PDF_ENGINE_CANDIDATES = ("typst", "wkhtmltopdf", "weasyprint",
                         "xelatex", "lualatex", "pdflatex")


def _pdf_engine():
    """返回 --pdf-engine 的值；无可用引擎返回 None（交 pandoc 明确报错 → VG-3）。"""
    explicit = os.environ.get("PANDOC_PDF_ENGINE")
    if explicit:
        return explicit
    for name in PDF_ENGINE_CANDIDATES:
        if shutil.which(name):
            return name
    return None


def _default_runner(argv, **kwargs):
    return subprocess.run(argv, **kwargs)


def render_pdf(markdown_text, out_dir, osid, runner=None):
    """pandoc --toc 渲染 EN 版 PDF；缺 pandoc/引擎抛 RuntimeError（VG-3）。"""
    runner = runner or _default_runner
    os.makedirs(out_dir, exist_ok=True)
    src = os.path.join(out_dir, "report-en.md")
    pdf = os.path.join(out_dir, PDF_NAME.format(osid=osid))
    with open(src, "w", encoding="utf-8") as f:
        f.write(markdown_text)
    argv = ["pandoc", "--toc"]
    engine = _pdf_engine()
    if engine:
        argv.append("--pdf-engine=" + engine)
    argv += [src, "-o", pdf]
    try:
        runner(argv, check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            "VG-3：pandoc 不可用或渲染失败（%s）；请核实 CI/沙箱 pandoc 安装。" % exc
        ) from exc
    return pdf


def make_archive(pdf_path, out_dir, osid, runner=None):
    """7z a -mx=9 无密码归档；缺 7z 抛 RuntimeError（VG-3）。"""
    runner = runner or _default_runner
    zip_path = os.path.join(out_dir, ZIP_NAME.format(osid=osid))
    if os.path.isfile(zip_path):
        os.remove(zip_path)
    try:
        runner(["7z", "a", "-mx=9", zip_path, pdf_path], check=True,
               capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RuntimeError(
            "VG-3：7z 不可用或打包失败（%s）；请核实 CI/沙箱 7z 安装。" % exc
        ) from exc
    return zip_path


def check_naming_and_size(pdf_path, zip_path, osid):
    """委托共享校验器（AC-12），保持单一判据源。"""
    return _shared().check_naming_and_size(pdf_path, zip_path, osid)


def _payload(model: ReportModel, report_md, appendix_md, pdf_path, zip_path):
    frags = [f for fs in model.hosts.values() for f in fs]
    return {
        "report_md": report_md,
        "appendix_md": appendix_md,
        "osid": model.osid,
        "fragments": [{
            "step_id": f.step_id, "host": f.host, "command": f.command,
            "output": f.output, "screenshot": f.screenshot,
            "ai_log": f.ai_log, "flag": f.flag,
        } for f in frags],
        "panel_flags": model.panel_flags,
        "pdf_path": pdf_path,
        "zip_path": zip_path,
    }


def verify_report(model: ReportModel, report_md, appendix_md="",
                  pdf_path=None, zip_path=None, require_artifacts=False):
    """verify-evidence 八项检查单（委托共享校验器）。

    `require_artifacts=False` 为报告内容 dry-run 校验（vrf-07 记未判定）；
    提交前置由 `package()` 以 `require_artifacts=True` 调用。
    """
    payload = _payload(model, report_md, appendix_md, pdf_path, zip_path)
    return _shared().verify(payload, require_artifacts=require_artifacts)


def package(model: ReportModel, en_markdown, out_dir, runner=None):
    """渲染 → 归档 → verify-evidence 提交前置（AC-12 / AC-13）。

    返回 passed 取 `submission_ready`；缺 pandoc/7z 时记录 VG-3 且非 0，
    由 CLI 传播退出码（阶段 10 修复项）。
    """
    result = {"pdf": None, "zip": None, "verify": None, "passed": False,
              "blocking": [], "vg3": False}
    try:
        pdf = render_pdf(en_markdown, out_dir, model.osid, runner=runner)
        zip_path = make_archive(pdf, out_dir, model.osid, runner=runner)
        result["pdf"], result["zip"] = pdf, zip_path
    except RuntimeError as exc:
        result["blocking"].append(str(exc))
        result["vg3"] = True

    v = verify_report(model, en_markdown, appendix_md=en_markdown,
                      pdf_path=result["pdf"], zip_path=result["zip"],
                      require_artifacts=True)
    result["verify"] = v
    result["blocking"].extend(v["blocking"])
    result["passed"] = bool(v["submission_ready"]) and not result["vg3"]
    return result
