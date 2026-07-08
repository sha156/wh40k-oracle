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

    a = sub.add_parser("aliases", help="从 data_refined 双语标题灌中文别名层（中文→canonical_id）")
    a.add_argument("--refined", default="data_refined")
    a.add_argument("--db", default="db/wh40k.sqlite")

    m = sub.add_parser("mfm", help="官方 MFM 分数：抓取/比对/应用（官方为最高真源）")
    m.add_argument("--fetch", action="store_true", help="联网抓全部阵营页（需代理）")
    m.add_argument("--slug", default=None, help="只补抓指定阵营（如 imperial-agents），合并进 JSON")
    m.add_argument("--check", action="store_true", help="与 units.points_json 比对出过期报告")
    m.add_argument("--apply", action="store_true", help="把 MFM 分数应用进 units.points_json")
    m.add_argument("--json", default="db_sources/mfm/mfm_points.json")
    m.add_argument("--db", default="db/wh40k.sqlite")

    d = sub.add_parser(
        "downloads",
        help="官方下载页版本监控：harvest 建基线 / check 比对报改版（需 3.11+scrapling 渲染）")
    d.add_argument("--harvest", action="store_true",
                   help="渲染分类页 + HEAD 元数据 → 写 manifest 基线")
    d.add_argument("--check", action="store_true",
                   help="重渲染并与 manifest diff，报 新增/改版/下架")
    d.add_argument("--manifest", default="db_sources/downloads/manifest.json")
    d.add_argument("--categories", default="warhammer-40000",
                   help="逗号分隔的游戏系统 slug（默认 warhammer-40000）")

    u = sub.add_parser(
        "update",
        help="一键刷新：BSData pull → MFM 抓取 → 重建库 → 应用分数 → 别名 → 交叉校验 → 收敛校验")
    u.add_argument("--offline", action="store_true",
                   help="跳过全部联网（git pull + MFM 抓取），复用本地缓存快速重建")
    u.add_argument("--no-fetch-mfm", action="store_true",
                   help="git pull BSData 但 MFM 复用缓存（不联网重抓分数）")
    u.add_argument("--no-check-downloads", action="store_true",
                   help="跳过官方下载页版本监控（省去 3.11 渲染的 ~30s）")
    u.add_argument("--manifest", default="db_sources/downloads/manifest.json")
    u.add_argument("--bsdata", default="db_sources/bsdata")
    u.add_argument("--csv-dir", default="db_sources/wahapedia")
    u.add_argument("--db", default="db/wh40k.sqlite")
    u.add_argument("--terms", default="wiki/terms.json")
    u.add_argument("--mfm-json", default="db_sources/mfm/mfm_points.json")
    u.add_argument("--refined", default="data_refined")

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
    elif args.cmd == "aliases":
        from db_compile.aliases import populate_aliases

        rep = populate_aliases(Path(args.db), Path(args.refined))
        print(f"中文别名层：提取 {rep['harvested']} 双语对，"
              f"匹配 canonical {rep['matched']}，未匹配 {rep['unmatched']}")
    elif args.cmd == "mfm":
        import json

        from db_compile.mfm import (apply_points, check_points, fetch_all,
                                    fetch_faction)

        json_path = Path(args.json)
        if args.fetch:
            print("抓取官方 MFM 全部阵营页…")
            fetch_all(json_path)
            print(f"写入 {json_path}")
        if args.slug:
            rows = fetch_faction(args.slug)
            data = json.loads(json_path.read_text(encoding="utf-8"))
            data["factions"][args.slug] = rows
            data["failed"] = [f for f in data.get("failed", []) if f != args.slug]
            json_path.write_text(json.dumps(data, ensure_ascii=False, indent=1),
                                 encoding="utf-8")
            print(f"补抓 {args.slug}: {len(rows)} 条，已合并进 {json_path}")
        # 顺序：apply 先于 check——同时给两个开关时语义是「应用后验证收敛」
        if args.apply:
            if not json_path.exists():
                raise SystemExit(f"{json_path} 不存在，先跑 --fetch")
            data = json.loads(json_path.read_text(encoding="utf-8"))
            factions = {slug: [tuple(r) for r in rows]
                        for slug, rows in data["factions"].items()}
            rep = apply_points(Path(args.db), factions,
                               fetched_at=data.get("fetched_at"))
            print(f"\nMFM 应用：匹配 {rep['units_matched']} 单位，"
                  f"更新 {rep['units_updated']} 个（官方分数已写入 points_json）")
            print("  注意：db_compile build 重建会覆盖，重建后需重跑 mfm --apply")
        if args.check:
            if not json_path.exists():
                raise SystemExit(f"{json_path} 不存在，先跑 --fetch")
            data = json.loads(json_path.read_text(encoding="utf-8"))
            factions = {slug: [tuple(r) for r in rows]
                        for slug, rows in data["factions"].items()}
            rep = check_points(Path(args.db), factions)
            pct = round(rep["agree"] / rep["compared"] * 100, 1) if rep["compared"] else 0
            print(f"\nMFM 比对（抓取时间 {data.get('fetched_at')}，只比基准梯度）：")
            print(f"  可比条目 {rep['compared']}  |  一致 {rep['agree']} ({pct}%)  |  "
                  f"过期 {len(rep['diffs'])}  |  MFM 有库里无 {len(rep['mfm_only'])}  |  "
                  f"梯度计价单位 {len(rep.get('tiered_units', []))}")
            if rep["diffs"]:
                print("\n  过期分数（官方 MFM 为准）：")
                for d in rep["diffs"][:40]:
                    print(f"    {d['unit'][:36]:36} {d['models']:11} "
                          f"库 {d['db']:>4} → MFM {d['mfm']:>4}")
                if len(rep["diffs"]) > 40:
                    print(f"    …共 {len(rep['diffs'])} 条，其余见 --json 报告")
    elif args.cmd == "downloads":
        from db_compile.downloads import (harvest, write_manifest, check,
                                          print_diffs)

        cats = tuple(s.strip() for s in args.categories.split(",") if s.strip())
        if args.harvest:
            m = harvest(cats)
            write_manifest(m, args.manifest)
            n = sum(len(v) for v in m["categories"].values())
            print(f"基线已建：{len(cats)} 分类 / {n} 文档 → {args.manifest}")
        if args.check:
            rep = check(args.manifest, cats)
            print_diffs(rep)
        if not (args.harvest or args.check):
            raise SystemExit("请指定 --harvest（建基线）或 --check（比对）")
    elif args.cmd == "update":
        from db_compile.update import UpdateConfig, run_update

        cfg = UpdateConfig(
            bsdata=Path(args.bsdata), csv_dir=Path(args.csv_dir), db=Path(args.db),
            terms=Path(args.terms), mfm_json=Path(args.mfm_json),
            refined=Path(args.refined), manifest=Path(args.manifest),
            offline=args.offline,
            fetch_mfm=not (args.offline or args.no_fetch_mfm),
            check_downloads=not (args.offline or args.no_check_downloads))
        report = run_update(cfg)
        raise SystemExit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
