"""Dated unit reversals on disposable SQLite, with explicit synthetic sources."""
import copy
import json
import sqlite3
from contextlib import closing

import pytest

from db_compile import source_reconcile as reconcile


def revisions():
    result = []
    for day, letter, old, new in [("2026-09-14", "a", "A", "B"),
                                  ("2026-09-30", "b", "B", "A")]:
        src = {"url": f"https://example.com/{letter}.pdf", "sha256": letter * 64,
               "page": 1, "title": "Synthetic unit source"}
        result.append({"source_date": day, "unit_sources": {"one": [src]},
                       "invalidate_translation_for": ["one"], "patches": [
                           {"table": "units", "key": {"id": "one"},
                            "from": {"keywords_json": old}, "to": {"keywords_json": new},
                            "source": src}]})
    # A later first-touch guard belongs to every state, including the earlier B.
    result[1]["patches"][0]["from"]["version"] = "guarded"
    result[1]["patches"][0]["to"]["version"] = "guarded"
    return result


def database(tmp_path, state="B", checkpoint=0):
    db = tmp_path / "reversal.sqlite"
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("CREATE TABLE units(id TEXT PRIMARY KEY,keywords_json TEXT,version TEXT)")
        conn.execute("INSERT INTO units VALUES ('one',?,'guarded')", (state,))
        conn.execute("CREATE TABLE official_unit_sources(unit_id TEXT PRIMARY KEY,sources_json TEXT)")
        conn.execute("CREATE TABLE official_unit_source_revisions(unit_id TEXT,source_date TEXT,sources_json TEXT)")
        if checkpoint is not None:
            revision = revisions()[checkpoint]
            raw = json.dumps(revision["unit_sources"]["one"])
            conn.execute("INSERT INTO official_unit_sources VALUES ('one',?)", (raw,))
            conn.execute("INSERT INTO official_unit_source_revisions VALUES ('one',?,?)",
                         (revision["source_date"], raw))
    return db


def test_dated_reversal_applies_exact_suffix_and_replays_byte_exact(tmp_path):
    db = database(tmp_path)
    declared = revisions()
    original = copy.deepcopy(declared)
    compiled, = reconcile.compile_revision_chain(declared)
    assert compiled.fields == ("keywords_json", "version")
    assert compiled.states[0] == compiled.states[2]
    assert reconcile.apply_patches(db, manifests=declared) == {
        "applied": 1, "already": 1, "inserted": 0, "total": 2}
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT keywords_json,version FROM units").fetchone() == ("A", "guarded")
        assert reconcile._read_source_history(conn, "one") == (
            declared[1]["unit_sources"]["one"],
            {item["source_date"]: item["unit_sources"]["one"] for item in declared})
    before = db.read_bytes()
    assert reconcile.apply_patches(db, {"revisions": declared}) == {
        "applied": 0, "already": 2, "inserted": 0, "total": 2}
    assert db.read_bytes() == before
    assert declared == original


@pytest.mark.parametrize("state,checkpoint", [("A", None), ("A", 0), ("B", 1), ("B", None)])
def test_absent_or_inconsistent_checkpoint_cannot_select_repeated_state(tmp_path, state, checkpoint):
    db = database(tmp_path, state, checkpoint)
    before = db.read_bytes()
    with pytest.raises(ValueError, match="history|checkpoint"):
        reconcile.apply_patches(db, manifests=revisions())
    assert db.read_bytes() == before


@pytest.mark.parametrize("damage", ["undated", "unknown", "drift", "bad_json", "bad_date",
                                  "duplicate", "same_date", "union_field"])
def test_bad_preexisting_history_or_union_guard_is_byte_exact_rejected(tmp_path, damage):
    db = database(tmp_path)
    with closing(sqlite3.connect(db)) as conn, conn:
        if damage == "undated":
            conn.execute("DELETE FROM official_unit_source_revisions")
        elif damage == "unknown":
            conn.execute("UPDATE official_unit_source_revisions SET source_date='2026-09-20'")
        elif damage == "drift":
            conn.execute("UPDATE official_unit_sources SET sources_json=?",
                         (json.dumps(revisions()[1]["unit_sources"]["one"]),))
        elif damage == "bad_json":
            conn.execute("UPDATE official_unit_source_revisions SET sources_json='broken'")
        elif damage == "bad_date":
            conn.execute("UPDATE official_unit_source_revisions SET source_date='2026-09-31'")
        elif damage == "duplicate":
            conn.execute("INSERT INTO official_unit_source_revisions SELECT * FROM official_unit_source_revisions")
        elif damage == "same_date":
            src = revisions()[0]["unit_sources"]["one"]
            src[0]["title"] = "Different declaration"
            raw = json.dumps(src)
            conn.execute("UPDATE official_unit_source_revisions SET sources_json=?", (raw,))
            conn.execute("UPDATE official_unit_sources SET sources_json=?", (raw,))
        else:
            conn.execute("UPDATE units SET version='drift'")
    before = db.read_bytes()
    with pytest.raises(ValueError):
        reconcile.apply_patches(db, manifests=revisions())
    assert db.read_bytes() == before


@pytest.mark.parametrize("damage", ["missing_anchor", "wrong_hash", "wrong_page", "same_revision",
                                  "undated", "adjacent_noop", "nonunit", "source_date"])
def test_unsupported_cycles_rejected_before_opening_sqlite(tmp_path, monkeypatch, damage):
    declared = revisions()
    if damage == "missing_anchor":
        del declared[1]["unit_sources"]
    elif damage in ("wrong_hash", "wrong_page"):
        declared[1]["unit_sources"] = copy.deepcopy(declared[1]["unit_sources"])
        declared[1]["unit_sources"]["one"][0]["sha256" if damage == "wrong_hash" else "page"] = (
            "c" * 64 if damage == "wrong_hash" else 2)
    elif damage == "same_revision":
        declared[0]["patches"].extend(declared[1]["patches"])
        declared.pop()
    elif damage == "undated":
        declared = [{"patches": [item["patches"][0] for item in declared]}]
    elif damage == "adjacent_noop":
        declared[1]["patches"][0]["to"]["keywords_json"] = "B"
    elif damage == "source_date":
        declared[1]["unit_sources"]["one"][0]["source_date"] = "2026-09-29"
    else:
        for item in declared:
            patch = item["patches"][0]
            patch["table"] = "weapons"
            patch["from"].pop("version", None)
            patch["to"].pop("version", None)
    def forbidden(*args, **kwargs):
        pytest.fail("Invalid cycle must fail before opening SQLite")
    monkeypatch.setattr(reconcile.sqlite3, "connect", forbidden)
    with pytest.raises(ValueError):
        reconcile.apply_patches(tmp_path / "absent.sqlite", {"revisions": declared})


def test_older_standalone_cannot_readd_removed_field_under_newer_sources(tmp_path):
    db = database(tmp_path)
    declared = revisions()
    reconcile.apply_patches(db, manifests=declared)
    before = db.read_bytes()
    with pytest.raises(ValueError, match="Older official revision"):
        reconcile.apply_patches(db, declared[0])
    assert db.read_bytes() == before
    # Older replay remains permitted only if all its supplied final fields exist.
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("UPDATE units SET keywords_json='B'")
    before = db.read_bytes()
    assert reconcile.apply_patches(db, declared[0])["already"] == 1
    assert db.read_bytes() == before


@pytest.mark.parametrize("failure", ["late_guard", "metadata", "base_exception"])
def test_reversal_failure_rolls_back_schema_rows_history_and_releases_handle(tmp_path, monkeypatch, failure):
    db = database(tmp_path)
    declared = revisions()
    if failure == "late_guard":
        declared[1]["patches"].append({"table": "units", "key": {"id": "missing"},
                                      "from": {"version": "old"}, "to": {"version": "new"},
                                      "source": declared[1]["patches"][0]["source"]})
        expected = ValueError
    else:
        original = reconcile._restore_metadata
        expected = KeyboardInterrupt if failure == "base_exception" else RuntimeError
        def fail(conn, manifests):
            original(conn, manifests)
            raise expected("Injected after metadata writes")
        monkeypatch.setattr(reconcile, "_restore_metadata", fail)
    before = db.read_bytes()
    with pytest.raises(expected):
        reconcile.apply_patches(db, manifests=declared)
    assert db.read_bytes() == before
    replacement = tmp_path / "replacement.sqlite"
    replacement.write_bytes(before)
    replacement.replace(db)
