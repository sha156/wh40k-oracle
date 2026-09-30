"""Copied-DB ID helpers stay lazy while real name resolution stays local."""
import json
import sqlite3
from contextlib import closing

import pytest

from agent import tools
from db_compile.entity_resolver import EntityResolver
from db_compile.mfm_source import write_ledger
from db_compile.schema import ALL_DDL, ensure_columns


def _no_default_resolver():
    pytest.fail("Copied-DB lookup attempted to use the production resolver")


@pytest.fixture
def minimal_db(tmp_path):
    path = tmp_path / "minimal.sqlite"
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("CREATE TABLE units(id TEXT,name_en TEXT,points_json TEXT)")
        conn.executemany("INSERT INTO units VALUES(?,?,?)", [
            ("fixture", "Synthetic canonical ID", json.dumps({"points": 123})),
            ("unpriced", "Synthetic unpriced ID", None),
            ("retired", "Synthetic retired ID", json.dumps({
                "points": 155, "mfm": {"current": False}})),
        ])
    return path


@pytest.mark.parametrize("queries,prices", [
    (["fixture"], [123]),
    (["unpriced"], [None]),
    (["retired"], [None]),
    (["fixture", "retired", "unpriced", "fixture"], [123, None, None, 123]),
    ([], []),
])
def test_minimal_direct_ids_need_no_datasheets_or_resolver(minimal_db, monkeypatch, queries, prices):
    before = minimal_db.read_bytes()
    monkeypatch.setattr(tools, "_get_default_resolver", _no_default_resolver)
    result = tools.calc_points(queries, db_path=minimal_db)
    assert result["found"] is True
    assert [row["unit_id"] for row in result["units"]] == queries
    assert [row["points"] for row in result["units"]] == prices
    assert not result.get("unresolved")
    assert minimal_db.read_bytes() == before


@pytest.fixture
def copied_db(tmp_path):
    path = tmp_path / "copied.sqlite"
    with closing(sqlite3.connect(path)) as conn, conn:
        for ddl in ALL_DDL:
            conn.executescript(ddl)
        ensure_columns(conn)
        conn.execute("INSERT INTO factions(id,name) VALUES('SM','Space Marines')")
        for uid, name, cost in [("squad", "Current Squad", 90), ("kaius", "Kaius Alpha", 999)]:
            conn.execute("INSERT INTO datasheets(id,name,faction_id) VALUES(?,?,'SM')", (uid, name))
            conn.execute("INSERT INTO units(id,name_en,faction_id,points_json) VALUES(?,?,'SM',?)", (
                uid, name, json.dumps({"points": cost})))
        write_ledger(conn, {"fetched_at": "2026-09-30T12:00:00Z", "pages": {
            "space-marines": {"url": "https://example.invalid/space-marines", "sha256": "a" * 64,
                              "rows": [{"kind": "unit", "section": "UNITS", "unit": name,
                                        "tier": "YOUR UNIT COSTS", "models": "1 model", "cost": cost}
                                       for name, cost in [("Kaius", 100), ("Kaius (Prototype)", 110)]]}}})
    return path


@pytest.mark.parametrize("query,uid,cost,confidence", [
    ("Current Squad", "squad", 90, "exact"),
    ("Current Squd", "squad", 90, "fuzzy"),
    ("Kaius Alpha", "kaius", 999, "exact"),
])
def test_actual_name_and_fuzzy_resolution_use_copied_database(copied_db, monkeypatch, query, uid, cost, confidence):
    monkeypatch.setattr(tools, "_get_default_resolver", _no_default_resolver)
    before = copied_db.read_bytes()
    result = tools.calc_points(["squad", query], db_path=copied_db)["units"]
    assert result[0]["unit_id"] == "squad" and result[0]["points"] == 90
    assert result[1]["unit_id"] == uid and result[1]["points"] == cost
    assert result[1]["resolved_via"]["confidence"] == confidence
    if confidence == "fuzzy":
        assert tools._FUZZY_DECLARE_NOTE in result[1]["note"]
    assert copied_db.read_bytes() == before


@pytest.mark.parametrize("query,name,cost", [
    ("Kaius", "Kaius", 100),
    ("Kaius (space-marines)", "Kaius", 100),
    ("Kaius (Prototype)", "Kaius (Prototype)", 110),
    ("Kaius (Prototype) (space-marines)", "Kaius (Prototype)", 110),
])
def test_lazy_resolution_preserves_exact_ledger_before_fuzzy_and_full_variant(copied_db, monkeypatch, query, name, cost):
    monkeypatch.setattr(tools, "_get_default_resolver", _no_default_resolver)
    hit = EntityResolver(db_path=copied_db).resolve("Kaius")
    assert hit.canonical_id == "kaius" and hit.confidence == "fuzzy"
    before = copied_db.read_bytes()
    row = tools.calc_points([query], db_path=copied_db)["units"][0]
    assert row["unit_id"] is None and row["points_only"]
    assert row["name_en"] == name and row["points"] == cost
    assert row["faction_slug"] == "space-marines"
    assert not row.get("resolved_via")
    assert copied_db.read_bytes() == before


def test_unresolved_copied_name_never_uses_production_resolver(copied_db, monkeypatch):
    monkeypatch.setattr(tools, "_get_default_resolver", _no_default_resolver)
    before = copied_db.read_bytes()
    result = tools.calc_points(["Entirely Unknown Unit"], db_path=copied_db)
    assert result["unresolved"] == ["Entirely Unknown Unit"]
    assert result["units"][0]["points"] is None
    assert result["units"][0]["unresolved"]
    assert copied_db.read_bytes() == before


def test_injected_resolver_is_retained_for_mixed_id_and_name_queries(copied_db, monkeypatch):
    resolver = EntityResolver(db_path=copied_db)

    def unexpected_construction(*args, **kwargs):
        pytest.fail("Injected resolver was replaced")

    monkeypatch.setattr(tools, "EntityResolver", unexpected_construction)
    monkeypatch.setattr(tools, "_get_default_resolver", _no_default_resolver)
    before = copied_db.read_bytes()
    result = tools.calc_points(["squad", "Current Squad"], db_path=copied_db, resolver=resolver)
    assert [row["points"] for row in result["units"]] == [90, 90]
    assert copied_db.read_bytes() == before
