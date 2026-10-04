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
