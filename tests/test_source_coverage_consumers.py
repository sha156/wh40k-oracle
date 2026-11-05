"""Actual central consumers with temporary strict declarations, no real assets."""
import copy
import json
import sqlite3
from contextlib import closing
from dataclasses import asdict
from pathlib import Path

import pytest

from db_compile.datasheet import find_datasheet, lookup_datasheet
from db_compile.source_coverage import apply_coverage
from tests.test_db_compile_datasheet import _make_db
from tests.test_source_coverage import source
from web_api.entity_card import build_entity_card
from web_api.formatter import _derive_entity_card, _evidence_digest
from web_api.trace import TraceRecorder


UID = "000000929"


def declaration(status="current_full_verified", retained=True):
    full = status in ("current_full_verified", "historical_snapshot")
    body = {
        "status": status, "scope": ["full_body"] if full else [],
        "effective_date": "2026-09-14" if full else None,
        "sources": [source()], "retained_snapshot": None,
    }
    if status == "fields_only":
        body.update(scope=["keywords", "abilities"], sources=[source("b", "preview_image")])
    if status == "newer_full_unavailable":
        body["sources"] = [source("b", "preview_image")]
        if retained:
            body["retained_snapshot"] = {
                "effective_date": "2026-09-14", "scope": ["full_body"], "sources": [source()],
            }
    points = {"status": "current_published", "effective_date": None,
              "sources": [source("c", "web", "2026-09-30")]}
    identity = {"unit_id": UID, "name_en": "Chaos Lord", "faction_id": "CSM",
                "faction_slug": "chaos-space-marines", "faction_keywords": ["Chaos"]}
    if status == "source_only_price":
        identity.update(unit_id=None, name_en="Source Hero")
        body["sources"] = copy.deepcopy(points["sources"])
    return {"identity": identity, "reviewed_on": "2026-10-01", "body": body, "points": points}


def install(db, record):
    from db_compile.mfm_source import write_ledger
    price = record["points"]["sources"][0]
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("BEGIN")
        conn.execute("UPDATE units SET points_json=? WHERE id=?", (json.dumps({
            "points": 85, "items": [{"desc": "1 model", "cost": 85}],
            "mfm": {"current": True}}), UID))
        write_ledger(conn, {"fetched_at": price["captured_at"], "pages": {
            "chaos-space-marines": {"url": price["url"], "sha256": price["sha256"], "rows": [
                {"kind": "unit", "section": "UNITS", "unit": record["identity"]["name_en"],
                 "tier": "YOUR UNIT COSTS", "models": "1 model", "cost": 85}]}}})
        apply_coverage(conn, {"schema_version": 1, "records": [record]}, expected_records=[None])


def assert_provenance(note, src):
    for value in (src["url"], src["sha256"], src["captured_at"], src["kind"]):
        assert value in note
    assert "source date " + src["source_date"] in note
    if src["page"] is not None:
        assert "page " + str(src["page"]) in note


@pytest.mark.parametrize("status,retained", [
    ("current_full_verified", True), ("fields_only", True),
    ("historical_snapshot", True), ("newer_full_unavailable", True),
    ("newer_full_unavailable", False),
])
def test_central_card_carries_whole_body_and_independent_price_note(tmp_path, status, retained):
    db = _make_db(tmp_path)
    record = declaration(status, retained)
    install(db, record)
    before = db.read_bytes()
    ds = lookup_datasheet(db, UID)
    note = ds.source_note
    assert note is not None
    for value in ("Chaos Lord", UID, "CSM", "chaos-space-marines", "Chaos", status,
                  "reviewed 2026-10-01", "Points: current_published",
                  "points effective date unverified", "does not certify body"):
        assert value in note
    for src in record["body"]["sources"] + record["points"]["sources"]:
        assert_provenance(note, src)
    if status == "fields_only":
        assert "verified scope: keywords, abilities" in note
        assert "full body unverified" in note
        assert "body effective date unverified" in note
    if status in ("current_full_verified", "historical_snapshot"):
        assert "body effective 2026-09-14" in note
        assert "verified scope: full_body" in note
    if status == "historical_snapshot":
        assert "not verified current rules" in note
    if status == "newer_full_unavailable":
        assert "newer full body unavailable" in note
        if retained:
            assert "retained full_body effective 2026-09-14" in note
            assert_provenance(note, record["body"]["retained_snapshot"]["sources"][0])
        else:
            assert "no verified retained body" in note
    assert ds.points_min == 85
    assert ds.models and ds.weapons
    card = build_entity_card({"found": True, "datasheet": asdict(ds)})
    assert card.src == note
    assert db.read_bytes() == before


def test_existing_preview_and_historical_price_notes_are_appended(tmp_path):
    db = _make_db(tmp_path)
    record = declaration("historical_snapshot")
    record["points"] = {"status": "historical", "effective_date": "2026-08-01",
                         "sources": [source("c", "web", "2026-09-30")]}
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("CREATE TABLE official_unit_sources(unit_id TEXT,sources_json TEXT)")
        conn.execute("INSERT INTO official_unit_sources VALUES (?,?)", (UID, json.dumps([
            {"kind": "official-preview-image", "published": "2026-09-20"}])))
        conn.execute("UPDATE units SET points_json=? WHERE id=?", (json.dumps({
            "items": [{"desc": "1 model", "cost": 85}],
            "mfm": {"current": False, "fetched_at": "2026-09-30T12:00:00Z"}}), UID))
        apply_coverage(conn, {"schema_version": 1, "records": [record]}, expected_records=[None])
    ds = lookup_datasheet(db, UID)
    assert "Historical price tiers (captured 2026-09-30T12:00:00Z): 1 model — 85 pts" in ds.source_note
    assert "Official preview 2026-09-20: released codex rules not verified." in ds.source_note
    assert "Points: historical; points effective 2026-08-01" in ds.source_note
    assert ds.points_min is None and ds.points_options == []
    assert build_entity_card({"found": True, "datasheet": asdict(ds)}).pts == "—"


def test_absent_registry_preserves_exact_legacy_payload(tmp_path):
    db = _make_db(tmp_path)
    before = asdict(lookup_datasheet(db, UID))
    before_card = build_entity_card({"found": True, "datasheet": before}).model_dump()
    assert lookup_datasheet(db, "") is None
    assert lookup_datasheet(db, "unknown-id") is None
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("CREATE TABLE source_coverage_registry(identity_key TEXT PRIMARY KEY,record_json TEXT NOT NULL)")
    assert asdict(lookup_datasheet(db, UID)) == before
    assert build_entity_card({"found": True, "datasheet": before}).model_dump() == before_card
    assert before["source_note"] is None


@pytest.mark.parametrize("legacy_note", [
    "Official preview 2026-09-20: released codex rules not verified.",
    "Historical price tiers (captured 2026-09-30T12:00:00Z): 1 model — 85 pts. Not current prices.",
])
def test_absent_registry_legacy_digest_remains_byte_equivalent(legacy_note):
    payload = {"found": True, "datasheet": {
        "name_en": "Legacy unit", "models": ["bulk " * 1000], "source_note": legacy_note}}
    recorder = TraceRecorder({})
    recorder.last_result["get_datasheet"] = payload
    expected = "[get_datasheet] " + json.dumps(payload, ensure_ascii=False, default=str)[:600]
    assert _evidence_digest(recorder) == expected[:2000]


def test_source_only_exact_note_never_invents_a_card(tmp_path):
    db = _make_db(tmp_path)
    record = declaration("source_only_price")
    install(db, record)
    from db_compile.coverage_notes import coverage_note
    with closing(sqlite3.connect(db)) as conn:
        note = coverage_note(conn, name_en="Source Hero", faction_slug="chaos-space-marines")
        assert "source_only_price" in note and "no canonical body" in note
        assert "Source Hero" in note and "chaos-space-marines" in note
        assert_provenance(note, record["points"]["sources"][0])
        assert coverage_note(conn, name_en="Source Hero", faction_slug="space-marines") is None
    assert find_datasheet(db, "Source Hero") is None
    assert lookup_datasheet(db, "Source Hero") is None
    assert build_entity_card({"found": True, "datasheet": None, "note": note}) is None


def redirect_canonical_reload(monkeypatch, db):
    from web_api import codex
    # Force the existing reload seam, but route every read to a temporary DB.
    monkeypatch.setattr(Path, "exists", lambda self: True)
    original = codex.unit_card
    monkeypatch.setattr(codex, "unit_card", lambda unused, uid, **kw: original(db, uid, **kw))


def test_formatter_canonical_reload_keeps_the_exact_central_note(tmp_path, monkeypatch):
    db = _make_db(tmp_path)
    install(db, declaration("newer_full_unavailable"))
    central = lookup_datasheet(db, UID).source_note
    recorder = TraceRecorder({})
    recorder.last_result["get_datasheet"] = {
        "found": True, "datasheet": {"unit_id": UID, "source_note": "stale tool note"}}
    redirect_canonical_reload(monkeypatch, db)
    assert _derive_entity_card(recorder, None).src == central


@pytest.mark.parametrize("mutation", ["identity", "json", "deleted", "preparse", "models"])
def test_invalid_stored_coverage_fails_closed_at_lookup_and_reload(tmp_path, monkeypatch, mutation):
    db = _make_db(tmp_path)
    install(db, declaration())
    with closing(sqlite3.connect(db)) as conn, conn:
        if mutation == "identity":
            conn.execute("UPDATE units SET name_en='Wrong sibling' WHERE id=?", (UID,))
        elif mutation == "deleted":
            conn.execute("DELETE FROM units WHERE id=?", (UID,))
        elif mutation == "models":
            conn.execute("DROP TABLE models")
        else:
            conn.execute("UPDATE source_coverage_registry SET record_json='broken'")
            if mutation == "preparse":
                conn.execute("UPDATE units SET points_json='[]' WHERE id=?", (UID,))
    with pytest.raises(ValueError, match="coverage|Coverage"):
        lookup_datasheet(db, UID)
    recorder = TraceRecorder({})
    recorder.last_result["get_datasheet"] = {
        "found": True, "datasheet": {"unit_id": UID, "name_en": "Stale but plausible"}}
    redirect_canonical_reload(monkeypatch, db)
    with pytest.raises(ValueError, match="coverage|Coverage"):
        _derive_entity_card(recorder, None)


def test_digest_preserves_all_whole_qualifiers_before_large_body_and_later_miss(tmp_path):
    db = _make_db(tmp_path)
    install(db, declaration("newer_full_unavailable"))
    note = lookup_datasheet(db, UID).source_note
    assert note
    notes = [note + " Subject " + str(n) for n in range(3)]
    def result(subject):
        if subject == 3:
            return {"found": False, "datasheet": None}
        return {"found": True, "datasheet": {
            "unit_id": str(subject), "name_en": "Subject " + str(subject),
            "weapons": ["large body" * 1000], "source_note": notes[subject]}}
    recorder = TraceRecorder({"get_datasheet": result})
    lookup = recorder.wrapped_tools()["get_datasheet"]
    for subject in range(4):
        lookup(subject)
    digest = _evidence_digest(recorder)
    for note in notes:
        assert note in digest
    assert "large body" not in digest  # complete qualifiers consume the soft bulk budget
    assert len(digest) > 2000
