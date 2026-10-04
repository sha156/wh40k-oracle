"""Disposable pipeline/CLI regressions; every source declaration is synthetic."""
from contextlib import closing
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from db_compile import source_reconcile, update


def _fixture(tmp_path, bad=False):
    db = tmp_path / "trial.sqlite"
    # The transaction context does not close SQLite's target handle; release it
    # before the CLI child atomically replaces this file on Windows.
    with closing(sqlite3.connect(db)) as conn, conn:
        conn.execute("CREATE TABLE abilities(id TEXT PRIMARY KEY, text_zh TEXT)")
        conn.executemany("INSERT INTO abilities VALUES (?, ?)",
                         [("one", "old"), ("two", "drift" if bad else "old")])
    manifest = tmp_path / "synthetic.json"
    manifest.write_text(json.dumps({"patches": [
        {"table": "abilities", "key": {"id": uid},
         "from": {"text_zh": "old"}, "to": {"text_zh": "new"},
         "source": {"url": "https://example.com/synthetic.pdf",
                    "sha256": "a" * 64, "page": 1}}
        for uid in ("one", "two")]}), encoding="utf-8")
    return db, manifest


def _spy_pipeline(monkeypatch, calls, source_result=None, optional_failure=False):
    """Keep the real ordering and critical flags, replace unrelated asset work."""
    pipeline = []
    for title, original, critical in update._PIPELINE:
        if original is update.stage_source_reconcile and source_result is None:
            fn = original
        else:
            def fn(cfg, original=original):
                calls.append((original.__name__, cfg.offline))
                if original is update.stage_source_reconcile:
                    return source_result
                if original is update.stage_fp_rules:
                    return update.StageResult("fp_rules", not optional_failure,
                                              "synthetic optional stage", warning="retained warning")
                return update.StageResult(original.__name__, True, "asset stage spy")
            fn.__name__ = original.__name__
            fn.writes_db = getattr(original, "writes_db", False)
        pipeline.append((title, fn, critical))
    monkeypatch.setattr(update, "_PIPELINE", pipeline)
    monkeypatch.setattr(update, "_RESTORE_STAGES",
                        [(title, fn) for title, fn, _ in pipeline
                         if getattr(fn, "writes_db", False)])


@pytest.mark.parametrize("entry", [update.restore_authority_layers, update.run_update])
def test_actual_reconcile_drift_stops_every_downstream_stage(tmp_path, monkeypatch, entry):
    db, manifest = _fixture(tmp_path, bad=True)
    calls = []
    _spy_pipeline(monkeypatch, calls)
    report = entry(update.UpdateConfig(db=db, source_reconcile_manifest=manifest))
    assert not report.ok
    assert report.aborted_at == "stage_source_reconcile"
    assert "prior-value mismatch" in report.stages[-1].summary
    assert report.stages[-2].warning == "retained warning"
    expected = ["stage_fp_errata", "stage_fp_rules"]
    if entry is update.run_update:
        expected = ["stage_bsdata_pull", "stage_mfm_fetch", "stage_build"] + expected
    assert [name for name, _ in calls] == expected
    if entry is update.restore_authority_layers:
        assert all(offline for _, offline in calls)
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT * FROM abilities ORDER BY id").fetchall() == [
            ("one", "old"), ("two", "drift")]
        assert not conn.execute("SELECT name FROM sqlite_master WHERE name LIKE 'official_%'").fetchall()


@pytest.mark.parametrize("entry", [update.restore_authority_layers, update.run_update])
def test_revision_union_drift_stops_real_pipeline(tmp_path, monkeypatch, entry):
    db, manifest = _fixture(tmp_path)
    with sqlite3.connect(db) as conn:
        conn.execute("CREATE TABLE models(unit_id TEXT,name TEXT,t INTEGER,m INTEGER)")
        conn.execute("INSERT INTO models VALUES ('model','Synthetic',6,6)")
    source = {"url": "https://example.com/synthetic.pdf", "sha256": "a" * 64, "page": 1}
    # This mixed row has an already-current later t value but stale m. It must
    # never be accepted as C, nor trigger any downstream authority projections.
    manifest.write_text(json.dumps({"revisions": [
        {"source_date": "2026-01-01", "patches": [{"table": "models",
         "key": {"unit_id": "model", "name": "Synthetic"}, "from": {"t": 4},
         "to": {"t": 5}, "source": source}]},
        {"source_date": "2026-02-01", "patches": [{"table": "models",
         "key": {"unit_id": "model", "name": "Synthetic"}, "from": {"t": 5, "m": 6},
         "to": {"t": 6, "m": 8}, "source": source}]}]}), encoding="utf-8")
    calls = []
    _spy_pipeline(monkeypatch, calls)
    report = entry(update.UpdateConfig(db=db, source_reconcile_manifest=manifest))
    assert not report.ok and report.aborted_at == "stage_source_reconcile"
    assert "prior-value mismatch" in report.stages[-1].summary
    expected = ["stage_fp_errata", "stage_fp_rules"]
    if entry is update.run_update:
        expected = ["stage_bsdata_pull", "stage_mfm_fetch", "stage_build"] + expected
    assert [name for name, _ in calls] == expected
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT t,m FROM models").fetchone() == (6, 6)


@pytest.mark.parametrize("entry", [update.restore_authority_layers, update.run_update])
def test_explicit_critical_failure_stops_downstream(tmp_path, monkeypatch, entry):
    calls = []
    _spy_pipeline(monkeypatch, calls, source_result=update.StageResult(
        "source_reconcile", False, "synthetic required failure", warning="failure warning"))
    report = entry(update.UpdateConfig(db=tmp_path / "unused.sqlite"))
    assert not report.ok and report.aborted_at == "source_reconcile"
    assert report.stages[-1].warning == "failure warning"
    assert calls[-1][0] == "stage_source_reconcile"
    assert "stage_mfm_apply" not in [name for name, _ in calls]


@pytest.mark.parametrize("entry", [update.restore_authority_layers, update.run_update])
@pytest.mark.parametrize("optional_failure", [False, True])
def test_legacy_success_and_optional_warning_continue(tmp_path, monkeypatch, entry, optional_failure):
    db, manifest = _fixture(tmp_path)
    monkeypatch.setattr(source_reconcile, "MANIFEST", manifest)
    calls = []
    _spy_pipeline(monkeypatch, calls, optional_failure=optional_failure)
    report = entry(update.UpdateConfig(db=db, offline=True))
    assert report.aborted_at is None
    assert report.ok is (not optional_failure)
    assert next(s for s in report.stages if s.name == "fp_rules").warning == "retained warning"
    assert "stage_mfm_apply" in [name for name, _ in calls]
    assert "stage_zh_weapons" in [name for name, _ in calls]
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT text_zh FROM abilities ORDER BY id").fetchall() == [("new",), ("new",)]


# Run the actual CLI dispatch in another process so return codes cannot be
# mistaken for a printout or a main() return value. Only unrelated asset stages
# are substituted; CSV building, source reconciliation and restore are real.
_CLI_BOOTSTRAP = """
import sys
from pathlib import Path
from db_compile import __main__ as cli, source_reconcile, update
source_reconcile.MANIFEST = Path(sys.argv[2])
pipeline = []
for title, original, critical in update._PIPELINE:
    if original is update.stage_source_reconcile:
        fn = original
    else:
        def fn(cfg, original=original):
            return update.StageResult(original.__name__, True, 'CLI asset stage spy')
        fn.writes_db = getattr(original, 'writes_db', False)
    pipeline.append((title, fn, critical))
update._PIPELINE = pipeline
update._RESTORE_STAGES = [(title, fn) for title, fn, _ in pipeline if getattr(fn, 'writes_db', False)]
sys.argv = ['db_compile', 'build', '--db', sys.argv[1], '--csv-dir', str(Path(sys.argv[1]).parent),
            '--terms', str(Path(sys.argv[1]).with_suffix('.terms.json'))] + sys.argv[3:]
cli.main()
"""


@pytest.mark.parametrize("bad,no_restore,expected", [(True, False, 1), (False, False, 0), (True, True, 0)])
def test_build_cli_process_status(tmp_path, bad, no_restore, expected):
    db, manifest = _fixture(tmp_path, bad=bad)
    (tmp_path / "Abilities.csv").write_text(
        "id|name|description|\none|Synthetic one|old|\ntwo|Synthetic two|"
        + ("drift" if bad else "old") + "|\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", _CLI_BOOTSTRAP, str(db), str(manifest)]
        + (["--no-restore"] if no_restore else []),
        cwd=str(Path(__file__).resolve().parents[1]), capture_output=True,
        encoding="utf-8", timeout=30)
    assert "'abilities': 2" in result.stdout
    assert result.returncode == expected, result.stdout + result.stderr
    if bad and not no_restore:
        assert "prior-value mismatch" in result.stdout
        assert "Required restoration failed" in result.stdout
        assert "CLI asset stage spy" not in result.stdout.split("prior-value mismatch", 1)[1]
    with sqlite3.connect(db) as conn:
        rows = conn.execute("SELECT id, text_zh FROM abilities ORDER BY id").fetchall()
        assert rows == ([("one", "old"), ("two", "drift")] if bad
                        else [("one", "new"), ("two", "new")])
        # Proves the real CSV builder replaced the minimal pre-existing DB.
        assert conn.execute("SELECT name_en FROM abilities WHERE id='one'").fetchone() == ("Synthetic one",)


@pytest.mark.parametrize("entry", [update.restore_authority_layers, update.run_update])
def test_dated_reversal_checkpoint_conflict_aborts_real_pipeline(tmp_path, monkeypatch, entry):
    from tests.test_official_dated_reversals import database, revisions

    db = database(tmp_path, state="A", checkpoint=0)
    manifest = tmp_path / "synthetic-reversal.json"
    manifest.write_text(json.dumps({"revisions": revisions()}), encoding="utf-8")
    before = db.read_bytes()
    calls = []
    _spy_pipeline(monkeypatch, calls)
    report = entry(update.UpdateConfig(db=db, source_reconcile_manifest=manifest))
    assert not report.ok and report.aborted_at == "stage_source_reconcile"
    assert "checkpoint and guarded row disagree" in report.stages[-1].summary
    assert not any(name in ("stage_mfm_apply", "stage_zh_weapons") for name, _ in calls)
    assert db.read_bytes() == before


def test_dated_reversal_fresh_csv_cli_fails_without_manufacturing_history(tmp_path):
    from tests.test_official_dated_reversals import database, revisions

    db = database(tmp_path)
    manifest = tmp_path / "synthetic-reversal.json"
    declared = revisions()
    for item in declared:
        patch = item["patches"][0]
        for values in (patch["from"], patch["to"]):
            values["keywords_json"] = json.dumps({"keywords": [values["keywords_json"]],
                                                 "faction_keywords": []})
            if "version" in values:
                values["version"] = None
    manifest.write_text(json.dumps({"revisions": declared}), encoding="utf-8")
    # The real builder replaces the previous B/checkpoint DB with unanchored CSV
    # A. Restoration must report failure rather than inventing a date for A.
    (tmp_path / "Datasheets.csv").write_text(
        "id|name|faction_id|\none|Synthetic unit|synthetic|\n",
        encoding="utf-8")
    (tmp_path / "Datasheets_keywords.csv").write_text(
        "datasheet_id|keyword|is_faction_keyword|\none|A|false|\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-c", _CLI_BOOTSTRAP, str(db), str(manifest)],
        cwd=str(Path(__file__).resolve().parents[1]), capture_output=True,
        encoding="utf-8", timeout=30)
    assert result.returncode == 1, result.stdout + result.stderr
    assert "Required restoration failed" in result.stdout
    assert "requires preexisting source history" in result.stdout
    with closing(sqlite3.connect(db)) as conn:
        assert not conn.execute("SELECT name FROM sqlite_master WHERE name LIKE 'official_%'").fetchall()
        assert conn.execute("SELECT keywords_json,version FROM units WHERE id='one'").fetchone() == (
            declared[0]["patches"][0]["from"]["keywords_json"], None)
