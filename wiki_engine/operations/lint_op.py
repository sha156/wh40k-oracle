"""wiki_engine/operations/lint_op.py — Lint 操作封装。

在 lint 基础上增加日志记录和 CI 模式支持。
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from wiki_engine.build_outputs import build_log_entry, write_log
from wiki_engine.lint import generate_lint_report, run_lint


def lint_operation(
    wiki_root: Path,
    refined_root: Optional[Path] = None,
    pairing_path: Optional[Path] = None,
    auto_fix: bool = True,
    write_report: bool = True,
    log: bool = True,
) -> int:
    """Lint 操作：运行检查、自动修复、生成报告、记录日志。

    返回 issue 总数（0 = 干净）。
    """
    result = run_lint(
        wiki_root=wiki_root,
        refined_root=refined_root,
        pairing_path=pairing_path,
        auto_fix=auto_fix,
    )

    if write_report:
        generate_lint_report(result, wiki_root)
        print("Lint 报告已生成: wiki/lint-report.md")

    # 打印摘要
    errors = sum(1 for i in result.issues if i.severity == "error")
    warnings = sum(1 for i in result.issues if i.severity == "warning")
    infos = sum(1 for i in result.issues if i.severity == "info")
    print("Lint: {} errors, {} warnings, {} info — {} auto-fixed".format(
        errors, warnings, infos, result.auto_fixed))

    if log:
        entry = build_log_entry(
            operation="lint",
            description="{} errors, {} warnings, {} info, {} auto-fixed".format(
                errors, warnings, infos, result.auto_fixed),
        )
        write_log(wiki_root / "log.md", entry)

    return result.total
