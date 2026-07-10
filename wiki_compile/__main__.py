"""CLI：python -m wiki_compile <extract|fetch-canonical|pair|terms>"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from wiki_compile.canonical import fetch_tables, load_canonical
from wiki_compile.extract import EntityCandidate, extract_entities
from wiki_compile.pair import PairingResult, pair_entities
from wiki_compile.pair_llm import run_llm_fallback
from wiki_compile.terms import write_terms


def main() -> None:
    ap = argparse.ArgumentParser(prog="wiki_compile")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("extract", help="扫描 data_refined 产出实体清单")
    p.add_argument("--data", default="data_refined")
    p.add_argument("--out", default="wiki_build/entities.json")

    p = sub.add_parser("fetch-canonical", help="下载 Wahapedia CSV（需代理）")
    p.add_argument("--dest", default="db_sources/wahapedia")

    p = sub.add_parser("pair", help="中英配对")
    p.add_argument("--entities", default="wiki_build/entities.json")
    p.add_argument("--canonical", default="db_sources/wahapedia")
    p.add_argument("--out", default="wiki_build/pairing.json")
    p.add_argument("--llm", action="store_true", help="启用 LLM 兜底")

    p = sub.add_parser("terms", help="生成 wiki/terms.*")
    p.add_argument("--pairing", default="wiki_build/pairing.json")
    p.add_argument("--wiki", default="wiki")

    args = ap.parse_args()
    if args.cmd == "extract":
        ents = extract_entities(Path(args.data))
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps([asdict(e) for e in ents],
                                  ensure_ascii=False, indent=1),
                       encoding="utf-8")
        print("实体数:", len(ents))
    elif args.cmd == "fetch-canonical":
        fetch_tables(Path(args.dest))
    elif args.cmd == "pair":
        raw = json.loads(Path(args.entities).read_text(encoding="utf-8"))
        ents = [EntityCandidate(**e) for e in raw]
        canonical = load_canonical(Path(args.canonical))
        result = pair_entities(ents, canonical)
        if args.llm:
            result = run_llm_fallback(result, canonical,
                                      Path("wiki_build/llm_cache"))
        out = Path(args.out)
        # 关键产物原子写（写 .tmp + os.replace），中途崩溃不留半截 pairing.json
        from wiki_engine._io import atomic_write_text
        atomic_write_text(out, json.dumps(
            {"pairs": [asdict(p) for p in result.pairs],
             "unmatched": [asdict(e) for e in result.unmatched]},
            ensure_ascii=False, indent=1))
        print("配对:", len(result.pairs), "未配对:", len(result.unmatched))
    elif args.cmd == "terms":
        from wiki_compile.pair import Pair
        raw = json.loads(Path(args.pairing).read_text(encoding="utf-8"))
        result = PairingResult(
            pairs=[Pair(**p) for p in raw["pairs"]],
            unmatched=[EntityCandidate(**e) for e in raw["unmatched"]])
        write_terms(result, Path(args.wiki))
        print("已生成", args.wiki, "/terms.json terms.md review_needed.md")


if __name__ == "__main__":
    main()
