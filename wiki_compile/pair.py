"""流水线②：中英配对。先精确匹配，再按书多数票推断阵营、在阵营内模糊匹配。"""
from __future__ import annotations

import difflib
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

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
    # H13：canonical 中跨阵营同名条目真实存在，dict 单值会 last-write-wins
    # 静默覆盖——这里保留全部同名候选，命中多条时按本书阵营消歧。
    by_norm: Dict[str, List[CanonicalEntry]] = {}
    for c in canonical:
        by_norm.setdefault(normalize_name(c.name), []).append(c)
    result = PairingResult()
    votes: Dict[str, Counter] = {}
    leftovers: List[EntityCandidate] = []
    # 精确命中但同名多候选的条目：推迟到阵营票算完后再消歧
    ambiguous: List[Tuple[EntityCandidate, List[CanonicalEntry]]] = []

    # 第一轮：精确匹配（唯一候选才直接落定），同时为每本书累计阵营票
    for e in entities:
        cands = by_norm.get(normalize_name(e.name_en)) if e.name_en else None
        if not cands:
            leftovers.append(e)
        elif len(cands) == 1:
            c = cands[0]
            result.pairs.append(_to_pair(e, c, "exact"))
            votes.setdefault(e.book, Counter())[c.faction_id] += 1
        else:
            ambiguous.append((e, cands))

    # 每本书的阵营 = 精确命中的多数票；模糊匹配限定在本阵营内减少误配
    book_faction = {b: v.most_common(1)[0][0] for b, v in votes.items()}

    # 第二轮：同名多候选按本书推断阵营消歧；无法消歧 → 警告并计入 review_needed
    for e, cands in ambiguous:
        fid = book_faction.get(e.book)
        in_faction = [c for c in cands if fid is not None and c.faction_id == fid]
        if len(in_faction) == 1:
            c = in_faction[0]
            result.pairs.append(_to_pair(e, c, "exact"))
            votes.setdefault(e.book, Counter())[c.faction_id] += 1
        else:
            print("[pair] 警告：《{}》条目 '{}' 命中 {} 条同名 canonical"
                  "（阵营: {}），无法按本书阵营消歧，计入 review_needed".format(
                      e.book, e.name_en, len(cands),
                      "/".join(c.faction_id for c in cands)))
            result.unmatched.append(e)

    # 第三轮：模糊匹配。池内条目按本书阵营过滤后仍同名多候选的，
    # 排除出池（无法安全消歧，宁缺毋误配）。
    pools: Dict[Optional[str], Dict[str, CanonicalEntry]] = {}

    def _pool_for(fid: Optional[str]) -> Dict[str, CanonicalEntry]:
        if fid not in pools:
            pool: Dict[str, CanonicalEntry] = {}
            for n, cs in by_norm.items():
                cs_f = [c for c in cs if fid is None or c.faction_id == fid]
                if len(cs_f) == 1:
                    pool[n] = cs_f[0]
            pools[fid] = pool
        return pools[fid]

    for e in leftovers:
        if not e.name_en:
            result.unmatched.append(e)
            continue
        # 当本书无精确命中锚点时 fid 为 None，模糊匹配退化为全阵营范围
        # （confidence 仍标 "fuzzy"，但非阵营限定）。
        fid = book_faction.get(e.book)
        pool = _pool_for(fid)
        hit = difflib.get_close_matches(
            normalize_name(e.name_en), list(pool), n=1, cutoff=FUZZY_CUTOFF)
        if hit:
            result.pairs.append(_to_pair(e, pool[hit[0]], "fuzzy"))
        else:
            result.unmatched.append(e)
    return result
