"""Actual SQLite history and interruption controls; no production assets."""
import asyncio
import copy
import hashlib
import json
import sqlite3
from contextlib import closing

import pytest

from tests.test_source_coverage import api, database, manifest, preserved, record, source


def coverage_rows(conn):
    return {
        table: conn.execute("SELECT * FROM " + table + " ORDER BY 1,2").fetchall()
        if conn.execute("SELECT 1 FROM sqlite_master WHERE name=?", (table,)).fetchone() else None
        for table in ("source_coverage_registry", "source_coverage_history")
    }


def publish(conn, declaration, previous):
    api().apply_coverage(conn, manifest(declaration), expected_records=[previous])
    assert api().resolve_coverage(conn, unit_id="armour") == declaration
    return declaration


def full(status="current_full_verified", digest="d", day="2026-09-30"):
    declaration = record(status=status)
    declaration["body"].update(effective_date=day, sources=[source(digest, "pdf", day)])
    return declaration


DETOURS = [(), ("historical_snapshot",), ("fields_only",),
           ("historical_snapshot", "fields_only", "historical_snapshot"),
           ("fields_only", "newer_full_unavailable", "fields_only", "historical_snapshot")]


@pytest.mark.parametrize("detours", DETOURS)
@pytest.mark.parametrize("relabel", [False, True], ids=["same-provenance", "changed-labels"])
def test_unavailable_barrier_survives_all_status_detours(database, detours, relabel):
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        bodies_prices = preserved(conn)
        previous = publish(conn, record(status="newer_full_unavailable"), None)
        for status in detours:
            previous = publish(conn, record(status=status), previous)
        proposed = record()
        if relabel:
            # New URL/page/capture/review labels and an advanced legal date do
            # not acquire new bytes from the unavailable full book.
            proposed["body"]["effective_date"] = "2026-09-30"
            proposed["body"]["sources"][0].update(
                url="https://example.invalid/relabel.pdf", page=99,
                source_date="2026-09-30", captured_at="2026-10-01T01:00:00Z")
        before = coverage_rows(conn)
        with pytest.raises(ValueError, match="cannot recertify"):
            api().apply_coverage(conn, manifest(proposed), expected_records=[previous])
        assert coverage_rows(conn) == before
        assert api().resolve_coverage(conn, unit_id="armour") == previous
        assert preserved(conn) == bodies_prices
        assert conn.in_transaction


@pytest.mark.parametrize("origin", ["current_full_verified", "historical_snapshot", "newer_full_unavailable"])
@pytest.mark.parametrize("detour", [False, True], ids=["direct", "via-fields"])
@pytest.mark.parametrize("destination", ["current_full_verified", "historical_snapshot", "newer_full_unavailable"])
def test_latest_full_or_retained_date_cannot_downgrade(database, origin, detour, destination):
    latest = full("historical_snapshot" if origin == "newer_full_unavailable" else origin)
    if origin == "newer_full_unavailable":
        unavailable = record(status=origin)
        unavailable["body"]["retained_snapshot"] = {
            k: copy.deepcopy(latest["body"][k]) for k in ("effective_date", "scope", "sources")}
        latest = unavailable
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        bodies_prices = preserved(conn)
        previous = publish(conn, latest, None)
        if detour:
            previous = publish(conn, record(status="fields_only"), previous)
        before = coverage_rows(conn)
        with pytest.raises(ValueError, match="date would downgrade"):
            api().apply_coverage(conn, manifest(record(status=destination)), expected_records=[previous])
        assert coverage_rows(conn) == before
        assert api().resolve_coverage(conn, unit_id="armour") == previous
        assert preserved(conn) == bodies_prices


@pytest.mark.parametrize("destination", ["current_full_verified", "historical_snapshot", "newer_full_unavailable"])
def test_relabelling_known_older_bytes_cannot_replace_latest_snapshot(database, destination):
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        old = publish(conn, record(status="historical_snapshot"), None)
        latest = publish(conn, full(), old)
        previous = publish(conn, record(status="fields_only"), latest)
        proposed = record(status=destination)
        snapshot = proposed["body"]["retained_snapshot"] or proposed["body"]
        snapshot["effective_date"] = "2026-09-30"
        snapshot["sources"][0].update(source_date="2026-09-30", captured_at="2026-09-30T12:00:00Z")
        before = coverage_rows(conn)
        with pytest.raises(ValueError, match="sources would downgrade"):
            api().apply_coverage(conn, manifest(proposed), expected_records=[previous])
        assert coverage_rows(conn) == before


def test_unavailable_cannot_drop_a_known_full_snapshot(database):
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        latest = publish(conn, full(), None)
        previous = publish(conn, record(status="fields_only"), latest)
        proposed = record(status="newer_full_unavailable")
        proposed["body"]["retained_snapshot"] = None
        before = coverage_rows(conn)
        with pytest.raises(ValueError, match="retain the latest"):
            api().apply_coverage(conn, manifest(proposed), expected_records=[previous])
        assert coverage_rows(conn) == before


@pytest.mark.parametrize("digests", [("b",), ("a", "b")])
def test_unchanged_unavailable_provenance_is_not_new_full_body_evidence(database, digests):
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        old = publish(conn, record(status="newer_full_unavailable"), None)
        previous = publish(conn, record(status="historical_snapshot"), old)
        proposed = record()
        proposed["body"]["sources"] = [source(digest) for digest in digests]
        before = coverage_rows(conn)
        with pytest.raises(ValueError, match="cannot recertify"):
            publish(conn, proposed, previous)
        assert coverage_rows(conn) == before


def test_genuinely_new_reviewed_sources_advance_after_detours_and_replay_exactly(database):
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        bodies_prices = preserved(conn)
        previous = publish(conn, record(status="newer_full_unavailable"), None)
        for status in ("historical_snapshot", "fields_only", "historical_snapshot"):
            previous = publish(conn, record(status=status), previous)
        latest = publish(conn, full(), previous)
        before = coverage_rows(conn)
        publish(conn, latest, latest)
        assert coverage_rows(conn) == before  # Exact replay adds no history.
        historical = copy.deepcopy(latest)
        historical["body"]["status"] = "historical_snapshot"
        previous = publish(conn, historical, latest)
        unavailable = record(status="newer_full_unavailable")
        unavailable["body"]["retained_snapshot"] = {
            k: copy.deepcopy(latest["body"][k]) for k in ("effective_date", "scope", "sources")}
        previous = publish(conn, unavailable, previous)
        with pytest.raises(ValueError, match="cannot recertify"):
            publish(conn, latest, previous)
        final = publish(conn, full(digest="f", day="2026-10-01"), previous)
        before = coverage_rows(conn)
        publish(conn, final, final)
        assert coverage_rows(conn) == before
        assert preserved(conn) == bodies_prices


def test_new_reviewed_retained_source_can_advance_without_claiming_current_body(database):
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        previous = publish(conn, full(), None)
        proposed = record(status="newer_full_unavailable")
        new_body = full(digest="f", day="2026-10-01")["body"]
        proposed["body"]["retained_snapshot"] = {
            k: copy.deepcopy(new_body[k]) for k in ("effective_date", "scope", "sources")}
        publish(conn, proposed, previous)
        assert api().resolve_coverage(conn, unit_id="armour")["body"]["scope"] == []


def test_mixed_record_history_guard_failure_keeps_all_owned_rows_and_caller_work(database):
    with closing(sqlite3.connect(database)) as conn:
        conn.execute("CREATE TABLE caller_work(value TEXT)")
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("INSERT INTO caller_work VALUES ('keep me')")
        previous = publish(conn, record(status="newer_full_unavailable"), None)
        previous = publish(conn, record(status="historical_snapshot"), previous)
        before = coverage_rows(conn)
        with pytest.raises(ValueError, match="cannot recertify"):
            api().apply_coverage(conn, manifest(record(None, "source_only_price"), record()),
                                 expected_records=[None, previous])
        assert coverage_rows(conn) == before
        assert conn.in_transaction
        conn.commit()
    with closing(sqlite3.connect(database)) as conn:
        assert coverage_rows(conn) == before
        assert conn.execute("SELECT * FROM caller_work").fetchall() == [("keep me",)]


@pytest.mark.parametrize("tamper", ["digest", "identity", "json"])
def test_history_is_validated_before_it_can_authorize_a_transition(database, tamper):
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        old = publish(conn, record(status="newer_full_unavailable"), None)
        previous = publish(conn, record(status="fields_only"), old)
        broken = copy.deepcopy(old)
        if tamper == "identity":
            broken["identity"]["name_en"] = "Different full variant"
        payload = "{}" if tamper == "json" else json.dumps(
            broken, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        digest = "0" * 64 if tamper == "digest" else hashlib.sha256(payload.encode()).hexdigest()
        conn.execute("UPDATE source_coverage_history SET record_json=?,record_sha256=? WHERE record_json LIKE ?",
                     (payload, digest, '%newer_full_unavailable%'))
        before = coverage_rows(conn)
        with pytest.raises(ValueError):
            publish(conn, full(), previous)
        assert coverage_rows(conn) == before


def test_date_semantics_do_not_invent_publication_from_document_or_capture_date(database):
    proposed = full()
    proposed["body"]["sources"][0].update(
        source_date="2026-10-03", captured_at="2026-09-14T12:00:00Z")
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        publish(conn, proposed, None)


def test_registry_only_legacy_state_still_supplies_latest_snapshot_boundary(database):
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        latest = publish(conn, full(), None)
        conn.execute("DROP TABLE source_coverage_history")
        before = coverage_rows(conn)
        with pytest.raises(ValueError, match="date would downgrade"):
            publish(conn, record(status="newer_full_unavailable"), latest)
        assert coverage_rows(conn) == before


def test_exact_prior_identity_and_review_date_guards_survive_history_checks(database):
    with closing(sqlite3.connect(database)) as conn, conn:
        conn.execute("BEGIN IMMEDIATE")
        previous = publish(conn, record(status="newer_full_unavailable"), None)
        proposed = full()
        with pytest.raises(ValueError, match="prior coverage"):
            publish(conn, proposed, record(status="historical_snapshot"))
        proposed["reviewed_on"] = "2026-09-30"
        with pytest.raises(ValueError, match="review date would downgrade"):
            publish(conn, proposed, previous)
        proposed["reviewed_on"] = "2026-10-01"
        proposed["identity"]["faction_slug"] = "ultramarines"
        with pytest.raises(ValueError, match="source faction"):
            publish(conn, proposed, previous)
        assert api().resolve_coverage(conn, unit_id="armour") == previous


class OwnedInterrupt(BaseException):
    pass


@pytest.mark.parametrize("interrupt_type", [KeyboardInterrupt, SystemExit, asyncio.CancelledError, OwnedInterrupt])
@pytest.mark.parametrize("existing", [False, True], ids=["new-tables", "existing-tables"])
@pytest.mark.parametrize("after_write", [False, True], ids=["before-second-insert", "after-second-insert"])
def test_caught_baseexception_undoes_only_owned_savepoint_and_keeps_original(
        database, interrupt_type, existing, after_write):
    original = interrupt_type("synthetic registry interruption")

    class InterruptConnection(sqlite3.Connection):
        registry_writes = 0
        armed = False

        def execute(self, sql, *args, **kwargs):
            target = self.armed and sql.startswith("INSERT OR REPLACE INTO source_coverage_registry")
            if target:
                self.registry_writes += 1
            if target and self.registry_writes == 2 and not after_write:
                raise original
            result = super().execute(sql, *args, **kwargs)
            if target and self.registry_writes == 2:
                raise original
            return result

    old = record(status="historical_snapshot") if existing else None
    with closing(sqlite3.connect(database, factory=InterruptConnection)) as conn:
        conn.execute("CREATE TABLE caller_work(value TEXT)")
        if existing:
            conn.execute("BEGIN IMMEDIATE")
            publish(conn, old, None)
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("INSERT INTO caller_work VALUES ('prior caller row')")
        bodies_prices, before = preserved(conn), coverage_rows(conn)
        conn.armed = True
        with pytest.raises(interrupt_type) as caught:
            api().apply_coverage(conn, manifest(record(None, "source_only_price"), record(status="fields_only")),
                                 expected_records=[None, old])
        assert caught.value is original
        assert conn.registry_writes == 2  # A real first write occurred.
        assert conn.in_transaction
        assert coverage_rows(conn) == before
        assert preserved(conn) == bodies_prices
        assert conn.execute("SELECT * FROM caller_work").fetchall() == [("prior caller row",)]
        # Release is observable: this function's savepoint no longer exists.
        with pytest.raises(sqlite3.OperationalError, match="no such savepoint"):
            conn.execute("ROLLBACK TO SAVEPOINT source_coverage_apply")
        conn.commit()
    with closing(sqlite3.connect(database)) as conn:
        assert coverage_rows(conn) == before
        assert preserved(conn) == bodies_prices
        assert conn.execute("SELECT * FROM caller_work").fetchall() == [("prior caller row",)]


def test_interruption_preserves_an_earlier_caller_savepoint_with_the_same_name(database):
    original = KeyboardInterrupt("synthetic nested-savepoint interrupt")

    class InterruptConnection(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            if sql.startswith("INSERT OR REPLACE INTO source_coverage_registry"):
                raise original
            return super().execute(sql, *args, **kwargs)

    with closing(sqlite3.connect(database, factory=InterruptConnection)) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("SAVEPOINT source_coverage_apply")
        before = coverage_rows(conn)
        with pytest.raises(KeyboardInterrupt) as caught:
            publish(conn, record(), None)
        assert caught.value is original
        assert coverage_rows(conn) == before
        # The caller's earlier savepoint survives the failed nested application.
        conn.execute("ROLLBACK TO SAVEPOINT source_coverage_apply")
        conn.execute("RELEASE SAVEPOINT source_coverage_apply")
        assert conn.in_transaction
        conn.rollback()


def test_cleanup_error_cannot_replace_the_original_interrupt(database):
    original = KeyboardInterrupt("synthetic original interrupt")

    class CleanupFailureConnection(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            if sql.startswith("INSERT OR REPLACE INTO source_coverage_registry"):
                raise original
            if sql == "RELEASE SAVEPOINT source_coverage_apply":
                # Perform the real release, then expose a controlled cleanup
                # exception. The wrapper is not a mocked SQLite state result.
                super().execute(sql, *args, **kwargs)
                raise sqlite3.OperationalError("synthetic release wrapper failure")
            return super().execute(sql, *args, **kwargs)

    with closing(sqlite3.connect(database, factory=CleanupFailureConnection)) as conn:
        conn.execute("BEGIN IMMEDIATE")
        before = coverage_rows(conn)
        with pytest.raises(KeyboardInterrupt) as caught:
            publish(conn, record(), None)
        assert caught.value is original
        assert conn.in_transaction
        assert coverage_rows(conn) == before
        conn.commit()
