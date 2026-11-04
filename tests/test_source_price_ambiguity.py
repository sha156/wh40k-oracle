"""Chapter-reprinted MFM prices must not hide the one canonical body (R2 regression).

The SM codex units are reprinted on every chapter MFM page. A plain English
name therefore has several ledger candidates; only the canonical identity
check may collapse them, and only to a single surviving candidate.
"""
import hashlib
import json
import sqlite3
from contextlib import closing
from pathlib import Path

import pytest

from agent import tools
from db_compile.build import build_database
from db_compile.entity_resolver import EntityResolver
from db_compile.mfm_source import write_ledger


CAPTURED = "2026-09-30T12:00:00Z"
REAL_DB = Path(__file__).resolve().parents[1] / "db" / "wh40k.sqlite"
needs_db = pytest.mark.skipif(not REAL_DB.exists(), reason="wh40k.sqlite 不存在")

UNITS = (
    # id, name, faction, faction keywords
    ("200", "Generic Captain", "SM", ["ADEPTUS ASTARTES"]),
    ("201", "Twin Hero", "SM", ["ADEPTUS ASTARTES"]),
    ("202", "Twin Hero", "AC", ["ADEPTUS CUSTODES"]),
    ("203", "Chapter Champion", "SM", ["ADEPTUS ASTARTES", "BLACK TEMPLARS"]),
)


def _row(name, cost):
    return {"kind": "unit", "section": "UNITS", "unit": name,
            "tier": "YOUR UNIT COSTS", "models": "1 model", "cost": cost}


def _snapshot():
    pages = {
        "space-marines": [_row("Generic Captain", 80), _row("Twin Hero", 100),
                          _row("Chapter Champion", 70)],
        "black-templars": [_row("Generic Captain", 80), _row("Chapter Champion", 70)],
        "adeptus-custodes": [_row("Twin Hero", 100)],
    }
    return {"fetched_at": CAPTURED, "pages": {
        slug: {"url": "https://example.invalid/" + slug,
               "sha256": hashlib.sha256(slug.encode()).hexdigest(), "rows": rows}
        for slug, rows in pages.items()}}


@pytest.fixture
def db(tmp_path):
    source = tmp_path / "csv"
    source.mkdir()
    (source / "Factions.csv").write_text(
        "id|name|link|\nSM|Space Marines|https://example.invalid|\n"
        "AC|Adeptus Custodes|https://example.invalid|\n", encoding="utf-8")
    (source / "Datasheets.csv").write_text(
        "id|name|faction_id|source_id|legend|role|loadout|transport|virtual|"
        "leader_head|leader_footer|damaged_w|damaged_description|link|\n"
        + "".join("{}|{}|{}|1||||||||||https://example.invalid|\n".format(uid, name, fac)
                  for uid, name, fac, _ in UNITS), encoding="utf-8")
    path = tmp_path / "synthetic.sqlite"
    build_database(source, path)
    with closing(sqlite3.connect(path)) as conn, conn:
        for uid, _, _, kws in UNITS:
            conn.execute("UPDATE units SET keywords_json=?, points_json=? WHERE id=?", (
                json.dumps({"keywords": ["CHARACTER"], "faction_keywords": kws}),
                json.dumps({"points": 80, "items": [{"desc": "1 model", "cost": 80}],
                            "mfm": {"current": True, "fetched_at": CAPTURED,
                                    "source_url": "https://example.invalid"}}), uid))
        write_ledger(conn, _snapshot())
    return path


def _datasheet(db, query):
    return tools.get_datasheet(query, db_path=db, resolver=EntityResolver(db_path=db))


def test_generic_unit_on_two_chapter_pages_keeps_canonical_body(db):
    assert tools._source_price_result("Generic Captain", db, EntityResolver(db_path=db)) is None
    out = _datasheet(db, "Generic Captain")
    assert out["found"] is True
    assert out.get("reason") != "ambiguous" and not out.get("points_only")
    assert out["datasheet"]["unit_id"] == "200"


def test_generic_unit_get_entity_is_not_price_only(db, tmp_path):
    wiki = tmp_path / "wiki"
    wiki.mkdir()
    out = tools.get_entity("Generic Captain", wiki_root=wiki,
                           resolver=EntityResolver(db_path=db), app_path=tmp_path / "none.py")
    assert out.get("reason") != "ambiguous" and not out.get("points_only")
    assert out["resolved_via"]["confidence"] == "exact"
    assert out["resolved_via"]["canonical_id"] == "200"


def test_same_name_in_two_canonical_factions_stays_ambiguous(db):
    out = _datasheet(db, "Twin Hero")
    assert out["found"] is False and out["reason"] == "ambiguous"
    assert sorted(c["faction_slug"] for c in out["candidates"]) == [
        "adeptus-custodes", "space-marines"]


def test_chapter_keyword_unit_resolves_to_its_body(db):
    # A BLACK TEMPLARS unit priced on both SM and BT pages: only the BT
    # candidate passes canonical_price_slug, so the body path continues.
    assert tools._source_price_result(
        "Chapter Champion", db, EntityResolver(db_path=db)) is None
    out = _datasheet(db, "Chapter Champion")
    assert out["found"] is True and not out.get("points_only")
    assert out["datasheet"]["unit_id"] == "203"


def test_body_in_one_faction_priced_in_another_stays_ambiguous(db):
    # Only same-faction chapter reprints may collapse; a Custodes price for a
    # name whose only body is SM is a different identity, not a reprint.
    with closing(sqlite3.connect(db)) as conn, conn:
        snap = _snapshot()
        snap["pages"]["adeptus-custodes"]["rows"].append(_row("Generic Captain", 80))
        write_ledger(conn, snap)
    out = _datasheet(db, "Generic Captain")
    assert out["found"] is False and out["reason"] == "ambiguous"
    assert sorted(c["faction_slug"] for c in out["candidates"]) == [
        "adeptus-custodes", "black-templars", "space-marines"]


def test_explicit_source_selector_stays_price_only(db):
    out = _datasheet(db, "@mfm:black-templars:Generic%20Captain")
    assert out["found"] is True and out["points_only"] is True
    assert out["datasheet"] is None and out["faction_slug"] == "black-templars"


@needs_db
@pytest.mark.parametrize("query,found", [
    ("Intercessor Squad", True), ("Captain", True), ("Drop Pod", True),
    ("Helbrute", False), ("罗伯特·基里曼", True),
])
def test_real_db_anchors(query, found):
    out = tools.get_datasheet(query, db_path=REAL_DB)
    assert out["found"] is found
    if found:
        assert out["datasheet"] is not None
