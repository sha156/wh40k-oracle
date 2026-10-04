"""Registry-only adoption and cancellation on private real SQLite fixtures."""
import copy
import hashlib
import json
import sqlite3
from contextlib import closing

import pytest

from tests.test_source_coverage import api, database, manifest, preserved, record
from tests.test_source_coverage_transitions import coverage_rows, full, publish


def seed_legacy(conn, declaration, history_mode):
    """Model the documented legacy schema directly, without clearing history."""
    api().validate_manifest(manifest(declaration))
    key = json.dumps(["canonical", "armour"], separators=(",", ":"))
    # Deliberately noncanonical JSON: adoption must retain exact original bytes,
    # not serialize the parsed declaration under a different content digest.
    payload = json.dumps(declaration, ensure_ascii=False, indent=2) + "\n"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    conn.execute("CREATE TABLE source_coverage_registry "
                 "(identity_key TEXT PRIMARY KEY,record_json TEXT NOT NULL)")
    conn.execute("INSERT INTO source_coverage_registry VALUES (?,?)", (key, payload))
    if history_mode != "missing":
        conn.execute("CREATE TABLE source_coverage_history "
                     "(identity_key TEXT NOT NULL,record_sha256 TEXT NOT NULL,record_json TEXT NOT NULL,"
                     "PRIMARY KEY(identity_key,record_sha256))")
        if history_mode == "populated":
            conn.execute("INSERT INTO source_coverage_history VALUES (?,?,?)", (key, digest, payload))
    conn.commit()
    assert api().resolve_coverage(conn, unit_id="armour") == declaration
    return key, digest, payload


@pytest.mark.parametrize("history_mode", ["missing", "empty", "populated"])
def test_exact_legacy_replay_is_read_write_noop_even_with_original_json_spacing(database, history_mode):
    initial = full()
    with closing(sqlite3.connect(database)) as conn:
        seed_legacy(conn, initial, history_mode)
        conn.execute("BEGIN IMMEDIATE")
        before, sentinels = coverage_rows(conn), preserved(conn)
        changes = conn.total_changes
        publish(conn, initial, initial)
        assert conn.total_changes == changes
        assert coverage_rows(conn) == before
        assert preserved(conn) == sentinels
        assert conn.in_transaction
        conn.rollback()


@pytest.mark.parametrize("history_mode", ["missing", "empty"])
@pytest.mark.parametrize("origin", ["latest-full", "unavailable-barrier"])
def test_legacy_fields_detours_cannot_forget_prior_boundary(database, history_mode, origin):
    initial = full() if origin == "latest-full" else record(status="newer_full_unavailable")
    with closing(sqlite3.connect(database)) as conn:
        original = seed_legacy(conn, initial, history_mode)
        conn.execute("BEGIN IMMEDIATE")
        sentinels = preserved(conn)
        previous = publish(conn, record(status="fields_only"), initial)
        before = coverage_rows(conn)
        match = "date would downgrade" if origin == "latest-full" else "cannot recertify"
        with pytest.raises(ValueError, match=match):
            publish(conn, record(), previous)
        assert coverage_rows(conn) == before
        assert original in before["source_coverage_history"]
        # Repeated honest detours cannot erase the adopted full/barrier record.
        historical = copy.deepcopy(initial)
        if origin == "unavailable-barrier":
            historical = record(status="historical_snapshot")
        else:
            historical["body"]["status"] = "historical_snapshot"
        for _ in range(3):
            previous = publish(conn, historical, previous)
            previous = publish(conn, record(status="fields_only"), previous)
        before = coverage_rows(conn)
        with pytest.raises(ValueError, match=match):
            publish(conn, record(), previous)
        assert coverage_rows(conn) == before
        assert preserved(conn) == sentinels
        assert conn.in_transaction
        conn.commit()
    with closing(sqlite3.connect(database)) as conn:
        assert coverage_rows(conn) == before
        assert preserved(conn) == sentinels


@pytest.mark.parametrize("history_mode", ["missing", "empty", "populated"])
@pytest.mark.parametrize("day", ["2026-09-30", "2026-10-01"])
def test_safe_legacy_adoption_preserves_exact_payload_and_allows_distinct_advancement(
        database, history_mode, day):
    initial = full()
    initial["body"]["sources"].append(copy.deepcopy(record()["body"]["sources"][0]))
    with closing(sqlite3.connect(database)) as conn:
        original = seed_legacy(conn, initial, history_mode)
        conn.execute("CREATE TABLE caller_work(value TEXT)")
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("INSERT INTO caller_work VALUES ('before caller savepoint')")
        conn.execute("SAVEPOINT source_coverage_apply")
        conn.execute("INSERT INTO caller_work VALUES ('inside caller savepoint')")
        sentinels = preserved(conn)
        previous = publish(conn, record(status="fields_only"), initial)
        rows = coverage_rows(conn)
        assert original in rows["source_coverage_history"]
        assert len(rows["source_coverage_history"]) == 2
        publish(conn, previous, previous)
        assert coverage_rows(conn) == rows  # Replay neither adds nor changes history.
        advanced = publish(conn, full(digest="f", day=day), previous)
        unavailable = record(status="newer_full_unavailable")
        unavailable["body"]["retained_snapshot"] = {
            k: copy.deepcopy(advanced["body"][k]) for k in ("effective_date", "scope", "sources")}
        previous = publish(conn, unavailable, advanced)
        previous = publish(conn, record(status="fields_only"), previous)
        with pytest.raises(ValueError, match="cannot recertify"):
            publish(conn, advanced, previous)
        assert preserved(conn) == sentinels
        assert conn.in_transaction
        # The caller's identically named savepoint is still the caller's own.
        conn.execute("ROLLBACK TO SAVEPOINT source_coverage_apply")
        conn.execute("RELEASE SAVEPOINT source_coverage_apply")
        assert conn.execute("SELECT * FROM caller_work").fetchall() == [("before caller savepoint",)]
        assert api().resolve_coverage(conn, unit_id="armour") == initial
        conn.commit()
    with closing(sqlite3.connect(database)) as conn:
        assert conn.execute("SELECT * FROM caller_work").fetchall() == [("before caller savepoint",)]
        assert preserved(conn) == sentinels


@pytest.mark.parametrize("history_mode", ["missing", "empty"])
@pytest.mark.parametrize("target", ["history-1", "history-2", "registry-1", "registry-2"])
@pytest.mark.parametrize("after_write", [False, True], ids=["before-write", "after-write"])
def test_interrupted_legacy_adoption_restores_exact_owned_state_and_caller_savepoint(
        database, history_mode, target, after_write):
    original_error = KeyboardInterrupt("synthetic adoption interruption")
    table_kind, write_number = target.split("-")

    class InterruptConnection(sqlite3.Connection):
        armed = False
        writes = 0

        def execute(self, sql, *args, **kwargs):
            prefix = ("INSERT OR IGNORE INTO source_coverage_history" if table_kind == "history"
                      else "INSERT OR REPLACE INTO source_coverage_registry")
            target_write = self.armed and sql.startswith(prefix)
            if target_write:
                self.writes += 1
                if self.writes == int(write_number) and not after_write:
                    raise original_error
            result = super().execute(sql, *args, **kwargs)
            if target_write and self.writes == int(write_number):
                raise original_error
            return result

    initial = full()
    with closing(sqlite3.connect(database, factory=InterruptConnection)) as conn:
        seed_legacy(conn, initial, history_mode)
        conn.execute("CREATE TABLE caller_work(value TEXT)")
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("INSERT INTO caller_work VALUES ('prior caller row')")
        conn.execute("SAVEPOINT source_coverage_apply")
        conn.execute("INSERT INTO caller_work VALUES ('caller savepoint row')")
        before, sentinels = coverage_rows(conn), preserved(conn)
        conn.armed = True
        with pytest.raises(KeyboardInterrupt) as caught:
            api().apply_coverage(conn, manifest(record(status="fields_only"),
                                               record(None, "source_only_price")),
                                 expected_records=[initial, None])
        assert caught.value is original_error
        assert conn.writes == int(write_number)
        assert coverage_rows(conn) == before
        assert preserved(conn) == sentinels
        assert conn.in_transaction
        assert conn.execute("SELECT * FROM caller_work").fetchall() == [
            ("prior caller row",), ("caller savepoint row",)]
        conn.execute("ROLLBACK TO SAVEPOINT source_coverage_apply")
        conn.execute("RELEASE SAVEPOINT source_coverage_apply")
        assert conn.execute("SELECT * FROM caller_work").fetchall() == [("prior caller row",)]
        conn.commit()
    with closing(sqlite3.connect(database)) as conn:
        assert coverage_rows(conn) == before
        assert preserved(conn) == sentinels
        assert conn.execute("SELECT * FROM caller_work").fetchall() == [("prior caller row",)]


@pytest.mark.parametrize("history_mode", ["missing", "empty"])
def test_rejected_mixed_adoption_does_not_write_previous_history(database, history_mode):
    initial = full()
    with closing(sqlite3.connect(database)) as conn:
        seed_legacy(conn, initial, history_mode)
        conn.execute("BEGIN IMMEDIATE")
        before, sentinels = coverage_rows(conn), preserved(conn)
        invalid = record(None, "source_only_price")
        invalid["identity"]["faction_id"] = "AC"
        with pytest.raises(ValueError, match="source faction"):
            api().apply_coverage(conn, manifest(record(status="fields_only"), invalid),
                                 expected_records=[initial, None])
        assert coverage_rows(conn) == before
        assert preserved(conn) == sentinels
        assert conn.in_transaction
        conn.rollback()


def test_adoption_cleanup_rejection_keeps_original_interrupt_and_requires_caller_rollback(database):
    original_error = KeyboardInterrupt("synthetic original adoption interruption")

    class CleanupFailureConnection(sqlite3.Connection):
        armed = False

        def execute(self, sql, *args, **kwargs):
            if self.armed and sql.startswith("INSERT OR REPLACE INTO source_coverage_registry"):
                raise original_error
            if self.armed and sql == "ROLLBACK TO SAVEPOINT source_coverage_apply":
                raise sqlite3.OperationalError("synthetic rollback rejection")
            return super().execute(sql, *args, **kwargs)

    initial = full()
    with closing(sqlite3.connect(database, factory=CleanupFailureConnection)) as conn:
        original = seed_legacy(conn, initial, "empty")
        conn.execute("BEGIN IMMEDIATE")
        before, sentinels = coverage_rows(conn), preserved(conn)
        conn.armed = True
        with pytest.raises(KeyboardInterrupt) as caught:
            publish(conn, record(status="fields_only"), initial)
        assert caught.value is original_error
        assert conn.in_transaction
        assert original in coverage_rows(conn)["source_coverage_history"]
        assert len(coverage_rows(conn)["source_coverage_history"]) == 2
        assert api().resolve_coverage(conn, unit_id="armour") == initial
        assert preserved(conn) == sentinels
        conn.rollback()  # Broken cleanup does not certify atomicity; caller recovers.
        assert coverage_rows(conn) == before
