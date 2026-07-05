"""流水线②：中英配对。先精确匹配，再按书多数票推断阵营、在阵营内模糊匹配。"""
from __future__ import annotations

import difflib
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from wiki_compile.canonical import CanonicalEntry
from wiki_compile.extract import EntityCandidate

# ’‘ 弯引号、–— 长短横线（PDF 提取常见）→ 归一到 ASCII
_PUNCT_MAP = str.maketrans(
    {"\u2019": "'", "\u2018": "'", "\u2013": "-", "\u2014": "-"})
FUZZY_CUTOFF = 0.85


def normalize_name(name: str) -> str:
    s = name.translate(_PUNCT_MAP).upper()
    s = re.sub(r"[^A-Z0-9' \-]", " ", s)
    return " ".join(s.split())


@dataclass
class Pair:
    zh: Optional[str]
    en: str
    canonical_id: str
    faction_id: str
    book: str
    pages: List[int]
    confidence: str  # exact / fuzzy / llm


@dataclass
class PairingResult:
    pairs: List[Pair] = field(default_factory=list)
    unmatched: List[EntityCandidate] = field(default_factory=list)


def _to_pair(e: EntityCandidate, c: CanonicalEntry, confidence: str) -> Pair:
    return Pair(zh=e.name_zh, en=c.name, canonical_id=c.id,
                faction_id=c.faction_id, book=e.book, pages=list(e.pages),
                confidence=confidence)


def pair_entities(entities: List[EntityCandidate],
                  canonical: List[CanonicalEntry]) -> PairingResult:
    by_norm: Dict[str, CanonicalEntry] = {
        normalize_name(c.name): c for c in canonical}
    result = PairingResult()
    votes: Dict[str, Counter] = {}
    leftovers: List[EntityCandidate] = []

    # 第一轮：精确匹配，同时为每本书累计阵营票
    for e in entities:
        c = by_norm.get(normalize_name(e.name_en)) if e.name_en else None
        if c is not None:
            result.pairs.append(_to_pair(e, c, "exact"))
            votes.setdefault(e.book, Counter())[c.faction_id] += 1
        else:
            leftovers.append(e)

    # 每本书的阵营 = 精确命中的多数票；模糊匹配限定在本阵营内减少误配
    book_faction = {b: v.most_common(1)[0][0] for b, v in votes.items()}
    for e in leftovers:
        if not e.name_en:
            result.unmatched.append(e)
            continue
        # 当本书无精确命中锚点时 fid 为 None，模糊匹配退化为全阵营范围
        # （confidence 仍标 "fuzzy"，但非阵营限定）。
        fid = book_faction.get(e.book)
        pool = [n for n, c in by_norm.items()
                if fid is None or c.faction_id == fid]
        hit = difflib.get_close_matches(
            normalize_name(e.name_en), pool, n=1, cutoff=FUZZY_CUTOFF)
        if hit:
            result.pairs.append(_to_pair(e, by_norm[hit[0]], "fuzzy"))
        else:
            result.unmatched.append(e)
    return result
