"""CLI：python -m wiki_engine <synthesize|crosslinks|build|lint|pipeline|ingest|query>

LLM Wiki 编译器 + 四操作的主入口。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from wiki_engine.synthesize import create_client, synthesize_all
from wiki_engine.crosslinks import inject_all
from wiki_engine.build_outputs import build_all_outputs, build_log_entry, write_log
from wiki_engine.lint import run_lint, generate_lint_report


def main() -> None:
    ap = argparse.ArgumentParser(prog="wiki_engine")
    sub = ap.add_subparsers(dest="cmd", required=True)

    # ── synthesize ──
    sp = sub.add_parser("synthesize", help="合成实体页（流水线③）")
    sp.add_argument("--pairing", default="wiki_build/pairing.json",
                    help="配对文件路径")
    sp.add_argument("--refined", default="data_refined",
                    help="data_refined 目录")
    sp.add_argument("--wiki", default="wiki", help="wiki 输出目录")
    sp.add_argument("--cache-dir", default="wiki_build/synth_cache",
                    help="合成缓存目录")
    sp.add_argument("--faction", help="只编译指定阵营（pilot 模式）")
    sp.add_argument("--workers", type=int, default=1,
                    help="并发数（LLM API 限流时用 1）")

    # ── crosslinks ──
    sp = sub.add_parser("crosslinks", help="注入 [[wikilinks]]（流水线④）")
    sp.add_argument("--wiki", default="wiki", help="wiki 目录")
    sp.add_argument("--terms", default="wiki/terms.json",
                    help="术语表路径（用于扩充别名匹配）")

    # ── build ──
    sp = sub.add_parser("build", help="构建 index.md 和阵营索引（流水线⑤）")
    sp.add_argument("--wiki", default="wiki", help="wiki 目录")

    # ── lint ──
    sp = sub.add_parser("lint", help="一致性检查（流水线⑥）")
    sp.add_argument("--wiki", default="wiki", help="wiki 目录")
    sp.add_argument("--refined", default="data_refined",
                    help="data_refined 目录（用于 raw 回链检查）")
    sp.add_argument("--no-fix", action="store_true",
                    help="不自动修复")
    sp.add_argument("--no-report", action="store_true",
                    help="不生成 lint-report.md")

    # ── pipeline ──
    sp = sub.add_parser("pipeline", help="运行完整流水线 ③→⑥")
    sp.add_argument("--pairing", default="wiki_build/pairing.json")
    sp.add_argument("--refined", default="data_refined")
    sp.add_argument("--wiki", default="wiki")
    sp.add_argument("--cache-dir", default="wiki_build/synth_cache")
    sp.add_argument("--faction", help="只处理指定阵营（pilot 模式）")
    sp.add_argument("--workers", type=int, default=1)
    sp.add_argument("--no-llm", action="store_true",
                    help="仅从缓存加载，不调用 LLM")

    # ── ingest ──
    sp = sub.add_parser("ingest", help="Ingest 操作：新源料进 wiki")
    sp.add_argument("sources", nargs="+", help="新 data_refined 目录或文件")
    sp.add_argument("--refined", default="data_refined")
    sp.add_argument("--wiki", default="wiki")
    sp.add_argument("--cache-dir", default="wiki_build/synth_cache")

    # ── query ──
    sp = sub.add_parser("query", help="Query 操作：搜索 wiki")
    sp.add_argument("query_text", help="搜索关键词或实体名")
    sp.add_argument("--wiki", default="wiki")

    args = ap.parse_args()

    if args.cmd == "synthesize":
        client = None if getattr(args, "no_llm", False) else create_client()
        stats = synthesize_all(
            pairing_path=Path(args.pairing),
            refined_root=Path(args.refined),
            wiki_root=Path(args.wiki),
            cache_dir=Path(args.cache_dir),
            client=client,
            faction_filter=args.faction,
            max_workers=args.workers,
        )
        print("合成完成: {pairs} pairs, {synthesized} 新合成, {cached} 缓存, "
              "{skipped} 跳过, {failed} 失败".format(**stats))

    elif args.cmd == "crosslinks":
        terms_path = Path(args.terms) if Path(args.terms).exists() else None
        modified = inject_all(Path(args.wiki), terms_path)
        print("交叉链接完成: {} 页已更新".format(len(modified)))

    elif args.cmd == "build":
        result = build_all_outputs(Path(args.wiki))
        print("构建完成: index.md + {} 个阵营索引, {} 条日志".format(
            result["faction_indexes"], result["log_entries"]))

    elif args.cmd == "lint":
        refined = Path(args.refined) if Path(args.refined).is_dir() else None
        result = run_lint(
            wiki_root=Path(args.wiki),
            refined_root=refined,
            auto_fix=not args.no_fix,
        )
        if not args.no_report:
            generate_lint_report(result, Path(args.wiki))
            print("Lint 报告: wiki/lint-report.md")
        errors = sum(1 for i in result.issues if i.severity == "error")
        warnings = sum(1 for i in result.issues if i.severity == "warning")
        print("Lint: {} errors, {} warnings, {} info, {} auto-fixed / {} total".format(
            errors, warnings,
            result.total - errors - warnings,
            result.auto_fixed,
            result.total,
        ))
        if errors > 0:
            sys.exit(1)

    elif args.cmd == "pipeline":
        print("=== Step ③: 合成实体页 ===")
        client = None if args.no_llm else create_client()
        stats = synthesize_all(
            pairing_path=Path(args.pairing),
            refined_root=Path(args.refined),
            wiki_root=Path(args.wiki),
            cache_dir=Path(args.cache_dir),
            client=client,
            faction_filter=args.faction,
            max_workers=args.workers,
        )
        print("合成: {pairs} pairs, {synthesized} 新合成, {cached} 缓存".format(**stats))

        print("\n=== Step ④: 注入交叉链接 ===")
        terms_path = Path(args.wiki) / "terms.json"
        modified = inject_all(Path(args.wiki),
                              terms_path if terms_path.exists() else None)
        print("交叉链接: {} 页已更新".format(len(modified)))

        print("\n=== Step ⑤: 构建索引 ===")
        entry = build_log_entry(
            operation="rebuild",
            description="全量流水线重建 {}".format(
                "（阵营: {}）".format(args.faction) if args.faction else ""),
        )
        result = build_all_outputs(Path(args.wiki), log_entries=[entry])
        print("构建: index.md + {} 个阵营索引".format(result["faction_indexes"]))

        print("\n=== Step ⑥: Lint ===")
        lint_result = run_lint(
            wiki_root=Path(args.wiki),
            refined_root=Path(args.refined) if Path(args.refined).is_dir() else None,
            auto_fix=True,
        )
        generate_lint_report(lint_result, Path(args.wiki))
        errors = sum(1 for i in lint_result.issues if i.severity == "error")
        print("Lint: {} errors, {} warnings — {} auto-fixed".format(
            errors, lint_result.total - errors, lint_result.auto_fixed))
        print("\n流水线完成 ✅")

    elif args.cmd == "ingest":
        from wiki_engine.operations.ingest_op import ingest
        sources = [Path(s) for s in args.sources]
        result = ingest(
            new_sources=sources,
            refined_root=Path(args.refined),
            wiki_root=Path(args.wiki),
            cache_dir=Path(args.cache_dir),
        )
        print("Ingest 完成")

    elif args.cmd == "query":
        from wiki_engine.operations.query_op import query, load_index, search_entities
        wiki_root = Path(args.wiki)
        result = query(args.query_text, wiki_root)
        if result["found"] and result["page"]:
            page = result["page"]
            print("=" * 60)
            print("实体: {}".format(page.fm.name_zh or page.fm.name_en or page.fm.id))
            print("阵营: {}".format(page.fm.faction))
            print("类型: {}".format(page.fm.type))
            print("=" * 60)
            print(page.body[:2000])
        elif result["results"]:
            print("找到 {} 个相关结果:".format(len(result["results"])))
            for entry in result["results"][:10]:
                name = entry.title_zh or entry.title_en or entry.path
                print("  - {} ({}/{})".format(name, entry.faction, entry.type))
                if entry.summary:
                    print("    {}".format(entry.summary[:120]))
        else:
            print("未找到匹配的实体。")


if __name__ == "__main__":
    main()
