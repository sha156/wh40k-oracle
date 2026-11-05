"""Actual conflict spellings in synthetic declarations; no source/body certification.

Names/IDs/ordered keywords are the five saved October 4 identity conflicts.
All database rows, prices and body evidence here are synthetic controls. The
separate acceptance harness verifies the frozen actual ledger and raw receipts.
"""
import copy
import json
import sqlite3
from contextlib import closing

import pytest

from tests.test_source_coverage import api, manifest, source


CONFLICTS = [
    ("000004201", "Berehk Stornbröw", "BEREHK STORNBRÖW", "LoV", "leagues-of-votann", ["Leagues of Votann"]),
    ("000002597", "Brôkhyr Iron-master", "BRÔKHYR IRON-MASTER", "LoV", "leagues-of-votann", ["Leagues of Votann"]),
    ("000002603", "Brôkhyr Thunderkyn", "BRÔKHYR THUNDERKYN", "LoV", "leagues-of-votann", ["Leagues of Votann"]),
    ("000002594", "Kâhl", "KÂHL", "LoV", "leagues-of-votann", ["Leagues of Votann"]),
    ("000002622", "Khârn The Betrayer", "KHÂRN THE BETRAYER", "WE", "world-eaters", ["World Eaters"]),
]


def declaration(conflict, source_only=False):
    uid, stored, published, faction, slug, keywords = conflict
    price = source("c", "web", "2026-09-30")
    return {
        "identity": {"unit_id": None if source_only else uid,
                     "name_en": published if source_only else stored,
                     "faction_id": faction, "faction_slug": slug,
                     "faction_keywords": [] if source_only else copy.deepcopy(keywords)},
        "reviewed_on": "2026-10-04",
        "body": {"status": "source_only_price" if source_only else "fields_only",
                 "scope": [] if source_only else ["keywords"], "effective_date": None,
                 "sources": [copy.deepcopy(price) if source_only else source("a")],
                 "retained_snapshot": None},
        "points": {"status": "current_published", "effective_date": None, "sources": [price]},
    }


@pytest.fixture
def unicode_db(tmp_path):
    path = tmp_path / "synthetic-unicode.sqlite"
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("CREATE TABLE factions(id TEXT PRIMARY KEY)")
        conn.executemany("INSERT INTO factions VALUES (?)", [("LoV",), ("WE",), ("SM",)])
        conn.execute("CREATE TABLE units(id TEXT PRIMARY KEY,name_en TEXT,faction_id TEXT,keywords_json TEXT,points_json TEXT)")
        for uid, stored, published, faction, slug, keywords in CONFLICTS:
            conn.execute("INSERT INTO units VALUES (?,?,?,?,?)", (
                uid, stored, faction, json.dumps({"faction_keywords": keywords}),
                json.dumps({"mfm": {"current": True}})))
        conn.execute("CREATE TABLE models(unit_id TEXT)")
        from db_compile.mfm_source import write_ledger
        price = source("c", "web", "2026-09-30")
        pages = {}
        for _, _, published, _, slug, _ in CONFLICTS:
            page = pages.setdefault(slug, {"url": price["url"], "sha256": price["sha256"], "rows": []})
            page["rows"].append({"kind": "unit", "section": "UNITS", "unit": published,
                                 "tier": "YOUR UNIT COSTS", "models": "1 model", "cost": 100})
        write_ledger(conn, {"fetched_at": price["captured_at"], "pages": pages})
    return path


def state(conn):
    """All schema/rows, including metadata absence, not merely registry counts."""
    return {name: (ddl, conn.execute('SELECT * FROM "' + name + '" ORDER BY rowid').fetchall())
            for name, ddl in conn.execute("SELECT name,sql FROM sqlite_master WHERE type='table' ORDER BY name")}


@pytest.mark.parametrize("conflict", CONFLICTS, ids=[c[2] for c in CONFLICTS])
def test_exact_stored_identity_accepts_unicode_case_price_receipt(unicode_db, conflict):
    r = declaration(conflict)
    with closing(sqlite3.connect(unicode_db)) as conn:
        before = state(conn)
        conn.execute("BEGIN")
        api().apply_coverage(conn, manifest(r), expected_records=[None])
        assert api().resolve_coverage(conn, unit_id=conflict[0]) == r
        accepted = state(conn)
        api().apply_coverage(conn, manifest(r), expected_records=[r])
        assert state(conn) == accepted
        assert conn.in_transaction
        conn.rollback()
        assert state(conn) == before


@pytest.mark.parametrize("conflict", CONFLICTS, ids=[c[2] for c in CONFLICTS])
def test_source_only_case_cannot_evade_body_exclusion_before_metadata(unicode_db, conflict):
    r = declaration(conflict, source_only=True)
    with closing(sqlite3.connect(unicode_db)) as conn:
        conn.execute("BEGIN")
        before = state(conn)
        with pytest.raises(ValueError, match="already has a canonical body"):
            api().apply_coverage(conn, manifest(r), expected_records=[None])
        assert state(conn) == before
        assert conn.in_transaction


@pytest.mark.parametrize("name", [
    "Kahl", "Kàhl", "Kâhl Captain", "Kâhls", "Kâhl  ", " Kâhl", "Kâhl!", "Kâhl\u0301",
    "Brôkhyr Iron master", "Brôkhyr  Iron-master", "Brôkhyr Iron-masters", "Khârn",
    "Khârn The Betrayers", "KHARN THE BETRAYER", "Khârn The Betrayer in Armour",
])
def test_canonical_id_requires_literal_stored_name_even_when_ledger_case_matches(unicode_db, name):
    r = declaration(CONFLICTS[3])
    r["identity"]["name_en"] = name
    with closing(sqlite3.connect(unicode_db)) as conn:
        conn.execute("BEGIN")
        before = state(conn)
        with pytest.raises(ValueError, match="canonical coverage identity|Invalid name_en"):
            api().apply_coverage(conn, manifest(r), expected_records=[None])
        assert state(conn) == before


@pytest.mark.parametrize("name", ["KAHL", "KÀHL", "KÂHLS", "KÂHL CAPTAIN", "KÂHL!", "KÂHL  CAPTAIN",
                                  "K\u0041\u0302HL", "KHÂRN", "KHARN THE BETRAYER", "BRÔKHYR IRON MASTER"])
def test_source_only_nearby_name_cannot_borrow_full_name_price_receipt(unicode_db, name):
    r = declaration(CONFLICTS[3], source_only=True)
    r["identity"]["name_en"] = name
    with closing(sqlite3.connect(unicode_db)) as conn:
        conn.execute("BEGIN")
        before = state(conn)
        with pytest.raises(ValueError, match="published price provenance"):
            api().apply_coverage(conn, manifest(r), expected_records=[None])
        assert state(conn) == before


@pytest.mark.parametrize("change,match", [
    (lambda r: r["identity"].update(unit_id="000002603"), "canonical coverage identity"),
    (lambda r: r["identity"].update(name_en="KÂHL"), "canonical coverage identity"),
    (lambda r: r["identity"].update(faction_id="WE"), "canonical coverage identity"),
    (lambda r: r["identity"].update(faction_slug="world-eaters"), "source faction"),
    (lambda r: r["identity"].update(faction_keywords=["LEAGUES OF VOTANN"]), "faction keywords"),
    (lambda r: r["points"]["sources"][0].update(sha256="b" * 64), "price provenance"),
    (lambda r: r["points"]["sources"][0].update(captured_at="2026-10-01T12:00:00Z"), "price provenance"),
    (lambda r: r["points"]["sources"][0].update(url="https://example.invalid/wrong/prices"), "price provenance"),
])
def test_unicode_identity_and_price_proof_remain_strict(unicode_db, change, match):
    r = declaration(CONFLICTS[3])
    change(r)
    with closing(sqlite3.connect(unicode_db)) as conn:
        conn.execute("BEGIN")
        before = state(conn)
        with pytest.raises(ValueError, match=match):
            api().apply_coverage(conn, manifest(r), expected_records=[None])
        assert state(conn) == before
        assert conn.in_transaction


def test_unicode_price_requires_every_fold_equivalent_unit_row_provenance(unicode_db):
    r = declaration(CONFLICTS[3])
    extra = source("d", "web", "2026-09-30")
    with closing(sqlite3.connect(unicode_db)) as conn:
        # Synthetic second source/conditional tier and a different-case spelling.
        conn.execute("INSERT INTO official_mfm_points SELECT faction_slug,999,kind,section,?,tier,models,150,"
                     "?,?,? FROM official_mfm_points WHERE kind='unit' AND faction_slug='leagues-of-votann' AND unit_name='KÂHL'", (
                         "kâhl", extra["url"], extra["sha256"], extra["captured_at"]))
        # Enhancement and a different faction must not contaminate unit evidence.
        conn.execute("INSERT INTO official_mfm_points SELECT faction_slug,1000,'enhancement',section,unit_name,"
                     "tier,models,cost,?,?,? FROM official_mfm_points WHERE kind='unit' AND faction_slug='leagues-of-votann' AND unit_name='KÂHL'", (
                         "https://example.invalid/excluded", "e" * 64, extra["captured_at"]))
        conn.execute("INSERT INTO official_mfm_points SELECT 'world-eaters',1001,kind,section,unit_name,"
                     "tier,models,cost,?,?,? FROM official_mfm_points WHERE kind='unit' AND faction_slug='leagues-of-votann' AND unit_name='KÂHL'", (
                         "https://example.invalid/excluded-faction", "f" * 64, extra["captured_at"]))
        conn.commit()
        conn.execute("BEGIN")
        before = state(conn)
        with pytest.raises(ValueError, match="price provenance"):
            api().apply_coverage(conn, manifest(r), expected_records=[None])
        assert state(conn) == before
        r["points"]["sources"].append(extra)
        api().apply_coverage(conn, manifest(r), expected_records=[None])
        assert api().resolve_coverage(conn, unit_id=CONFLICTS[3][0]) == r
        for table in before:
            assert state(conn)[table] == before[table]
        conn.rollback()
        assert state(conn) == before


def test_fold_equivalent_canonical_duplicates_exclude_source_only_without_guessing(unicode_db):
    with closing(sqlite3.connect(unicode_db)) as conn:
        conn.execute("INSERT INTO units SELECT 'duplicate', 'KÂHL', faction_id,keywords_json,points_json "
                     "FROM units WHERE id='000002594'")
        conn.commit()
        conn.execute("BEGIN")
        before = state(conn)
        with pytest.raises(ValueError, match="already has a canonical body"):
            api().apply_coverage(conn, manifest(declaration(CONFLICTS[3], True)), expected_records=[None])
        assert state(conn) == before
        # Canonical resolution still requires its explicit ID and literal name.
        r = declaration(CONFLICTS[3])
        api().apply_coverage(conn, manifest(r), expected_records=[None])
        assert api().resolve_coverage(conn, unit_id="000002594") == r
        assert api().resolve_coverage(conn, unit_id="duplicate") is None


def test_late_unicode_price_mismatch_preserves_accepted_history_and_caller_work(unicode_db):
    r = declaration(CONFLICTS[3])
    r["reviewed_on"] = "2026-10-03"
    with closing(sqlite3.connect(unicode_db)) as conn:
        conn.execute("BEGIN")
        api().apply_coverage(conn, manifest(r), expected_records=[None])
        conn.execute("SAVEPOINT caller_owned")
        changed = copy.deepcopy(r)
        changed["reviewed_on"] = "2026-10-04"
        late = declaration(CONFLICTS[4])
        late["points"]["sources"][0]["sha256"] = "d" * 64
        before = state(conn)
        with pytest.raises(ValueError, match="price provenance"):
            api().apply_coverage(conn, manifest(changed, late), expected_records=[r, None])
        assert state(conn) == before
        assert api().resolve_coverage(conn, unit_id=CONFLICTS[3][0]) == r
        assert conn.in_transaction
        conn.execute("RELEASE SAVEPOINT caller_owned")


def test_wrong_chapter_is_not_rescued_by_unicode_name_match(unicode_db):
    r = declaration(CONFLICTS[3])
    r["identity"].update(faction_id="SM", faction_slug="blood-angels",
                         faction_keywords=["Adeptus Astartes", "Ultramarines"])
    with closing(sqlite3.connect(unicode_db)) as conn:
        conn.execute("UPDATE units SET faction_id='SM', keywords_json=? WHERE id='000002594'", (
            json.dumps({"faction_keywords": r["identity"]["faction_keywords"]}),))
        conn.commit()
        conn.execute("BEGIN")
        before = state(conn)
        with pytest.raises(ValueError, match="source chapter"):
            api().apply_coverage(conn, manifest(r), expected_records=[None])
        assert state(conn) == before
