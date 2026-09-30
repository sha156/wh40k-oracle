"""Synthetic-only coverage contract and caller-owned atomic promotion tests."""
import copy
import importlib
import json
import sqlite3
from contextlib import closing

import pytest


def api():
    # Deferred import permits the same test matrix to demonstrate that the exact
    # frozen base has no coverage contract, rather than failing at collection.
    return importlib.import_module("db_compile.source_coverage")


def source(digest="a", kind="pdf", day="2026-09-14"):
    return {"url": "https://example.invalid/" + digest + (".pdf" if kind != "web" else "/prices"),
            "sha256": digest * 64, "kind": kind, "page": None if kind == "web" else 7,
            "source_date": day, "captured_at": day + "T12:00:00Z"}


def record(uid="armour", status="current_full_verified"):
    identity = {"unit_id": uid, "name_en": "Marneus Calgar in Armour of Antilochus",
                "faction_id": "SM", "faction_slug": "space-marines",
                "faction_keywords": ["ADEPTUS ASTARTES", "ULTRAMARINES"]}
    full = status in ("current_full_verified", "historical_snapshot")
    body = {"status": status, "scope": ["full_body"] if full else [],
            "effective_date": "2026-09-14" if full else None,
            "sources": [source()], "retained_snapshot": None}
    if status == "fields_only":
        body["scope"] = ["keywords", "abilities"]
        body["sources"] = [source("b", "preview_image")]
    if status == "newer_full_unavailable":
        body["sources"] = [source("b", "preview_image")]
        body["retained_snapshot"] = {"effective_date": "2026-09-14", "scope": ["full_body"],
                                     "sources": [source()]}
    points = {"status": "historical", "effective_date": None,
              "sources": [source("a", "web", "2026-09-14")]}
    if status == "source_only_price":
        points = {"status": "current_published", "effective_date": None,
                  "sources": [source("c", "web", "2026-09-30")]}
        identity.update(unit_id=None, name_en="Marneus Calgar")
        body["sources"] = copy.deepcopy(points["sources"])
    return {"identity": identity, "reviewed_on": "2026-10-01", "body": body, "points": points}


def manifest(*records):
    return {"schema_version": 1, "records": list(records)}


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "synthetic.sqlite"
    with closing(sqlite3.connect(path)) as conn, conn:
        conn.execute("CREATE TABLE factions(id TEXT PRIMARY KEY,name TEXT)")
        conn.executemany("INSERT INTO factions VALUES (?,?)", [("SM", "Space Marines"), ("AC", "Adeptus Custodes")])
        conn.execute("CREATE TABLE units(id TEXT PRIMARY KEY,name_en TEXT,faction_id TEXT,keywords_json TEXT,points_json TEXT)")
        conn.execute("INSERT INTO units VALUES (?,?,?,?,?)", (
            "armour", "Marneus Calgar in Armour of Antilochus", "SM",
            json.dumps({"keywords": ["CHARACTER"], "faction_keywords": ["ADEPTUS ASTARTES", "ULTRAMARINES"]}),
            json.dumps({"points": 155, "mfm": {"current": False}})))
        # Bodies/DSL/history are deliberate sentinels: coverage cannot change them.
        conn.execute("CREATE TABLE models(unit_id TEXT,w TEXT)")
        conn.execute("INSERT INTO models VALUES ('armour','6')")
        conn.execute("CREATE TABLE abilities(id TEXT,effect_dsl_json TEXT)")
        conn.execute("INSERT INTO abilities VALUES ('a1','{\"sentinel\":true}')")
        conn.execute("CREATE TABLE source_archived_units(name_en TEXT,historical_points INTEGER)")
        conn.execute("INSERT INTO source_archived_units VALUES ('Marneus Calgar',200)")
        from db_compile.mfm_source import write_ledger
        prices = source("c", "web", "2026-09-30")
        write_ledger(conn, {"fetched_at": prices["captured_at"], "pages": {
            "space-marines": {"url": prices["url"], "sha256": prices["sha256"], "rows": [
                {"kind": "unit", "section": "UNITS", "unit": "MARNEUS CALGAR",
                 "tier": "YOUR UNIT COSTS", "models": "1 model", "cost": 180},
                {"kind": "unit", "section": "UNITS", "unit": "MARNEUS CALGAR",
                 "tier": "YOUR UNIT COSTS", "models": "2 models", "cost": 300}]}}})
    return path


def preserved(conn):
    return {table: conn.execute("SELECT * FROM " + table).fetchall() for table in (
        "factions", "units", "models", "abilities", "source_archived_units", "official_mfm_points")}


@pytest.mark.parametrize("status", ["current_full_verified", "fields_only", "historical_snapshot",
                                   "newer_full_unavailable", "source_only_price"])
def test_supported_statuses_round_trip_without_certifying_prices_as_body(database, status):
    declaration = record(None if status == "source_only_price" else "armour", status)
    untouched = copy.deepcopy(declaration)
    with closing(sqlite3.connect(database)) as conn, conn:
        before = preserved(conn)
        conn.execute("BEGIN IMMEDIATE")
        assert api().apply_coverage(conn, manifest(declaration), expected_records=[None]) == {
            "schema_version": 1, "records": 1}
        if status == "source_only_price":
            resolved = api().resolve_coverage(conn, name_en="MARNEUS CALGAR", faction_slug="space-marines")
        else:
            resolved = api().resolve_coverage(conn, unit_id="armour")
        assert resolved == declaration
        assert preserved(conn) == before
        assert declaration == untouched
        assert conn.in_transaction  # The inner operation must not commit the caller.
        assert conn.execute("SELECT count(*) FROM source_coverage_history").fetchone()[0] == 1


def test_absent_registry_and_missing_identity_are_read_only_unknowns(database):
    before = database.read_bytes()
    with closing(sqlite3.connect(database)) as conn:
        assert api().resolve_coverage(conn, unit_id="armour") is None
        assert api().resolve_coverage(conn, unit_id="missing") is None
        assert api().resolve_coverage(conn, name_en="Marneus Calgar", faction_slug="space-marines") is None
        assert not conn.in_transaction
    assert database.read_bytes() == before


@pytest.mark.parametrize("change,match", [
    (lambda r: r.update(coverage="certified"), "record fields"),
    (lambda r: r["body"].update(status="current"), "Unknown body"),
    (lambda r: r["body"].update(status=[]), "Unknown body"),
    (lambda r: r["body"].update(scope=["full_body", "weapons"]), "body scope"),
    (lambda r: r["body"].update(effective_date="2026-02-30"), "effective date"),
    (lambda r: r["body"].update(effective_date=None), "effective date"),
    (lambda r: r["body"].update(effective_date="2026-10-03"), "after review"),
    (lambda r: r["body"].update(sources=[]), "explicit source"),
    (lambda r: r["body"]["sources"][0].update(sha256="unknown"), "SHA-256"),
    (lambda r: r["body"]["sources"][0].update(page=True), "one-based"),
    (lambda r: r["body"]["sources"][0].update(url="https://name:secret@example.invalid/a.pdf"), "HTTPS"),
    (lambda r: r["body"]["sources"][0].update(captured_at="2026-09-14"), "timestamp"),
    (lambda r: r["body"]["sources"][0].update(captured_at="2026-10-02T00:00:00Z"), "after review"),
    (lambda r: r["body"]["sources"][0].update(kind="preview_image"), "cannot certify"),
    (lambda r: r["points"].update(status="current_full_verified"), "points status"),
    (lambda r: r["points"].update(status="unavailable"), "price provenance"),
    (lambda r: r["identity"].update(unit_id=None), "canonical body ID"),
    (lambda r: r["identity"].update(faction_keywords=["ULTRAMARINES", "ULTRAMARINES"]), "Duplicate faction"),
])
def test_malformed_declarations_reject_before_writes(database, change, match):
    declaration = record()
    change(declaration)
    before = database.read_bytes()
    with closing(sqlite3.connect(database)) as conn:
        conn.execute("BEGIN IMMEDIATE")
        with pytest.raises(ValueError, match=match):
            api().apply_coverage(conn, manifest(declaration), expected_records=[None])
        conn.rollback()
    assert database.read_bytes() == before


def test_strict_manifest_duplicate_and_document_conflict():
    module = api()
    with pytest.raises(ValueError, match="schema version"):
        module.validate_manifest({"schema_version": True, "records": [record()]})
    with pytest.raises(ValueError, match="Duplicate coverage"):
        module.validate_manifest(manifest(record(), record()))
    r = record()
    second = copy.deepcopy(r["body"]["sources"][0])
    second.update(page=8, sha256="b" * 64)
    r["body"]["sources"].append(second)
    with pytest.raises(ValueError, match="Conflicting source document"):
        module.validate_manifest(manifest(r))


@pytest.mark.parametrize("change,match", [
    (lambda r: r["identity"].update(name_en="Marneus Calgar"), "canonical coverage identity"),
    (lambda r: r["identity"].update(unit_id="missing"), "canonical coverage identity"),
    (lambda r: r["identity"].update(faction_id="AC"), "canonical coverage identity"),
    (lambda r: r["identity"].update(faction_keywords=["ADEPTUS ASTARTES"]), "faction keywords"),
    (lambda r: r["identity"].update(faction_slug="adeptus-custodes"), "source faction"),
    (lambda r: r["identity"].update(faction_slug="blood-angels"), "source chapter"),
])
def test_canonical_identity_faction_and_chapter_cannot_drift(database, change, match):
    r = record()
    change(r)
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        with pytest.raises(ValueError, match=match):
            api().apply_coverage(conn, manifest(r), expected_records=[None])
        assert preserved(conn)["units"][0][0] == "armour"
        assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='source_coverage_registry'").fetchone()


@pytest.mark.parametrize("change", [
    lambda r: r["identity"].update(name_en="Marneus Calgar in Armour of Antilochus"),
    lambda r: r["identity"].update(name_en="Marneus Calgar Jr"),
    lambda r: r["identity"].update(faction_slug="blood-angels"),
    lambda r: [s.update(sha256="d" * 64) for s in r["points"]["sources"] + r["body"]["sources"]],
])
def test_source_only_identity_requires_exact_ledger_and_no_sibling_body(database, change):
    r = record(None, "source_only_price")
    change(r)
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        with pytest.raises(ValueError):
            api().apply_coverage(conn, manifest(r), expected_records=[None])
        assert conn.execute("SELECT count(*) FROM units").fetchone()[0] == 1


def test_exact_price_identity_requires_qualification_and_never_loads_armour_body(database):
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        api().apply_coverage(conn, manifest(record(None, "source_only_price")), expected_records=[None])
        with pytest.raises(ValueError, match="exact source faction"):
            api().resolve_coverage(conn, name_en="Marneus Calgar")
        assert api().resolve_coverage(conn, unit_id="armour") is None
        assert api().resolve_coverage(conn, name_en="Marneus Calgar", faction_slug="blood-angels") is None
        assert api().resolve_coverage(conn, name_en="Marneus Calgar Jr", faction_slug="space-marines") is None


@pytest.mark.parametrize("chapter", ["BLACK TEMPLARS", "BLOOD ANGELS", "DARK ANGELS", "DEATHWATCH",
                                     "SPACE WOLVES", "ULTRAMARINES", "SALAMANDERS", "IMPERIAL FISTS",
                                     "IRON HANDS", "RAVEN GUARD", "WHITE SCARS"])
def test_generic_sm_price_source_preserves_each_exact_chapter_identity(database, chapter):
    r = record()
    r["identity"]["faction_keywords"] = ["ADEPTUS ASTARTES", chapter]
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("UPDATE units SET keywords_json=? WHERE id='armour'", (
            json.dumps({"faction_keywords": ["ADEPTUS ASTARTES", chapter]}),))
        api().apply_coverage(conn, manifest(r), expected_records=[None])
        assert api().resolve_coverage(conn, unit_id="armour")["identity"]["faction_keywords"] == ["ADEPTUS ASTARTES", chapter]


@pytest.mark.parametrize("status", ["current_full_verified", "historical_snapshot", "newer_full_unavailable"])
def test_price_or_unit_membership_cannot_certify_a_missing_body(database, status):
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("DELETE FROM models")
        with pytest.raises(ValueError, match="stored model"):
            api().apply_coverage(conn, manifest(record(status=status)), expected_records=[None])
        # A limited fields declaration remains available without claiming a body.
        api().apply_coverage(conn, manifest(record(status="fields_only")), expected_records=[None])
        assert api().resolve_coverage(conn, unit_id="armour")["body"]["scope"] == ["keywords", "abilities"]


def test_application_requires_transaction_and_exact_prior_state(database):
    with closing(sqlite3.connect(database)) as conn:
        with pytest.raises(ValueError, match="active transaction"):
            api().apply_coverage(conn, manifest(record()), expected_records=[None])
        conn.execute("BEGIN IMMEDIATE")
        api().apply_coverage(conn, manifest(record()), expected_records=[None])
        with pytest.raises(ValueError, match="prior coverage"):
            api().apply_coverage(conn, manifest(record(status="historical_snapshot")), expected_records=[None])
        assert api().resolve_coverage(conn, unit_id="armour")["body"]["status"] == "current_full_verified"
        conn.rollback()
        assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='source_coverage_registry'").fetchone()


def test_body_price_staging_rolls_back_together_when_outer_promotion_fails(database):
    with closing(sqlite3.connect(database)) as conn:
        before = preserved(conn)
        with pytest.raises(RuntimeError, match="promotion gate"):
            with conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute("UPDATE models SET w='7' WHERE unit_id='armour'")
                conn.execute("UPDATE official_mfm_points SET cost=190 WHERE cost=180")
                api().apply_coverage(conn, manifest(record(status="newer_full_unavailable")), expected_records=[None])
                raise RuntimeError("promotion gate failed")
        assert preserved(conn) == before
        assert not conn.execute("SELECT 1 FROM sqlite_master WHERE name='source_coverage_registry'").fetchone()


def test_caught_write_failure_undoes_registry_delta_but_preserves_outer_transaction(database):
    old = record(status="historical_snapshot")
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        api().apply_coverage(conn, manifest(old), expected_records=[None])
        conn.execute("CREATE TRIGGER fail_coverage BEFORE INSERT ON source_coverage_registry "
                     "WHEN NEW.record_json LIKE '%fields_only%' BEGIN SELECT RAISE(ABORT,'fixture abort'); END")
        price = record(None, "source_only_price")
        with pytest.raises(sqlite3.IntegrityError, match="fixture abort"):
            api().apply_coverage(conn, manifest(price, record(status="fields_only")), expected_records=[None, old])
        assert api().resolve_coverage(conn, unit_id="armour") == old
        assert api().resolve_coverage(conn, name_en="Marneus Calgar", faction_slug="space-marines") is None
        assert conn.execute("SELECT count(*) FROM source_coverage_history").fetchone()[0] == 1
        assert conn.in_transaction


def test_reviewed_updates_keep_history_and_cannot_recertify_retained_bytes(database):
    old = record(status="historical_snapshot")
    unavailable = record(status="newer_full_unavailable")
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        api().apply_coverage(conn, manifest(old), expected_records=[None])
        api().apply_coverage(conn, manifest(unavailable), expected_records=[old])
        with pytest.raises(ValueError, match="cannot recertify"):
            api().apply_coverage(conn, manifest(record()), expected_records=[unavailable])
        reviewed = record()
        reviewed["body"].update(effective_date="2026-09-30", sources=[source("d", "pdf", "2026-09-30")])
        api().apply_coverage(conn, manifest(reviewed), expected_records=[unavailable])
        api().apply_coverage(conn, manifest(reviewed), expected_records=[reviewed])
        assert conn.execute("SELECT count(*) FROM source_coverage_history").fetchone()[0] == 3
        assert api().resolve_coverage(conn, unit_id="armour") == reviewed
        downgrade = copy.deepcopy(reviewed)
        downgrade["body"]["effective_date"] = "2026-09-14"
        with pytest.raises(ValueError, match="date would downgrade"):
            api().apply_coverage(conn, manifest(downgrade), expected_records=[reviewed])


def test_stored_tampering_and_canonical_drift_fail_closed(database):
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        api().apply_coverage(conn, manifest(record()), expected_records=[None])
        conn.execute("UPDATE units SET name_en='different variant' WHERE id='armour'")
        with pytest.raises(ValueError, match="canonical coverage identity"):
            api().resolve_coverage(conn, unit_id="armour")
        conn.execute("UPDATE source_coverage_registry SET record_json='{}'")
        with pytest.raises(ValueError, match="record fields"):
            api().resolve_coverage(conn, unit_id="armour")


def test_current_body_and_current_prices_are_independent_verified_declarations(database):
    old = record()
    current = record(status="newer_full_unavailable")
    current["points"] = {"status": "current_published", "effective_date": None,
                         "sources": [source("c", "web", "2026-09-30")]}
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        api().apply_coverage(conn, manifest(old), expected_records=[None])
        with pytest.raises(ValueError, match="explicit current projection"):
            api().apply_coverage(conn, manifest(current), expected_records=[old])
        # The staged exact current canonical identity is distinct from ordinary.
        conn.execute("INSERT INTO official_mfm_points SELECT faction_slug,2,kind,section,?,tier,models,155,"
                     "source_url,source_sha256,fetched_at FROM official_mfm_points WHERE ordinal=0",
                     (current["identity"]["name_en"],))
        conn.execute("UPDATE units SET points_json=? WHERE id='armour'",
                     (json.dumps({"mfm": {"current": True}, "points": 155}),))
        api().apply_coverage(conn, manifest(current), expected_records=[old])
        resolved = api().resolve_coverage(conn, unit_id="armour")
        assert resolved["points"]["status"] == "current_published"
        assert resolved["points"]["effective_date"] is None  # Capture is not legality.
        assert resolved["body"]["status"] == "newer_full_unavailable"
        assert resolved["body"]["scope"] == []
        assert resolved["body"]["retained_snapshot"]["effective_date"] == "2026-09-14"
        conn.execute("UPDATE official_mfm_points SET source_sha256=? WHERE ordinal=2", ("d" * 64,))
        with pytest.raises(ValueError, match="price provenance"):
            api().resolve_coverage(conn, unit_id="armour")


def test_coverage_stays_out_of_patch_restoration_contract(tmp_path):
    from db_compile.source_reconcile import apply_patches
    path = tmp_path / "not-created.sqlite"
    with pytest.raises(ValueError, match="Coverage metadata is not supported"):
        apply_patches(path, {"patches": [], "source_coverage": manifest(record())})
    assert not path.exists()
