"""双语术语表产出（P0 最终交付物）与读取。"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict

from wiki_compile.pair import PairingResult


def write_terms(result: PairingResult, wiki_dir: Path) -> None:
    wiki_dir.mkdir(parents=True, exist_ok=True)
    data = {"source": "wahapedia wh40k10ed",
            "pairs": [asdict(p) for p in result.pairs]}
    (wiki_dir / "terms.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = ["# 双语术语总表", "",
             "| 中文名 | 英文名 | 置信 | 来源书 | 页 |",
             "|--------|--------|------|--------|----|"]
    for p in sorted(result.pairs, key=lambda p: (p.book, p.en)):
        lines.append("| {} | {} | {} | {} | {} |".format(
            p.zh or "—", p.en, p.confidence, p.book,
            ",".join(str(n) for n in p.pages)))
    (wiki_dir / "terms.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    rl = ["# 待人工校对（未配对实体）", ""]
    for e in result.unmatched:
        rl.append("- 《{}》 p{}：{}".format(
            e.book, ",".join(str(n) for n in e.pages), e.raw_heading))
    (wiki_dir / "review_needed.md").write_text("\n".join(rl) + "\n",
                                               encoding="utf-8")


def load_term_aliases(path: Path) -> Dict[str, str]:
    """terms.json → {中文名: canonical英文名}。缺失/损坏返回空表（检索层可安全降级）。"""
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {p["zh"]: p["en"] for p in data.get("pairs", [])
            if p.get("zh") and p.get("en")}
