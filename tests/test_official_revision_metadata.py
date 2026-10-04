"""Synthetic provenance chronology; never publish these sources as official data."""
import copy
import json
import sqlite3
import subprocess
import sys
from contextlib import closing
from pathlib import Path

import pytest

from db_compile import source_reconcile as reconcile


def source(letter="a", **extra):
    return {"url": f"https://example.com/synthetic-{letter}.pdf",
            "sha256": letter * 64, "page": 1, **extra}


def manifest(day="2026-01-01", letter="a", old="old", new="new"):
    return {"source_date": day, "patches": [{"table": "abilities", "key": {"id": "rule"},
            "from": {"text_zh": old}, "to": {"text_zh": new}, "source": source(letter)}],
            "invalidate_translation_for": ["one"], "unit_sources": {"one": [source(letter)]}}


def database(tmp_path):
    db = tmp_path / "synthetic.sqlite"
    # Commit/rollback before closing the parent target handed to the CLI child.
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("CREATE TABLE units(id TEXT PRIMARY KEY)")
        conn.execute("INSERT INTO units VALUES ('one')")
        conn.execute("CREATE TABLE abilities(id TEXT PRIMARY KEY,text_zh TEXT)")
        conn.execute("INSERT INTO abilities VALUES ('rule','old')")
    return db


@pytest.mark.parametrize("fail_insert", [False, True])
def test_database_fixture_closes_real_handle_and_preserves_transaction(tmp_path, monkeypatch, fail_insert):
    real_connect = sqlite3.connect
    handles = []
    failure = RuntimeError("fixture insert failed")

    class Connection(sqlite3.Connection):
        def execute(self, sql, *args, **kwargs):
            if fail_insert and sql == "INSERT INTO abilities VALUES ('rule','old')":
                raise failure
            return super().execute(sql, *args, **kwargs)

    def retained_connect(*args, **kwargs):
        conn = real_connect(*args, **kwargs, factory=Connection)
        handles.append(conn)
        return conn

    monkeypatch.setattr(sqlite3, "connect", retained_connect)
    if fail_insert:
        with pytest.raises(RuntimeError) as caught:
            database(tmp_path)
        assert caught.value is failure
    else:
        assert database(tmp_path) == tmp_path / "synthetic.sqlite"
    assert len(handles) == 1
    with pytest.raises(sqlite3.ProgrammingError, match="closed"):
        handles[0].execute("SELECT 1")
    db = tmp_path / "synthetic.sqlite"
    with closing(real_connect(db)) as conn:
        assert conn.execute("SELECT * FROM units").fetchall() == ([] if fail_insert else [("one",)])
        if fail_insert:
            assert not conn.execute("SELECT name FROM sqlite_master WHERE name='abilities'").fetchall()
        else:
            assert conn.execute("SELECT * FROM abilities").fetchall() == [("rule", "old")]
    replacement = tmp_path / "replacement.sqlite"
    replacement.write_bytes(db.read_bytes())
    replacement.replace(db)
    assert not replacement.exists()


def snapshot(db):
    with sqlite3.connect(db) as conn:
        return list(conn.iterdump())


def current(db):
    with sqlite3.connect(db) as conn:
        return (conn.execute("SELECT source_date FROM official_rule_revisions WHERE unit_id='one'").fetchone()[0],
                reconcile.unit_sources(conn, "one"))


def test_replay_is_write_free_including_provenance(tmp_path):
    db = database(tmp_path)
    declared = manifest()
    reconcile.apply_patches(db, declared)
    before = db.read_bytes()
    assert reconcile.apply_patches(db, declared)["already"] == 1
    assert db.read_bytes() == before
    assert current(db) == ("2026-01-01", [source()])


def test_older_replay_retains_exact_newer_provenance(tmp_path):
    db = database(tmp_path)
    old = manifest()
    # Identical rule text makes this an independent provenance regression,
    # without allowing an older row chain to accept unknown current row values.
    newer = manifest("2026-02-01", "b")
    reconcile.apply_patches(db, old)
    reconcile.apply_patches(db, newer)
    before = db.read_bytes()
    assert reconcile.apply_patches(db, old)["already"] == 1
    assert current(db) == ("2026-02-01", [source("b")])
    assert db.read_bytes() == before


@pytest.mark.parametrize("start", ["old", "middle", "new"])
def test_ordered_rows_and_provenance_converge_and_replay(tmp_path, start):
    db = database(tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE abilities SET text_zh=?", (start,))
    declared = [manifest(new="middle"), manifest("2026-02-01", "b", "middle", "new")]
    reconcile.apply_patches(db, manifests=declared)
    assert current(db) == ("2026-02-01", [source("b")])
    before = db.read_bytes()
    assert reconcile.apply_patches(db, manifests=declared)["already"] == 2
    assert db.read_bytes() == before


@pytest.mark.parametrize("mutation", ["bad_ids", "duplicate_ids", "bad_uid", "bad_map", "bad_list",
    "empty_list", "bad_source", "bad_url", "bad_hash", "boolean_page", "zero_page",
    "bad_published", "bad_version", "missing_date", "null_date", "bad_date",
    "duplicate_source", "conflicting_source", "bad_additional", "bad_additional_date"])
def test_malformed_metadata_rejected_before_connection(tmp_path, monkeypatch, mutation):
    declared = manifest()
    s = declared["unit_sources"]["one"][0]
    if mutation == "bad_ids":
        declared["invalidate_translation_for"] = "one"
    elif mutation == "duplicate_ids":
        declared["invalidate_translation_for"] = ["one", "one"]
    elif mutation == "bad_uid":
        declared["unit_sources"] = {"": [source()]}
    elif mutation == "bad_map":
        declared["unit_sources"] = []
    elif mutation == "bad_list":
        declared["unit_sources"]["one"] = source()
    elif mutation == "empty_list":
        declared["unit_sources"]["one"] = []
    elif mutation == "bad_source":
        declared["unit_sources"]["one"] = [None]
    elif mutation == "bad_url":
        s["url"] = "https://"
    elif mutation == "bad_hash":
        s["sha256"] = "incorrect"
    elif mutation == "boolean_page":
        s["page"] = True
    elif mutation == "zero_page":
        s["page"] = 0
    elif mutation == "bad_published":
        s["published"] = "2026-02-30"
    elif mutation == "bad_version":
        s["version"] = {"guess": "v2"}
    elif mutation == "missing_date":
        del declared["source_date"]
    elif mutation == "null_date":
        declared["source_date"] = None
    elif mutation == "bad_date":
        declared["source_date"] = "2026-02-30"
    elif mutation == "duplicate_source":
        declared["unit_sources"]["one"].append(copy.deepcopy(s))
    elif mutation == "conflicting_source":
        declared["unit_sources"]["one"].append({**s, "sha256": "b" * 64})
    elif mutation == "bad_additional":
        declared["patches"][0]["additional_sources"] = [None]
    else:
        declared["patches"][0]["additional_sources"] = [source(published="2026-02-30")]
    def no_connection(*args, **kwargs):
        pytest.fail("Malformed declarations must fail before SQLite access")
    monkeypatch.setattr(reconcile.sqlite3, "connect", no_connection)
    with pytest.raises(ValueError):
        reconcile.apply_patches(tmp_path / "uncreated.sqlite", declared)


@pytest.mark.parametrize("change", ["url", "sha256", "page", "version", "published", "title"])
def test_same_date_conflicting_source_identity_rolls_back_row(tmp_path, change):
    db = database(tmp_path)
    reconcile.apply_patches(db, manifest())
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE abilities SET text_zh='old'")
    before = snapshot(db)
    declared = manifest()
    declared["unit_sources"]["one"][0][change] = {
        "url": "https://example.com/different.pdf", "sha256": "b" * 64,
        "page": 2, "version": "v2", "published": "2025-12-01", "title": "Different",
    }[change]
    with pytest.raises(ValueError, match="source|provenance"):
        reconcile.apply_patches(db, declared)
    assert snapshot(db) == before


@pytest.mark.parametrize("bad", ["invalid_json", "bad_shape", "wrong_current", "bad_revision_date", "duplicate_current"])
def test_existing_metadata_failure_rolls_back_every_row_and_table(tmp_path, bad):
    db = database(tmp_path)
    reconcile.apply_patches(db, manifest())
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE abilities SET text_zh='old'")
        if bad == "bad_revision_date":
            conn.execute("UPDATE official_rule_revisions SET source_date='2026-02-30'")
        elif bad == "duplicate_current":
            conn.execute("ALTER TABLE official_unit_sources RENAME TO saved_sources")
            conn.execute("CREATE TABLE official_unit_sources(unit_id TEXT,sources_json TEXT)")
            conn.executemany("INSERT INTO official_unit_sources VALUES ('one',?)", [(json.dumps([source()]),)] * 2)
        else:
            value = {"invalid_json": "{broken", "bad_shape": "{}", "wrong_current": json.dumps([source("c")])}[bad]
            conn.execute("UPDATE official_unit_sources SET sources_json=?", (value,))
    before = snapshot(db)
    with pytest.raises(ValueError, match="source|provenance|date|Ambiguous"):
        reconcile.apply_patches(db, manifest("2026-02-01", "b"))
    assert snapshot(db) == before


def test_legacy_provenance_adoption_requires_exact_declared_source_state(tmp_path):
    db = database(tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE official_unit_sources(unit_id TEXT PRIMARY KEY,sources_json TEXT NOT NULL)")
        # Retain legacy JSON bytes/key ordering, and sources from unrelated units.
        raw = json.dumps([source()], indent=2)
        conn.execute("INSERT INTO official_unit_sources VALUES ('one',?)", (raw,))
        conn.execute("INSERT INTO official_unit_sources VALUES ('unrelated','[]')")
        conn.execute("CREATE TABLE official_rule_revisions(unit_id TEXT PRIMARY KEY,source_date TEXT NOT NULL)")
        conn.execute("INSERT INTO official_rule_revisions VALUES ('unrelated','2025-01-01')")
    reconcile.apply_patches(db, manifest())
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT sources_json FROM official_unit_sources WHERE unit_id='one'").fetchone() == (raw,)
        assert conn.execute("SELECT sources_json FROM official_unit_sources WHERE unit_id='unrelated'").fetchone() == ("[]",)
        assert conn.execute("SELECT source_date FROM official_rule_revisions WHERE unit_id='unrelated'").fetchone() == ("2025-01-01",)
    before = db.read_bytes()
    reconcile.apply_patches(db, manifest())
    assert db.read_bytes() == before


def test_unknown_legacy_sources_are_not_overwritten_by_a_later_date(tmp_path):
    db = database(tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE official_unit_sources(unit_id TEXT PRIMARY KEY,sources_json TEXT NOT NULL)")
        conn.execute("INSERT INTO official_unit_sources VALUES ('one',?)", (json.dumps([source("c")]),))
    before = snapshot(db)
    with pytest.raises(ValueError, match="source|provenance"):
        reconcile.apply_patches(db, manifest())
    assert snapshot(db) == before


def test_replayed_older_conflicting_identity_is_not_hidden_by_newest_date(tmp_path):
    db = database(tmp_path)
    newer = manifest("2026-02-01", "b")
    newer["patches"] = []
    reconcile.apply_patches(db, manifests=[manifest(), newer])
    before = snapshot(db)
    with pytest.raises(ValueError, match="source|provenance"):
        reconcile.apply_patches(db, manifest(letter="c"))
    assert snapshot(db) == before


def test_metadata_missing_unit_rolls_back_rows_and_new_tables(tmp_path):
    db = database(tmp_path)
    before = snapshot(db)
    declared = manifest()
    declared["unit_sources"]["missing"] = [source()]
    with pytest.raises(ValueError, match="Missing.*target"):
        reconcile.apply_patches(db, declared)
    assert snapshot(db) == before


def test_history_and_current_sources_roll_back_on_later_metadata_failure(tmp_path):
    db = database(tmp_path)
    reconcile.apply_patches(db, manifest())
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE abilities SET text_zh='old'")
    before = snapshot(db)
    declared = manifest("2026-02-01", "b")
    declared["unit_sources"]["missing"] = [source()]
    with pytest.raises(ValueError, match="Missing.*target"):
        reconcile.apply_patches(db, declared)
    assert snapshot(db) == before


def test_sources_keep_all_citation_fields_and_later_changes_are_guarded(tmp_path):
    db = database(tmp_path)
    declared = manifest()
    declared["unit_sources"]["one"] = [source(title="Synthetic", version="v1",
        kind="official-preview-image", published="2025-12-01", article="https://example.com/article")]
    original = copy.deepcopy(declared)
    reconcile.apply_patches(db, declared)
    assert current(db)[1] == original["unit_sources"]["one"]
    assert declared == original
    newer = manifest("2026-02-01", "b")
    reconcile.apply_patches(db, newer)
    assert current(db)[1] == [source("b")]


@pytest.mark.parametrize("entry_name", ["restore_authority_layers", "run_update"])
def test_actual_pipeline_aborts_on_metadata_conflict(tmp_path, monkeypatch, entry_name):
    from db_compile import update
    from tests.test_official_restore_failures import _spy_pipeline
    db = database(tmp_path)
    reconcile.apply_patches(db, manifest())
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE abilities SET text_zh='old'")
    before = snapshot(db)
    path = tmp_path / "synthetic.json"
    path.write_text(json.dumps(manifest(letter="b")), encoding="utf-8")
    calls = []
    _spy_pipeline(monkeypatch, calls)
    report = getattr(update, entry_name)(update.UpdateConfig(db=db, source_reconcile_manifest=path))
    assert not report.ok and report.aborted_at == "stage_source_reconcile"
    assert "source" in report.stages[-1].summary
    expected = ["stage_fp_errata", "stage_fp_rules"]
    if entry_name == "run_update":
        expected = ["stage_bsdata_pull", "stage_mfm_fetch", "stage_build"] + expected
    assert [name for name, _ in calls] == expected
    assert snapshot(db) == before


@pytest.mark.parametrize("kind", ["bad_date", "bad_json", "bad_list", "missing_current", "duplicate_date"])
def test_tampered_source_chronology_cannot_authorize_a_newer_source(tmp_path, kind):
    db = database(tmp_path)
    reconcile.apply_patches(db, manifest())
    with sqlite3.connect(db) as conn:
        conn.execute("UPDATE abilities SET text_zh='old'")
        if kind == "bad_date":
            conn.execute("UPDATE official_unit_source_revisions SET source_date='2026-02-30'")
        elif kind in ("bad_json", "bad_list"):
            conn.execute("UPDATE official_unit_source_revisions SET sources_json=?",
                         ("{broken" if kind == "bad_json" else "[]",))
        elif kind == "missing_current":
            conn.execute("DELETE FROM official_unit_sources")
        else:
            conn.execute("ALTER TABLE official_unit_source_revisions RENAME TO saved_history")
            conn.execute("CREATE TABLE official_unit_source_revisions(unit_id TEXT,source_date TEXT,sources_json TEXT)")
            conn.execute("INSERT INTO official_unit_source_revisions SELECT * FROM saved_history")
            conn.execute("INSERT INTO official_unit_source_revisions SELECT * FROM saved_history")
    before = snapshot(db)
    with pytest.raises(ValueError, match="source|provenance|date|Ambiguous"):
        reconcile.apply_patches(db, manifest("2026-02-01", "b"))
    assert snapshot(db) == before


def test_revision_date_does_not_silently_redate_an_unknown_legacy_list(tmp_path):
    db = database(tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE official_rule_revisions(unit_id TEXT PRIMARY KEY,source_date TEXT NOT NULL)")
        conn.execute("INSERT INTO official_rule_revisions VALUES ('one','2026-03-01')")
        conn.execute("CREATE TABLE official_unit_sources(unit_id TEXT PRIMARY KEY,sources_json TEXT NOT NULL)")
        conn.execute("INSERT INTO official_unit_sources VALUES ('one',?)", (json.dumps([source("c")]),))
    before = snapshot(db)
    with pytest.raises(ValueError, match="legacy.*source"):
        reconcile.apply_patches(db, manifest())
    assert snapshot(db) == before


def test_reintroduced_superseded_source_list_is_rejected(tmp_path):
    db = database(tmp_path)
    reconcile.apply_patches(db, manifest())
    reconcile.apply_patches(db, manifest("2026-02-01", "b"))
    before = snapshot(db)
    with pytest.raises(ValueError, match="Revisited.*source"):
        reconcile.apply_patches(db, manifest("2026-03-01", "a"))
    assert snapshot(db) == before


def test_new_metadata_conflict_returns_nonzero_from_actual_csv_build_cli(tmp_path):
    from tests.test_official_restore_failures import _CLI_BOOTSTRAP
    db = database(tmp_path)
    declared = manifest()
    declared["unit_sources"]["one"][0]["published"] = "2026-02-30"
    path = tmp_path / "synthetic.json"
    path.write_text(json.dumps(declared), encoding="utf-8")
    (tmp_path / "Abilities.csv").write_text(
        "id|name|description|\nrule|Synthetic rule|old|\n", encoding="utf-8")
    result = subprocess.run([sys.executable, "-X", "utf8", "-c", _CLI_BOOTSTRAP, str(db), str(path)],
        cwd=str(Path(__file__).resolve().parents[1]), capture_output=True, encoding="utf-8", timeout=30)
    assert "'abilities': 1" in result.stdout
    assert result.returncode == 1, result.stdout + result.stderr
    assert "Invalid source date" in result.stdout
    assert "Required restoration failed" in result.stdout
    assert "CLI asset stage spy" not in result.stdout.split("Invalid source date", 1)[1]
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT text_zh FROM abilities").fetchall() == [("old",)]
        assert not conn.execute("SELECT name FROM sqlite_master WHERE name LIKE 'official_%'").fetchall()


@pytest.mark.parametrize("kind", ["snapshot_reversion", "hash_reversion_with_companion", "published_downgrade",
                                  "same_hash_changed_version", "same_hash_removed_date", "cross_page_hash_conflict"])
def test_source_chronology_contradictions_fail_before_sql(tmp_path, monkeypatch, kind):
    first = manifest()
    second = manifest("2026-02-01", "b")
    third = manifest("2026-03-01", "c")
    for declared in (first, second, third):
        declared["patches"] = []
    if kind == "snapshot_reversion":
        third["unit_sources"] = copy.deepcopy(first["unit_sources"])
    elif kind == "hash_reversion_with_companion":
        second["unit_sources"]["one"] = [{**source(), "sha256": "b" * 64}]
        third["unit_sources"]["one"] = [source(), source("c")]
    elif kind == "published_downgrade":
        first["unit_sources"]["one"] = [source(published="2025-12-01")]
        second["unit_sources"]["one"] = [{**source(), "sha256": "b" * 64, "published": "2025-11-01"}]
    elif kind == "same_hash_changed_version":
        first["unit_sources"]["one"] = [source(version="v2")]
        second["unit_sources"]["one"] = [source(version="v1")]
    elif kind == "same_hash_removed_date":
        first["unit_sources"]["one"] = [source(published="2025-12-01")]
        second["unit_sources"]["one"] = [source()]
    else:
        first["unit_sources"]["one"] = [source(), {**source(), "page": 2, "sha256": "b" * 64}]
    def no_connection(*args, **kwargs):
        pytest.fail("Source chronology contradictions must fail before SQLite")
    monkeypatch.setattr(reconcile.sqlite3, "connect", no_connection)
    with pytest.raises(ValueError):
        reconcile.apply_patches(tmp_path / "uncreated.sqlite", manifests=[first, second, third])


def test_same_document_distinct_pages_and_unchanged_snapshot_are_supported(tmp_path):
    db = database(tmp_path)
    first = manifest()
    first["unit_sources"]["one"] = [source(version="v1"), source(page=2, version="v1")]
    second = {**copy.deepcopy(first), "source_date": "2026-02-01", "patches": []}
    reconcile.apply_patches(db, manifests=[first, second])
    assert current(db) == ("2026-02-01", first["unit_sources"]["one"])
    before = db.read_bytes()
    reconcile.apply_patches(db, manifests=[first, second])
    assert db.read_bytes() == before


@pytest.mark.parametrize("location", ["other_unit", "patch_source", "additional_source"])
def test_conflicting_document_declarations_across_a_revision_fail_before_sql(tmp_path, monkeypatch, location):
    declared = manifest()
    conflicting = {**source(), "page": 2, "sha256": "b" * 64}
    if location == "other_unit":
        declared["unit_sources"]["two"] = [conflicting]
    elif location == "patch_source":
        declared["patches"][0]["source"] = conflicting
    else:
        declared["patches"][0]["source"] = source("c")
        declared["patches"][0]["additional_sources"] = [conflicting]
    def no_connection(*args, **kwargs):
        pytest.fail("A revision cannot declare two hashes for the same source URL")
    monkeypatch.setattr(reconcile.sqlite3, "connect", no_connection)
    with pytest.raises(ValueError, match="Conflicting source declarations"):
        reconcile.apply_patches(tmp_path / "uncreated.sqlite", declared)
