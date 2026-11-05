"""Exact row-chain regressions using synthetic declarations and disposable SQLite."""
import copy
import json
import sqlite3

import pytest

from db_compile import source_reconcile as reconcile


SOURCE = {"url": "https://example.com/synthetic.pdf", "sha256": "a" * 64, "page": 1}


def patch(old, new, uid="one", table="models"):
    key = {"unit_id": uid, "name": "Synthetic model"} if table == "models" else {"id": uid}
    return {"table": table, "key": key, "from": old, "to": new, "source": dict(SOURCE)}


def chain():
    return [patch({"t": 4}, {"t": 5}), patch({"t": 5, "m": 6}, {"t": 6, "m": 8})]


def revisions(patches=None):
    first, second = patches if patches is not None else chain()
    return [{"source_date": "2026-01-01", "patches": [first]},
            {"source_date": "2026-02-01", "patches": [second]}]


def database(tmp_path, state, duplicate=False):
    db = tmp_path / "synthetic.sqlite"
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE models(unit_id TEXT, name TEXT, t INTEGER, m INTEGER, w INTEGER)")
        if state is not None:
            conn.execute("INSERT INTO models VALUES ('one','Synthetic model',?,?,99)", state)
            if duplicate:
                conn.execute("INSERT INTO models VALUES ('one','Synthetic model',?,?,99)", state)
    return db


def snapshot(db):
    with sqlite3.connect(db) as conn:
        return list(conn.iterdump())


@pytest.mark.parametrize("state,applied,already", [((4, 6), 2, 0), ((5, 6), 1, 1), ((6, 8), 0, 2)])
def test_flat_legacy_chain_converges_and_replay_is_read_only(tmp_path, state, applied, already):
    db = database(tmp_path, state)
    manifest = {"patches": chain()}
    report = reconcile.apply_patches(db, manifest)
    assert report == {"applied": applied, "already": already, "inserted": 0, "total": 2}
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT t,m,w FROM models").fetchall() == [(6, 8, 99)]
    before = snapshot(db)
    before_bytes = db.read_bytes()
    assert reconcile.apply_patches(db, manifest) == {"applied": 0, "already": 2, "inserted": 0, "total": 2}
    assert snapshot(db) == before
    assert db.read_bytes() == before_bytes


@pytest.mark.parametrize("state", [(6, 6), (4, 8), (5, 8), (6, 99), (99, 8)])
def test_union_field_mixtures_are_not_reviewed_states(tmp_path, state):
    db = database(tmp_path, state)
    before = snapshot(db)
    with pytest.raises(ValueError, match="prior-value mismatch"):
        reconcile.apply_patches(db, {"patches": chain()})
    assert snapshot(db) == before


@pytest.mark.parametrize("state", [(4, 6), (5, 6), (6, 8)])
@pytest.mark.parametrize("entry", ["keyword", "envelope"])
def test_ordered_manifests_support_both_call_forms(tmp_path, state, entry):
    db = database(tmp_path, state)
    declared = revisions()
    original = copy.deepcopy(declared)
    if entry == "keyword":
        reconcile.apply_patches(db, manifests=declared)
    else:
        reconcile.apply_patches(db, {"revisions": declared})
    assert declared == original
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT t,m,w FROM models").fetchone() == (6, 8, 99)


@pytest.mark.parametrize("kind", ["reverse", "duplicate_date", "bad_date", "missing_date",
                                  "contradiction", "duplicate_patch", "cycle", "empty"])
def test_bad_declarations_fail_before_connection(tmp_path, monkeypatch, kind):
    declared = revisions()
    if kind == "reverse":
        declared.reverse()
    elif kind == "duplicate_date":
        declared[1]["source_date"] = declared[0]["source_date"]
    elif kind == "bad_date":
        declared[1]["source_date"] = "2026-02-30"
    elif kind == "missing_date":
        del declared[1]["source_date"]
    elif kind == "contradiction":
        declared[1]["patches"][0]["from"]["t"] = 999
    elif kind == "duplicate_patch":
        declared[0]["patches"].append(copy.deepcopy(declared[0]["patches"][0]))
    elif kind == "cycle":
        declared[1]["patches"][0] = patch({"t": 5}, {"t": 4})
    else:
        declared = []
    def no_connection(*args, **kwargs):
        pytest.fail("Invalid declarations must fail before opening SQLite")
    monkeypatch.setattr(reconcile.sqlite3, "connect", no_connection)
    with pytest.raises(ValueError):
        reconcile.apply_patches(tmp_path / "uncreated.sqlite", {"revisions": declared})


def test_public_compiler_validates_order_and_backfills_union_fields():
    declared = revisions()
    compiled, = reconcile.compile_revision_chain(declared)
    assert compiled.table == "models"
    assert compiled.key == (("name", "Synthetic model"), ("unit_id", "one"))
    assert compiled.fields == ("m", "t")
    assert compiled.states == ({"t": 4, "m": 6}, {"t": 5, "m": 6}, {"t": 6, "m": 8})
    declared[0]["patches"][0]["to"]["t"] = 999
    assert compiled.transitions[0]["to"] == {"t": 5}
    with pytest.raises(ValueError, match="strictly increasing"):
        reconcile.compile_revision_chain(list(reversed(revisions())))


@pytest.mark.parametrize("kind", ["missing_from", "late_insertion", "boolean_page", "bad_key",
                                  "identity_write", "non_scalar", "noop_in_chain"])
def test_invalid_flat_chain_declarations_fail_before_sql(tmp_path, monkeypatch, kind):
    declared = {"patches": chain()}
    if kind == "missing_from":
        del declared["patches"][0]["from"]
    elif kind == "late_insertion":
        declared["patches"][1]["from"] = None
    elif kind == "boolean_page":
        declared["patches"][0]["source"]["page"] = True
    elif kind == "bad_key":
        del declared["patches"][0]["key"]["name"]
    elif kind == "identity_write":
        declared["patches"][0]["from"] = {"unit_id": "one"}
        declared["patches"][0]["to"] = {"unit_id": "other"}
    elif kind == "non_scalar":
        declared["patches"][0]["to"]["t"] = [5]
    else:
        declared["patches"][0]["to"]["t"] = 4
    def no_connection(*args, **kwargs):
        pytest.fail("Invalid declarations must fail before opening SQLite")
    monkeypatch.setattr(reconcile.sqlite3, "connect", no_connection)
    with pytest.raises(ValueError):
        reconcile.apply_patches(tmp_path / "uncreated.sqlite", declared)


def test_legacy_single_noop_remains_already_current(tmp_path):
    db = database(tmp_path, (4, 6))
    assert reconcile.apply_patches(db, {"patches": [patch({"t": 4}, {"t": 4})]}) == {
        "applied": 0, "already": 1, "inserted": 0, "total": 1}


@pytest.mark.parametrize("failure", ["missing", "drift", "ambiguous"])
def test_later_target_failure_rolls_back_all_tables_and_provenance(tmp_path, failure):
    db = database(tmp_path, (4, 6))
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE abilities(id TEXT, text_zh TEXT)")
        if failure != "missing":
            conn.execute("INSERT INTO abilities VALUES ('two',?)", ("drift" if failure == "drift" else "old",))
            if failure == "ambiguous":
                conn.execute("INSERT INTO abilities VALUES ('two','old')")
        conn.execute("CREATE TABLE official_rule_revisions(unit_id TEXT PRIMARY KEY,source_date TEXT NOT NULL)")
        conn.execute("INSERT INTO official_rule_revisions VALUES ('unrelated','2025-01-01')")
        conn.execute("CREATE TABLE official_unit_sources(unit_id TEXT PRIMARY KEY,sources_json TEXT NOT NULL)")
        conn.execute("INSERT INTO official_unit_sources VALUES ('unrelated','[]')")
    before = snapshot(db)
    declared = revisions()
    declared[0].update(invalidate_translation_for=["one"], unit_sources={"one": [SOURCE]})
    declared[1]["patches"].append(patch({"text_zh": "old"}, {"text_zh": "new"}, "two", "abilities"))
    with pytest.raises(ValueError, match="Missing|mismatch|Ambiguous"):
        reconcile.apply_patches(db, {"revisions": declared})
    assert snapshot(db) == before


@pytest.mark.parametrize("state,inserted,applied,already", [(None, 1, 1, 0), ((4, 6), 0, 1, 1), ((6, 8), 0, 0, 2)])
def test_explicit_absent_insertion_chain(tmp_path, state, inserted, applied, already):
    db = database(tmp_path, state)
    declared = revisions([patch(None, {"t": 4, "m": 6}), patch({"t": 4, "m": 6}, {"t": 6, "m": 8})])
    report = reconcile.apply_patches(db, {"revisions": declared})
    assert report == {"inserted": inserted, "applied": applied, "already": already, "total": 2}
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT t,m FROM models").fetchall() == [(6, 8)]
    before = db.read_bytes()
    assert reconcile.apply_patches(db, {"revisions": declared})["already"] == 2
    assert db.read_bytes() == before


def test_insertion_backfills_a_field_first_touched_later(tmp_path):
    db = database(tmp_path, None)
    declared = {"patches": [patch(None, {"t": 4}), patch({"t": 4, "m": 6}, {"t": 6, "m": 8})]}
    assert reconcile.apply_patches(db, declared)["inserted"] == 1
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT t,m FROM models").fetchone() == (6, 8)
    assert reconcile.apply_patches(db, declared)["already"] == 2


def test_constraint_insertion_failure_rolls_back_earlier_table_changes(tmp_path):
    db = database(tmp_path, (4, 6))
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE abilities(id TEXT PRIMARY KEY, text_zh TEXT UNIQUE)")
        conn.execute("INSERT INTO abilities VALUES ('other','occupied')")
    before = snapshot(db)
    declared = {"patches": chain() + [patch(None, {"text_zh": "occupied"}, "two", "abilities")]}
    with pytest.raises(sqlite3.IntegrityError, match="UNIQUE"):
        reconcile.apply_patches(db, declared)
    assert snapshot(db) == before


@pytest.mark.parametrize("state", [(4, 8), (6, 6), (999, 999)])
def test_insertion_chain_rejects_existing_wrong_row(tmp_path, state):
    db = database(tmp_path, state)
    before = snapshot(db)
    with pytest.raises(ValueError, match="prior-value mismatch"):
        reconcile.apply_patches(db, {"patches": [patch(None, {"t": 4, "m": 6}),
                                               patch({"t": 4, "m": 6}, {"t": 6, "m": 8})]})
    assert snapshot(db) == before


def test_duplicate_canonical_model_identity_is_rejected(tmp_path):
    db = database(tmp_path, (4, 6), duplicate=True)
    before = snapshot(db)
    with pytest.raises(ValueError, match="Ambiguous"):
        reconcile.apply_patches(db, {"patches": chain()})
    assert snapshot(db) == before


def test_complete_model_key_keeps_same_named_units_independent(tmp_path):
    db = database(tmp_path, (4, 6))
    with sqlite3.connect(db) as conn:
        conn.execute("INSERT INTO models VALUES ('other','Synthetic model',10,11,99)")
    reconcile.apply_patches(db, {"patches": chain() + [patch({"t": 10}, {"t": 12}, "other")]})
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT unit_id,t,m FROM models ORDER BY unit_id").fetchall() == [
            ("one", 6, 8), ("other", 12, 11)]


@pytest.mark.parametrize("configured", [False, True])
def test_chain_envelope_can_be_loaded_by_pipeline_contract(tmp_path, monkeypatch, configured):
    db = database(tmp_path, (6, 8))
    path = tmp_path / "synthetic-revisions.json"
    path.write_text(json.dumps({"revisions": revisions()}), encoding="utf-8")
    from db_compile.update import UpdateConfig, stage_source_reconcile
    if configured:
        cfg = UpdateConfig(db=db, source_reconcile_manifest=path)
    else:
        monkeypatch.setattr(reconcile, "MANIFEST", path)
        cfg = UpdateConfig(db=db)
    result = stage_source_reconcile(cfg)
    assert result.ok
    assert "2" in result.summary
