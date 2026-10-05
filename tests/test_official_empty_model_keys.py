"""Exact empty model names are real composite keys, never owner wildcards."""
import copy
import sqlite3
from contextlib import closing

import pytest

from db_compile import source_reconcile as reconcile


def patch(uid="one", name=""):
    return {"table": "models", "key": {"unit_id": uid, "name": name},
            "from": {"t": "4"}, "to": {"t": "5"},
            "source": {"url": "https://example.com/reviewed.pdf",
                       "sha256": "a" * 64, "page": 38}}


def database(tmp_path):
    db = tmp_path / "models.sqlite"
    # Match the actual schema: no unique index, so verify exact row cardinality.
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("CREATE TABLE units(id TEXT PRIMARY KEY,name_en TEXT)")
        conn.executemany("INSERT INTO units VALUES (?,?)", [("one", "Owner"), ("two", "Other")])
        conn.execute("CREATE TABLE models(unit_id TEXT REFERENCES units(id),name TEXT,t TEXT,w TEXT)")
        conn.executemany("INSERT INTO models VALUES (?,?,?,?)",
                         [("one", "", "4", "2"), ("one", "Named", "4", "3"),
                          ("two", "", "4", "1")])
    return db


def test_exact_empty_key_applies_and_replays_without_touching_siblings(tmp_path):
    db = database(tmp_path)
    manifest = {"patches": [patch()]}
    original = copy.deepcopy(manifest)
    assert reconcile.apply_patches(db, manifest) == {
        "applied": 1, "already": 0, "inserted": 0, "total": 1}
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT unit_id,name,t,w FROM models ORDER BY unit_id,name").fetchall() == [
            ("one", "", "5", "2"), ("one", "Named", "4", "3"), ("two", "", "4", "1")]
    before = db.read_bytes()
    assert reconcile.apply_patches(db, manifest)["already"] == 1
    assert db.read_bytes() == before
    assert manifest == original


@pytest.mark.parametrize("key", [
    {"unit_id": "one"}, {"unit_id": "one", "name": None},
    {"unit_id": "", "name": ""}, {"unit_id": None, "name": ""},
    {"unit_id": "   ", "name": ""}, {"unit_id": 1, "name": ""},
    {"unit_id": "one", "name": "", "id": "invented"},
])
def test_incomplete_or_coerced_identity_rejects_before_database_creation(tmp_path, key):
    target = tmp_path / "absent.sqlite"
    proposed = patch()
    proposed["key"] = key
    with pytest.raises(ValueError, match="identity"):
        reconcile.apply_patches(target, {"patches": [proposed]})
    assert not target.exists()


@pytest.mark.parametrize("damage", ["missing", "null_name", "duplicate", "owner_missing",
                                    "wrong_owner", "case_variant", "schema_type", "owner_duplicate"])
def test_empty_key_requires_actual_unique_text_composite_row_and_exact_owner(tmp_path, damage):
    db = database(tmp_path)
    proposed = patch()
    with closing(sqlite3.connect(db)) as conn, conn:
        if damage == "missing":
            conn.execute("DELETE FROM models WHERE unit_id='one' AND name=''")
        elif damage == "null_name":
            conn.execute("UPDATE models SET name=NULL WHERE unit_id='one' AND name=''")
        elif damage == "duplicate":
            conn.execute("INSERT INTO models VALUES ('one','','4','2')")
        elif damage == "owner_missing":
            conn.execute("DELETE FROM units WHERE id='one'")
        elif damage == "wrong_owner":
            proposed["key"]["unit_id"] = "missing-owner"
        elif damage == "case_variant":
            proposed["key"]["unit_id"] = "ONE"
        elif damage == "owner_duplicate":
            conn.execute("ALTER TABLE units RENAME TO old_units")
            conn.execute("CREATE TABLE units(id TEXT,name_en TEXT)")
            conn.execute("INSERT INTO units SELECT * FROM old_units")
            conn.execute("INSERT INTO units VALUES ('one','Duplicate owner')")
        else:
            conn.execute("ALTER TABLE models RENAME TO old_models")
            conn.execute("CREATE TABLE models(unit_id INTEGER,name TEXT,t TEXT,w TEXT)")
            conn.execute("INSERT INTO models SELECT * FROM old_models")
    before = db.read_bytes()
    with pytest.raises(ValueError, match="Missing|Ambiguous|schema"):
        reconcile.apply_patches(db, {"patches": [proposed]})
    assert db.read_bytes() == before


def test_empty_key_uses_binary_comparison_even_under_nocase_schema(tmp_path):
    db = database(tmp_path)
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("ALTER TABLE models RENAME TO old_models")
        conn.execute("CREATE TABLE models(unit_id TEXT COLLATE NOCASE,name TEXT,t TEXT,w TEXT)")
        conn.execute("INSERT INTO models SELECT * FROM old_models")
        conn.execute("INSERT INTO models VALUES ('ONE','','4','9')")
    assert reconcile.apply_patches(db, {"patches": [patch()]})["applied"] == 1
    with closing(sqlite3.connect(db)) as conn:
        assert conn.execute("SELECT t FROM models WHERE unit_id COLLATE BINARY='ONE'").fetchall() == [("4",)]


def test_empty_key_checks_whole_revision_union_before_applying(tmp_path):
    db = database(tmp_path)
    first = patch()
    second = copy.deepcopy(first)
    second.update({"from": {"t": "5", "w": "2"}, "to": {"t": "6", "w": "3"}})
    revisions = [{"source_date": "2026-09-14", "patches": [first]},
                 {"source_date": "2026-09-30", "patches": [second]}]
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("UPDATE models SET w='wrong guard' WHERE unit_id='one' AND name=''")
    before = db.read_bytes()
    with pytest.raises(ValueError, match="prior-value mismatch"):
        reconcile.apply_patches(db, manifests=revisions)
    assert db.read_bytes() == before


def test_empty_key_cannot_insert_invented_model(tmp_path):
    db = database(tmp_path)
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("DELETE FROM models WHERE unit_id='one' AND name=''")
    proposed = patch()
    proposed["from"] = None
    before = db.read_bytes()
    with pytest.raises(ValueError, match="Missing"):
        reconcile.apply_patches(db, {"patches": [proposed]})
    assert db.read_bytes() == before


@pytest.mark.parametrize("failure", ["late_guard", "metadata", "base_exception", "duplicate_patch"])
def test_empty_model_failure_rolls_back_and_releases_windows_handle(tmp_path, monkeypatch, failure):
    db = database(tmp_path)
    manifest = {"patches": [patch()]}
    expected = ValueError
    if failure == "late_guard":
        bad = patch("two")
        bad["from"]["t"] = "wrong prior"
        manifest["patches"].append(bad)
    elif failure == "duplicate_patch":
        manifest["patches"].append(copy.deepcopy(manifest["patches"][0]))
    else:
        expected = KeyboardInterrupt if failure == "base_exception" else RuntimeError
        restore = reconcile._restore_metadata

        def fail(conn, declared):
            restore(conn, declared)
            raise expected("Injected after row and schema writes")

        monkeypatch.setattr(reconcile, "_restore_metadata", fail)
    before = db.read_bytes()
    with pytest.raises(expected):
        reconcile.apply_patches(db, manifest)
    assert db.read_bytes() == before
    replacement = tmp_path / "replacement.sqlite"
    replacement.write_bytes(before)
    replacement.replace(db)


@pytest.mark.parametrize("table,key", [("units", {"id": ""}), ("weapons", {"id": ""}),
                                     ("abilities", {"id": ""})])
def test_empty_identity_exception_does_not_extend_to_other_tables(tmp_path, table, key):
    proposed = patch()
    proposed.update(table=table, key=key)
    with pytest.raises(ValueError, match="identity"):
        reconcile.apply_patches(tmp_path / "absent.sqlite", {"patches": [proposed]})
