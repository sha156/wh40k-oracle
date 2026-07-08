"""CLI：python -m db_compile build"""
from __future__ import annotations

import argparse
from pathlib import Path

from db_compile.build import build_database


def main() -> None:
    ap = argparse.ArgumentParser(prog="db_compile")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("build", help="db_sources/wahapedia/*.csv → wh40k.sqlite")
    p.add_argument("--csv-dir", default="db_sources/wahapedia")
    p.add_argument("--db", default="db/wh40k.sqlite")
    p.add_argument("--terms", default="wiki/terms.json")

    x = sub.add_parser("crosscheck", help="BSData ↔ Wahapedia 英文属性交叉校验")
    x.add_argument("--bsdata", default="db_sources/bsdata")
    x.add_argument("--db", default="db/wh40k.sqlite")
    x.add_argument("--out", default=None, help="可选：把完整报告写成 JSON")

    args = ap.parse_args()
    if args.cmd == "build":
        report = build_database(Path(args.csv_dir), Path(args.db), Path(args.terms))
        print("行数:", report.row_counts)
        if report.missing_csv:
            print("待下载 CSV：", ", ".join(report.missing_csv))
    elif args.cmd == "crosscheck":
        import json

        from db_compile.crosscheck import run

        rep = run(Path(args.bsdata), Path(args.db))
        print(f"Wahapedia {rep.wahapedia_total} 单位 / BSData {rep.bsdata_total} 单位")
        print(f"同名匹配 {rep.matched} ({rep.match_rate}%)  |  "
              f"属性一致 {rep.agreed} ({rep.agreement_rate}%)  |  真分歧 {len(rep.discrepancies)}")
        print("\n真·不一致清单（需人工对官方）：")
        for d in rep.discrepancies:
            print(f"  {d['name'][:32]:32} {d['field']}: "
                  f"Wah[{d['wahapedia']}] ≠ BS[{d['bsdata']}]")
        if args.out:
            payload = {
                "summary": {
                    "wahapedia_total": rep.wahapedia_total, "bsdata_total": rep.bsdata_total,
                    "matched": rep.matched, "match_rate": rep.match_rate,
                    "agreed": rep.agreed, "agreement_rate": rep.agreement_rate,
                    "discrepancy_count": len(rep.discrepancies),
                },
                "discrepancies": rep.discrepancies,
                "unmatched_wahapedia": rep.unmatched_wahapedia,
            }
            Path(args.out).write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
            print(f"\n完整报告写入 {args.out}")


if __name__ == "__main__":
    main()
