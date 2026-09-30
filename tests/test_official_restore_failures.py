"""Disposable pipeline/CLI regressions; every source declaration is synthetic."""
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from db_compile import source_reconcile, update


def _fixture(tmp_path, bad=False):
    db = tmp_path / "trial.sqlite"
    with sqlite3.connect(db) as conn:
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
    monkeypatch.setattr(source_reconcile, "MANIFEST", manifest)
    calls = []
    _spy_pipeline(monkeypatch, calls)
    report = entry(update.UpdateConfig(db=db))
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
