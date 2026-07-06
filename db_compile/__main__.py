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

    args = ap.parse_args()
    if args.cmd == "build":
        report = build_database(Path(args.csv_dir), Path(args.db), Path(args.terms))
        print("行数:", report.row_counts)
        if report.missing_csv:
            print("待下载 CSV：", ", ".join(report.missing_csv))


if __name__ == "__main__":
    main()
