"""Read the complete official price ledger, including prices without datasheets."""
from contextlib import closing
import json
from pathlib import Path
import re
import sqlite3


def browse(db_path, query="", offset=0, limit=50):
    with closing(sqlite3.connect(f"file:{Path(db_path).resolve().as_posix()}?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='official_mfm_points'").fetchone():
            raise ValueError("官方完整点数快照尚未同步")
        query = query.strip().casefold()
        rows = [dict(r) for r in conn.execute("SELECT * FROM official_mfm_points ORDER BY faction_slug,ordinal")]
        matches = [r for r in rows if not query or query in (r["unit_name"] + " " + r["models"] + " " + r["faction_slug"]).casefold()]
        return {"total": len(matches), "sourceRows": len(rows), "offset": offset,
                "fetchedAt": rows[0]["fetched_at"] if rows else None,
                "rows": matches[offset:offset + limit]}


def exact_unit(db_path, name, *, faction_slug=None):
    """Return exact price evidence, never a fuzzy body or a merged faction identity.

    Internal callers may supply an exact source slug. Existing name-only callers
    can round-trip candidates as ``Full Variant (source-slug)``. A full ledger
    name (including parentheses) takes precedence over interpreting a suffix.
    Canonical faction codes do not stand in for source slugs/chapter identities.
    Capture timestamps do not establish source publication or effective dates.
    """
    from db_compile.mfm import is_base_tier
    from db_compile.point_tiers import minimum_unit_cost

    if not isinstance(name, str) or not name.strip():
        return None
    name = name.strip()
    if faction_slug is not None:
        if not isinstance(faction_slug, str):
            return None
        faction_slug = faction_slug.strip().casefold()
    # Read all unit rows: pagination/topK must not hide an exact identity or one
    # of its factions/conditional tiers. The ledger itself remains untouched.
    with closing(sqlite3.connect(f"file:{Path(db_path).resolve().as_posix()}?mode=ro", uri=True)) as conn:
        conn.row_factory = sqlite3.Row
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE name='official_mfm_points'").fetchone():
            raise ValueError("官方完整点数快照尚未同步")
        ledger = [dict(r) for r in conn.execute(
            "SELECT * FROM official_mfm_points WHERE kind='unit' ORDER BY faction_slug,ordinal")]
    rows = [r for r in ledger if r["unit_name"].casefold() == name.casefold()]
    if not rows and faction_slug is None:
        qualified = re.fullmatch(r"(.+)\s*[（(]\s*([a-z0-9]+(?:-[a-z0-9]+)*)\s*[)）]", name, re.I)
        if qualified:
            name = qualified[1].strip()
            faction_slug = qualified[2].casefold()
            rows = [r for r in ledger if r["unit_name"].casefold() == name.casefold()]
    if faction_slug is not None:
        rows = [r for r in rows if r["faction_slug"] == faction_slug]
    if not rows:
        return None

    candidates = []
    for slug in sorted({r["faction_slug"] for r in rows}):
        prices = [r for r in rows if r["faction_slug"] == slug]
        candidates.append({
            "name_en": prices[0]["unit_name"], "faction_slug": slug,
            "query": "{} ({})".format(prices[0]["unit_name"], slug),
            "points": minimum_unit_cost([
                {"desc": r["models"], "cost": r["cost"]}
                for r in prices if is_base_tier(r["tier"])]),
            "official_prices": prices,
        })
    ambiguous = len(candidates) != 1
    sources = []
    for row in rows:
        source = {"url": row["source_url"], "sha256": row.get("source_sha256"),
                  "captured_at": row["fetched_at"], "source_date": None}
        if source not in sources:
            sources.append(source)
    scope = ("仅为官方 MFM 已发布点数证据，不提供或认证完整兵牌、装备/编成合法性或模拟规则。"
             "抓取时间不是规则/点数生效日期；生效日期尚未验证。")
    captures = "、".join(sorted({str(s["captured_at"]) for s in sources}))
    note = "点数源抓取时间：" + captures + "。 " + scope
    if ambiguous:
        note += " 同名跨来源阵营，价格相同也不表示同一身份；请用 candidates.query 精确选择来源阵营。"
    return {"unit_id": None, "name_en": rows[0]["unit_name"],
            "faction_slug": None if ambiguous else candidates[0]["faction_slug"],
            "points": None if ambiguous else candidates[0]["points"],
            # Scope/capture qualifiers precede bulk tiers in bounded digests.
            "points_only": True, "price_status": "current_published",
            "effective_date": None, "source_scope": scope, "note": note,
            "ambiguous": ambiguous, "candidates": candidates if ambiguous else [],
            "price_sources": sources, "official_prices": rows}


def _canonical_identity_matches(db_path, unit_id, price):
    """Keep a canonical price path only for the same full variant/faction/chapter.

    This is an identity check, not a body-coverage or legality certification.
    Source-slug chapter distinctions are never collapsed by equal prices.
    """
    from db_compile.mfm import MFM_SLUG_TO_FACTION

    slug = price.get("faction_slug")
    if price.get("ambiguous") or slug not in MFM_SLUG_TO_FACTION:
        return False
    with closing(sqlite3.connect(f"file:{Path(db_path).resolve().as_posix()}?mode=ro", uri=True)) as conn:
        row = conn.execute("SELECT name_en,faction_id,keywords_json FROM units WHERE id=?", (unit_id,)).fetchone()
    if (not row or row[0].casefold() != price["name_en"].casefold()
            or row[1] != MFM_SLUG_TO_FACTION[slug]):
        return False
    if row[1] == "SM" and slug != "space-marines":
        try:
            keywords = json.loads(row[2] or "{}").get("faction_keywords", [])
        except (ValueError, AttributeError, TypeError):
            return False
        if not isinstance(keywords, list) or slug.replace("-", " ") not in {
                kw.casefold() for kw in keywords if isinstance(kw, str)}:
            return False
    return True
