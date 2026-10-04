"""Explicit string selectors round-trip through the actual SQLite price tool."""
from contextlib import closing
import json
import sqlite3
from urllib.parse import quote

import pytest

from agent import tools
from db_compile.mfm_source import write_ledger
from db_compile.schema import ALL_DDL, ensure_columns
from db_compile.source_archive import project_deleted_details
from web_api.official_points import exact_unit


def source(name, slug="space-marines"):
    return "@mfm:" + slug + ":" + quote(name, safe="")


def literal(name):
    return "@literal:" + quote(name, safe="")


SPECIAL_NAMES = [
    "Kaius (Prototype)", "战士（试验型）", "Hero's \"quoted\" variant",
    "Hero: 100% / # ? + &", "@mfm:space-marines:Kaius",
    "@literal:Kaius", "%28Prototype%29", "Nested (Model (II))",
]


@pytest.fixture
def db(tmp_path):
    path = tmp_path / "selector.sqlite"
    with closing(sqlite3.connect(path)) as conn, conn:
        for ddl in ALL_DDL:
            conn.executescript(ddl)
        ensure_columns(conn)
        conn.execute("INSERT INTO factions(id,name) VALUES('SM','Space Marines')")
        for uid, name, cost, current in [
            ("canonical", "Current Squad", 90, True),
            ("alpha", "Kaius Alpha", 999, True),
            ("armour", "Marneus Calgar in Armour of Antilochus", 155, False),
            ("variant", "Canonical (Prototype)", 130, True),
            (source("Kaius"), "ID grammar collision", 888, True),
        ]:
            conn.execute("INSERT INTO datasheets(id,name,faction_id) VALUES(?,?,'SM')", (uid, name))
            conn.execute("INSERT INTO units(id,name_en,faction_id,points_json) VALUES(?,?,'SM',?)", (
                uid, name, json.dumps({"points": cost, "items": [{"desc": "1 model", "cost": cost}],
                                      "mfm": {"current": current}})))

        def row(name, cost, models="1 model", tier="YOUR UNIT COSTS"):
            return {"kind": "unit", "section": "UNITS", "unit": name,
                    "tier": tier, "models": models, "cost": cost}

        sm = [row("Shared Hero", 120), row("Shared Hero", 220, "2 models"),
              row("Kaius", 100), row("Kaius", 150, tier="YOUR 2ND UNIT COSTS"),
              row("Kaius", 10, "+ 1 Weapon", "YOUR WARGEAR COSTS"),
              row("Marneus Calgar", 180), row("Marneus Calgar", 300, "2 models")]
        for name in SPECIAL_NAMES:
            sm.extend([row(name, 110), row(name, 210, "2 models")])
        pages = {"space-marines": sm, "adeptus-custodes": [
            row("Shared Hero", 120), row("Shared Hero (space-marines)", 777),
            *[row(name, 310) for name in SPECIAL_NAMES]]}
        write_ledger(conn, {"fetched_at": "2026-09-30T12:00:00Z", "pages": {
            slug: {"url": "https://example.invalid/" + slug, "sha256": "a" * 64, "rows": rows}
            for slug, rows in pages.items()}})
    project_deleted_details(path, details=[{
        "id": 6, "name_en": "Marneus Calgar", "name_zh": "马涅乌斯.卡尔加（已删除）",
        "faction_zh": "极限战士", "score": 200,
        "composition": "Marneus Calgar and two Victrix Honour Guard"}])
    return path


def calculate(db, query):
    before = db.read_bytes()
    result = tools.calc_points([query], db_path=db)["units"][0]
    assert db.read_bytes() == before
    return result


def test_emitted_selector_selects_advertised_sm120_not_literal_custodes777(db):
    candidates = exact_unit(db, "Shared Hero")["candidates"]
    selected = next(c for c in candidates if c["faction_slug"] == "space-marines")
    row = calculate(db, selected["query"])
    assert (row["name_en"], row["faction_slug"], row["points"]) == ("Shared Hero", "space-marines", 120)
    assert [p["cost"] for p in row["official_prices"]] == [120, 220]
    full = calculate(db, literal("Shared Hero (space-marines)"))
    assert (full["name_en"], full["faction_slug"], full["points"]) == ("Shared Hero (space-marines)", "adeptus-custodes", 777)


@pytest.mark.parametrize("name", SPECIAL_NAMES)
def test_all_emitted_variants_and_factions_roundtrip_all_tiers(db, name):
    # Explicit literal escaping disables suffix parsing even for reserved names.
    ambiguous = calculate(db, literal(name))
    assert ambiguous["ambiguous"] and ambiguous["points"] is None
    assert len(ambiguous["candidates"]) == 2
    for candidate in ambiguous["candidates"]:
        structured = exact_unit(db, candidate["name_en"], faction_slug=candidate["faction_slug"])
        assert structured["official_prices"] == candidate["official_prices"]
        row = calculate(db, candidate["query"])
        assert (row["name_en"], row["faction_slug"], row["points"]) == (
            candidate["name_en"], candidate["faction_slug"], candidate["points"])
        assert row["official_prices"] == candidate["official_prices"]
        assert row["unit_id"] is None and row["points_only"]
        assert not {"models", "weapons", "datasheet", "canonical_id"} & row.keys()


@pytest.mark.parametrize("query", [
    "@mfm:", "@mfm:space-marines:", "@mfm:SM:Kaius", "@mfm:unknown:Kaius",
    "@mfm:adeptus-custodes:Kaius", "@mfm:space-marines:Kaius%ZZ",
    "@mfm:space-marines:Kaius%", "@mfm:space-marines:%FF", "@mfm:space-marines:%4Baius",
    "@mfm:space-marines:Kaius%20", "@mfm:space-marines:Kaius Alpha",
    "@mfm:space-marines:Unknown", "@literal:", "@literal:Kaius%ZZ",
    "@literal:Kaius%", "@literal:Unknown", "@literal:Kaius%00",
])
def test_malformed_unknown_or_wrong_source_selectors_never_fall_back(db, query, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Explicit selector reached canonical, archive or fuzzy resolution")
    monkeypatch.setattr(tools, "EntityResolver", forbidden)
    monkeypatch.setattr(tools, "_resolve_for_points", forbidden)
    monkeypatch.setattr(tools, "_archived_record", forbidden)
    row = calculate(db, query)
    assert row["unresolved"] and row["points"] is None and row["unit_id"] is None
    assert not row.get("official_prices")


@pytest.mark.parametrize("query", ["Shared Hero (space-marines)", "Shared Hero（space-marines）"])
def test_colliding_legacy_suffix_fails_closed_with_explicit_recovery(db, query):
    row = calculate(db, query)
    assert row["unresolved"] and row["points"] is None
    assert "@mfm:" in row["note"] and "@literal:" in row["note"]


@pytest.mark.parametrize("query,cost,uid", [
    ("canonical", 90, "canonical"), ("Current Squad", 90, "canonical"),
    ("Canonical (Prototype)", 130, "variant"), ("armour", None, "armour"),
    ("Marneus Calgar in Armour of Antilochus", None, "armour"),
])
def test_canonical_id_literal_parenthetical_and_noncurrent_preservation(db, query, cost, uid):
    row = calculate(db, query)
    assert row["unit_id"] == uid and row["points"] == cost
    assert not row.get("official_prices")


def test_explicit_selector_beats_identical_canonical_id_and_unrelated_fuzzy_name(db):
    row = calculate(db, source("Kaius"))
    assert row["points"] == 100 and row["unit_id"] is None and row["name_en"] == "Kaius"
    assert [p["cost"] for p in row["official_prices"]] == [100, 150, 10]


def test_ordinary_current180_history200_and_armour155_stay_separate(db):
    ordinary = calculate(db, "Marneus Calgar")
    assert ordinary["points"] == 180 and ordinary["historical_points"] == 200
    assert [p["cost"] for p in ordinary["official_prices"]] == [180, 300]
    selected = calculate(db, source("Marneus Calgar"))
    assert selected["points"] == 180 and selected["unit_id"] is None
    assert not selected.get("historical_record")
    assert calculate(db, "armour")["points"] is None


def test_safe_legacy_source_name_keeps_all_tiers(db):
    row = calculate(db, "Kaius (space-marines)")
    assert row["name_en"] == "Kaius" and row["faction_slug"] == "space-marines"
    assert [p["cost"] for p in row["official_prices"]] == [100, 150, 10]


@pytest.mark.parametrize("query", ["Kaius (adeptus-custodes)", "Kaius (SM)",
                                   "Kaius (unknown)", "Unknown (space-marines)"])
def test_unknown_legacy_source_intent_never_borrows_another_name_or_faction(db, query, monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("Unmatched legacy source selector reached fuzzy name resolution")
    monkeypatch.setattr(tools, "_resolve_for_points", forbidden)
    row = calculate(db, query)
    assert row["unresolved"] and row["points"] is None and row["unit_id"] is None
