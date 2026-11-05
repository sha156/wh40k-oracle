"""Actual SQLite same-date footprint and known-full recertification controls."""
import copy
import hashlib
import json
import sqlite3
from contextlib import closing

import pytest

from tests.test_source_coverage import api, database, manifest, preserved, record, source
from tests.test_source_coverage_transitions import coverage_rows, publish


def full(digests, status="current_full_verified", day="2026-09-30"):
    declaration = record(status=status)
    declaration["body"].update(
        effective_date=day, sources=[source(digest, day=day) for digest in digests])
    return declaration


def unavailable(snapshot):
    declaration = record(status="newer_full_unavailable")
    declaration["body"]["retained_snapshot"] = {
        key: copy.deepcopy(snapshot["body"][key])
        for key in ("effective_date", "scope", "sources")}
    return declaration


def start(conn, detour):
    conn.execute("CREATE TABLE caller_work(value TEXT)")
    conn.commit()
    conn.execute("BEGIN IMMEDIATE")
    conn.execute("INSERT INTO caller_work VALUES ('preserve caller')")
    old = publish(conn, full("a", "historical_snapshot"), None)
    latest = publish(conn, full("ad"), old)
    previous = latest
    if detour == "fields":
        previous = publish(conn, record(status="fields_only"), previous)
    elif detour == "historical-fields":
        previous = publish(conn, full("ad", "historical_snapshot"), previous)
        previous = publish(conn, record(status="fields_only"), previous)
    return old, latest, previous


def require_rejection(conn, declaration, previous):
    before, sentinels = coverage_rows(conn), preserved(conn)
    caller = conn.execute("SELECT * FROM caller_work").fetchall()
    with pytest.raises(ValueError):
        api().apply_coverage(conn, manifest(declaration), expected_records=[previous])
    assert coverage_rows(conn) == before
    assert preserved(conn) == sentinels
    assert conn.execute("SELECT * FROM caller_work").fetchall() == caller
    assert api().resolve_coverage(conn, unit_id="armour") == previous
    assert conn.in_transaction


@pytest.mark.parametrize("detour", ["direct", "fields", "historical-fields"])
@pytest.mark.parametrize("destination", ["newer_full_unavailable", "historical_snapshot",
                                         "current_full_verified"])
def test_known_same_date_superset_cannot_lose_full_source(database, detour, destination):
    with closing(sqlite3.connect(database)) as conn:
        old, latest, previous = start(conn, detour)
        proposed = unavailable(old) if destination == "newer_full_unavailable" else full("a", destination)
        require_rejection(conn, proposed, previous)
        conn.commit()


@pytest.mark.parametrize("detour", ["direct", "fields", "historical-fields"])
@pytest.mark.parametrize("retained", ["a", "ad"])
def test_multiple_equal_date_full_snapshots_cannot_forget_known_superset(database, detour, retained):
    with closing(sqlite3.connect(database)) as conn:
        old, latest, previous = start(conn, "direct")
        previous = publish(conn, full("ade"), previous)
        if detour != "direct":
            if detour == "historical-fields":
                previous = publish(conn, full("ade", "historical_snapshot"), previous)
            previous = publish(conn, record(status="fields_only"), previous)
        require_rejection(conn, unavailable(full(retained, "historical_snapshot")), previous)
        conn.commit()


@pytest.mark.parametrize("detour", ["direct", "fields"])
def test_existing_smaller_unavailable_history_cannot_recertify_exact_known_full(database, detour):
    with closing(sqlite3.connect(database)) as conn:
        old, latest, previous = start(conn, detour)
        # Seed the already reproduced, structurally valid old-base state. The
        # transition under test is always the actual public apply_coverage.
        prior = unavailable(old)
        payload = json.dumps(prior, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        key = json.dumps(["canonical", "armour"], separators=(",", ":"))
        conn.execute("INSERT INTO source_coverage_history VALUES (?,?,?)",
                     (key, hashlib.sha256(payload.encode()).hexdigest(), payload))
        conn.execute("UPDATE source_coverage_registry SET record_json=? WHERE identity_key=?",
                     (payload, key))
        require_rejection(conn, copy.deepcopy(latest), prior)
        conn.commit()


@pytest.mark.parametrize("day", ["2026-09-30", "2026-10-01"])
@pytest.mark.parametrize("digests", ["ade", "f"])
def test_distinct_new_source_still_advances_and_replays_without_history(database, day, digests):
    with closing(sqlite3.connect(database)) as conn:
        old, latest, previous = start(conn, "fields")
        previous = publish(conn, unavailable(latest), previous)
        sentinels = preserved(conn)
        proposed = full(digests, day=day)
        previous = publish(conn, proposed, previous)
        before, changes = coverage_rows(conn), conn.total_changes
        publish(conn, copy.deepcopy(proposed), previous)
        assert coverage_rows(conn) == before
        assert conn.total_changes == changes
        assert preserved(conn) == sentinels
        assert conn.in_transaction
        conn.commit()


@pytest.mark.parametrize("tamper", ["digest", "identity", "schema"])
def test_same_date_malformed_history_fails_closed(database, tamper):
    with closing(sqlite3.connect(database)) as conn:
        old, latest, previous = start(conn, "fields")
        payload = copy.deepcopy(latest)
        if tamper == "identity":
            payload["identity"]["name_en"] = "Another full variant"
        if tamper == "schema":
            payload["body"]["sources"] = []
        text = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        digest = "0" * 64 if tamper == "digest" else hashlib.sha256(text.encode()).hexdigest()
        conn.execute("UPDATE source_coverage_history SET record_json=?,record_sha256=? "
                     "WHERE record_json LIKE '%current_full_verified%'", (text, digest))
        require_rejection(conn, full("ade"), previous)
        conn.commit()


@pytest.mark.parametrize("digests", ["a", "d"])
def test_incomparable_equal_date_snapshots_do_not_restore_smaller_subset(database, digests):
    with closing(sqlite3.connect(database)) as conn:
        old, latest, previous = start(conn, "direct")
        # A genuinely distinct replacement is legal; content-addressed history
        # cannot establish that it supersedes the other same-date declaration.
        previous = publish(conn, full("f"), previous)
        previous = publish(conn, record(status="fields_only"), previous)
        require_rejection(conn, unavailable(full(digests, "historical_snapshot")), previous)
        previous = publish(conn, unavailable(full("f")), previous)
        assert api().resolve_coverage(conn, unit_id="armour") == previous
        conn.commit()


@pytest.mark.parametrize("digests", ["ad", "f"])
def test_incomparable_equal_date_full_replacements_can_be_retained_and_read(database, digests):
    with closing(sqlite3.connect(database)) as conn:
        old, latest, previous = start(conn, "direct")
        previous = publish(conn, full("f"), previous)
        previous = publish(conn, record(status="fields_only"), previous)
        historical = full(digests, "historical_snapshot")
        previous = publish(conn, historical, previous)
        assert api().resolve_coverage(conn, unit_id="armour") == historical
        previous = publish(conn, unavailable(historical), previous)
        require_rejection(conn, full("ad"), previous)
        require_rejection(conn, full("f"), previous)
        previous = publish(conn, full("e"), previous)
        before, changes = coverage_rows(conn), conn.total_changes
        publish(conn, previous, previous)
        assert coverage_rows(conn) == before and conn.total_changes == changes
        conn.commit()


@pytest.mark.parametrize("day", ["2026-09-30", "2026-10-01"])
def test_known_full_relabelled_after_legacy_smaller_barrier_is_not_new_evidence(database, day):
    with closing(sqlite3.connect(database)) as conn:
        old, latest, previous = start(conn, "direct")
        prior = unavailable(old)
        payload = json.dumps(prior, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        key = json.dumps(["canonical", "armour"], separators=(",", ":"))
        conn.execute("INSERT INTO source_coverage_history VALUES (?,?,?)",
                     (key, hashlib.sha256(payload.encode()).hexdigest(), payload))
        conn.execute("UPDATE source_coverage_registry SET record_json=? WHERE identity_key=?",
                     (payload, key))
        previous = publish(conn, record(status="fields_only"), prior)
        proposed = full("ad", day=day)
        proposed["body"]["sources"][1].update(url="https://example.invalid/relabel.pdf", page=99)
        require_rejection(conn, proposed, previous)
        # Historical reads/statuses retain the complete footprint honestly.
        previous = publish(conn, full("ad", "historical_snapshot"), previous)
        assert api().resolve_coverage(conn, unit_id="armour") == previous
        assert previous["body"]["status"] == "historical_snapshot"
        conn.commit()


def stage_price(conn, evidence, price):
    from db_compile.mfm_source import write_ledger

    write_ledger(conn, {"fetched_at": evidence["captured_at"], "pages": {
        "space-marines": {"url": evidence["url"], "sha256": evidence["sha256"], "rows": [
            {"kind": "unit", "section": "UNITS", "unit": "MARNEUS CALGAR IN ARMOUR OF ANTILOCHUS",
             "tier": "YOUR UNIT COSTS", "models": "1 model", "cost": price}]}}})
    conn.execute("UPDATE units SET points_json=? WHERE id='armour'",
                 (json.dumps({"points": price, "mfm": {"current": True}}),))


def metadata_start(conn, current_price=False):
    conn.execute("CREATE TABLE caller_work(value TEXT)")
    initial = record(status="newer_full_unavailable")
    if current_price:
        evidence = source("c", "web", "2026-09-30")
        stage_price(conn, evidence, 155)
        initial["points"] = {"status": "current_published", "effective_date": "2026-09-30",
                             "sources": [evidence]}
    conn.commit()
    conn.execute("BEGIN IMMEDIATE")
    conn.execute("INSERT INTO caller_work VALUES ('preserve caller')")
    previous = publish(conn, initial, None)
    current = full("de")
    current["points"] = copy.deepcopy(initial["points"])
    return publish(conn, current, previous)


@pytest.mark.parametrize("change", ["review", "historical-price", "current-price"])
def test_unchanged_body_metadata_and_independent_prices_are_not_recertification(database, change):
    with closing(sqlite3.connect(database)) as conn:
        current = metadata_start(conn, current_price=change == "current-price")
        proposed = copy.deepcopy(current)
        if change == "review":
            proposed["reviewed_on"] = "2026-10-02"
        elif change == "historical-price":
            proposed["points"].update(effective_date="2026-09-30",
                                      sources=[source("f", "web", "2026-09-30")])
        else:
            evidence = source("f", "web", "2026-10-01")
            stage_price(conn, evidence, 160)  # Synthetic caller-owned price update.
            proposed["points"] = {"status": "current_published", "effective_date": "2026-10-01",
                                  "sources": [evidence]}
        assert proposed["body"] == current["body"]
        api().validate_manifest(manifest(proposed))
        api()._check_identity(conn, proposed)
        before, sentinels, changes = coverage_rows(conn), preserved(conn), conn.total_changes
        conn.execute("SAVEPOINT source_coverage_apply")  # Earlier caller-owned same name.
        publish(conn, proposed, current)
        conn.execute("RELEASE SAVEPOINT source_coverage_apply")
        assert conn.in_transaction and preserved(conn) == sentinels
        assert conn.execute("SELECT * FROM caller_work").fetchall() == [("preserve caller",)]
        after = coverage_rows(conn)
        payload = json.dumps(proposed, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        key = json.dumps(["canonical", "armour"], separators=(",", ":"))
        assert after["source_coverage_registry"] == [(key, payload)]
        assert set(after["source_coverage_history"]) == set(before["source_coverage_history"]) | {
            (key, hashlib.sha256(payload.encode()).hexdigest(), payload)}
        assert conn.total_changes == changes + 2  # One declaration and one registry replacement.
        assert any(json.loads(row[2])["body"]["status"] == "newer_full_unavailable"
                   for row in after["source_coverage_history"])
        if change == "current-price":
            assert conn.execute("SELECT DISTINCT cost FROM official_mfm_points").fetchall() == [(160,)]
            assert json.loads(conn.execute("SELECT points_json FROM units").fetchone()[0])["points"] == 160
        changes = conn.total_changes
        publish(conn, copy.deepcopy(proposed), proposed)
        assert coverage_rows(conn) == after and conn.total_changes == changes
        conn.commit()
    committed_bytes = database.read_bytes()
    with closing(sqlite3.connect(database)) as conn:
        assert api().resolve_coverage(conn, unit_id="armour") == proposed
        assert coverage_rows(conn) == after and preserved(conn) == sentinels
        conn.execute("BEGIN IMMEDIATE")
        publish(conn, copy.deepcopy(proposed), proposed)
        assert conn.total_changes == 0
        conn.commit()
    assert database.read_bytes() == committed_bytes


@pytest.mark.parametrize("tamper", ["digest", "identity", "schema"])
@pytest.mark.parametrize("change", ["review", "price"])
def test_unchanged_body_updates_still_validate_entire_history(database, tamper, change):
    with closing(sqlite3.connect(database)) as conn:
        current = metadata_start(conn)
        proposed = copy.deepcopy(current)
        if change == "review":
            proposed["reviewed_on"] = "2026-10-02"
        else:
            proposed["points"]["sources"] = [source("f", "web", "2026-09-30")]
        old = record(status="newer_full_unavailable")
        if tamper == "identity":
            old["identity"]["name_en"] = "Another full variant"
        if tamper == "schema":
            old["body"]["sources"] = []
        payload = json.dumps(old, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        digest = "0" * 64 if tamper == "digest" else hashlib.sha256(payload.encode()).hexdigest()
        conn.execute("UPDATE source_coverage_history SET record_json=?,record_sha256=? "
                     "WHERE record_json LIKE '%newer_full_unavailable%'", (payload, digest))
        require_rejection(conn, proposed, current)


@pytest.mark.parametrize("field,value", [
    ("url", "https://example.invalid/relabel.pdf"), ("page", 99), ("kind", "web"),
    ("source_date", "2026-10-01"), ("captured_at", "2026-10-01T01:00:00Z"),
    ("effective_date", "2026-10-01"), ("source_order", None), ("known_hash", None),
])
def test_body_field_or_provenance_changes_do_not_get_metadata_exemption(database, field, value):
    with closing(sqlite3.connect(database)) as conn:
        current = metadata_start(conn)
        proposed = copy.deepcopy(current)
        proposed["reviewed_on"] = "2026-10-02"
        if field == "effective_date":
            proposed["body"][field] = value
        elif field == "source_order":
            proposed["body"]["sources"].reverse()
        elif field == "known_hash":
            proposed["body"]["sources"][0] = source("a", day="2026-09-30")
        else:
            proposed["body"]["sources"][0][field] = value
            if field == "kind":
                proposed["body"]["sources"][0]["page"] = None
        assert proposed["body"] != current["body"]
        api().validate_manifest(manifest(proposed))
        require_rejection(conn, proposed, current)


@pytest.mark.parametrize("invalid", ["review-downgrade", "future-price", "price-schema",
                                      "ledger", "projection", "identity", "prior"])
def test_unchanged_body_does_not_bypass_metadata_price_identity_or_prior_guards(database, invalid):
    with closing(sqlite3.connect(database)) as conn:
        current = metadata_start(conn, current_price=True)
        proposed = copy.deepcopy(current)
        proposed["reviewed_on"] = "2026-10-02"
        expected = current
        if invalid == "review-downgrade":
            proposed["reviewed_on"] = "2026-09-30"
        elif invalid == "future-price":
            proposed["points"]["effective_date"] = "2026-10-03"
        elif invalid == "price-schema":
            proposed["points"]["extra"] = "invalid"
        elif invalid == "ledger":
            proposed["points"]["sources"] = [source("f", "web", "2026-10-01")]
        elif invalid == "projection":
            proposed["points"]["status"] = "historical"
        elif invalid == "identity":
            proposed["identity"]["faction_keywords"] = ["ADEPTUS ASTARTES"]
        else:
            expected = copy.deepcopy(current)
            expected["reviewed_on"] = "2026-09-30"
        before, sentinels = coverage_rows(conn), preserved(conn)
        with pytest.raises(ValueError):
            api().apply_coverage(conn, manifest(proposed), expected_records=[expected])
        assert coverage_rows(conn) == before and preserved(conn) == sentinels
        assert api().resolve_coverage(conn, unit_id="armour") == current
        assert conn.in_transaction
        assert conn.execute("SELECT * FROM caller_work").fetchall() == [("preserve caller",)]
