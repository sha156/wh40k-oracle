"""Real producer/CLI filesystem failures retain redacted context and safe recovery."""
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from db_compile.blacklibrary_snapshot import merge_snapshot
from scripts import fetch_blacklibrary_snapshot as module
from tests.test_blacklibrary_snapshot import Session, snapshot, unit
from tests.test_blacklibrary_snapshot_merge import existing


SECRET = "Bearer private-account credential /unrestricted/private/location"
BOUNDARY_ERROR = "Snapshot manifest or required outputs are incomplete or invalid"
TARGETS = [
    ("catalogs/40k-factions.json", "catalogs"),
    ("raw/unit-list/page-001.json", "unit_inventory"),
    ("details.json", "details"),
]


def frozen_json(root):
    return {path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*.json")}


def inject_write_failure(monkeypatch, out, name, operation, error, *, when=lambda: True):
    """Fail the actual Path operation, not write_json/run or merge validation."""
    target = out / name
    calls = []
    original = getattr(Path, operation)

    def fail(path, *args, **kwargs):
        matches = (path == target.parent if operation == "mkdir" else
                   path == target.with_suffix(".json.tmp") if operation == "write_bytes" else
                   args and args[0] == target)
        if matches and when():
            calls.append(path)
            raise error
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, operation, fail)
    return calls


@pytest.mark.parametrize("name,phase", TARGETS)
@pytest.mark.parametrize("operation", ["mkdir", "write_bytes", "replace"])
def test_actual_write_boundaries_partial_merge_rejection_and_resume(tmp_path, monkeypatch, name, phase, operation):
    # Inline details avoid a manifest checkpoint sharing the root-directory
    # mkdir target before the actual details output in that phase.
    snap = snapshot(tmp_path, Session([unit(inline=name == "details.json")]))
    prior = [existing(), existing(2)]
    original = copy.deepcopy(prior)
    active = tmp_path / "active-cache.json"
    active.write_text(json.dumps(prior), encoding="utf-8")
    active_bytes = active.read_bytes()
    error = PermissionError(13, SECRET, "C:/private/account/file.json")
    error.winerror = 5
    with monkeypatch.context() as patch:
        calls = inject_write_failure(patch, snap.out, name, operation, error,
                                     when=lambda: snap._phase == phase and (
                                         operation != "mkdir" or name != "details.json" or not calls))
        result = snap.run([active])
    diagnostic_path = (name.rpartition("/")[0] or "." if operation == "mkdir"
                       else name + (".tmp" if operation == "write_bytes" else ""))
    expected = {"phase": phase, "operation": operation,
                "path": diagnostic_path,
                "class": "PermissionError", "errno": 13, "winerror": 5}
    # Only the shared-root details mkdir injection is one-shot, so the partial
    # manifest can still be saved there. Other operation counts are independent.
    assert len(calls) == 1
    assert all(meta.get("attempts", 1) == 1 for meta in result["requests"].values())
    assert result["status"] == "partial" and result["error"] == "PermissionError"
    assert result["filesystem_error"] == expected
    persisted = json.loads((snap.out / "manifest.json").read_text(encoding="utf-8"))
    assert persisted["filesystem_error"] == expected
    assert "details.json" not in persisted["outputs"]
    assert result["unit_list_reconciled"] is (phase != "unit_inventory")
    for output, meta in result["outputs"].items():
        data = (snap.out / output).read_bytes()
        assert module.digest(data) == meta["sha256"]
        assert len(json.loads(data)) == meta["records"]
    before = frozen_json(snap.out)
    with pytest.raises(ValueError) as caught:
        merge_snapshot(snap.out, prior)
    assert str(caught.value) == BOUNDARY_ERROR
    assert prior == original and frozen_json(snap.out) == before
    assert active.read_bytes() == active_bytes
    all_json = "".join(data.decode("utf-8") for data in before.values())
    for forbidden in (SECRET, "C:/private/account", "Bearer", "private-account", "unrestricted"):
        assert forbidden not in all_json

    resumed_session = Session()
    resumed = snapshot(tmp_path, resumed_session)
    recovered = resumed.run([active])
    assert recovered["status"] == "complete_known_endpoints"
    assert "filesystem_error" not in recovered and "error" not in recovered
    rows, units, report = merge_snapshot(resumed.out, prior)
    assert report["accepted"] == 1 and report["retained_previous"] == ["2"]
    assert len(units) == 1 and prior == original and active.read_bytes() == active_bytes
    retained = next(row for row in rows if row["id"] == 2)
    assert {key: retained[key] for key in prior[1]} == prior[1]
    # Completed prior outputs/raw captures are reused byte-for-byte on recovery.
    for path, data in before.items():
        if path != "manifest.json":
            assert (resumed.out / path).read_bytes() == data
    if phase == "details":
        assert resumed_session.calls == []


def test_resume_read_error_reports_only_known_phase(tmp_path, monkeypatch):
    snap = snapshot(tmp_path, Session())
    assert snap.run()["status"] == "complete_known_endpoints"
    resumed = snapshot(tmp_path, Session())
    raw = resumed.out / "raw/unit-list/page-001.json"
    original = Path.read_bytes

    def fail(path):
        if path == raw:
            raise PermissionError(13, SECRET, "C:/private/account/filename")
        return original(path)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_bytes", fail)
        result = resumed.run()
    assert result["filesystem_error"] == {"phase": "unit_inventory", "class": "PermissionError", "errno": 13}
    assert result["status"] == "partial" and not result["unit_list_reconciled"]
    assert snapshot(tmp_path, Session()).run()["status"] == "complete_known_endpoints"


@pytest.mark.parametrize("failure_point", ["observer", "all_diagnostics"])
def test_diagnostic_failure_preserves_primary_partial_error_and_checkpoint(tmp_path, monkeypatch, failure_point):
    snap = snapshot(tmp_path, Session())
    primary = PermissionError(13, SECRET)
    original = module.filesystem_diagnostic

    def broken(exc, phase, operation=None, relative_path=None):
        if failure_point == "all_diagnostics" or operation is not None:
            raise RuntimeError("secondary diagnostic credential must never escape")
        return original(exc, phase, operation, relative_path)

    with monkeypatch.context() as patch:
        patch.setattr(module, "filesystem_diagnostic", broken)
        calls = inject_write_failure(patch, snap.out, "details.json", "replace", primary)
        result = snap.run()
    assert len(calls) == 1 and result["status"] == "partial"
    assert result["error"] == "PermissionError"
    if failure_point == "observer":
        assert result["filesystem_error"] == {"phase": "details", "class": "PermissionError", "errno": 13}
    else:
        assert "filesystem_error" not in result
    persisted = (snap.out / "manifest.json").read_text(encoding="utf-8")
    assert "secondary diagnostic" not in persisted and SECRET not in persisted
    assert json.loads(persisted)["error"] == "PermissionError"
    assert snapshot(tmp_path, Session()).run()["status"] == "complete_known_endpoints"


def test_observer_error_reraises_same_original_oserror(tmp_path):
    target = tmp_path / "existing-directory.json"
    target.mkdir()
    errors = []

    def broken(exc, operation):
        errors.append((exc, operation))
        raise RuntimeError(SECRET)

    with pytest.raises(OSError) as caught:
        module.write_json(target, [], on_filesystem_error=broken)
    assert errors == [(caught.value, "replace")]
    assert caught.value.__cause__ is None and target.is_dir()


def test_unknown_error_subclass_and_uncontrolled_output_name_are_redacted(tmp_path, monkeypatch):
    class PrivateAccountCredentialError(PermissionError):
        def __str__(self):
            raise AssertionError("Filesystem exception text must never be read")

    snap = snapshot(tmp_path, Session())
    with monkeypatch.context() as patch:
        inject_write_failure(patch, snap.out, "details.json", "replace", PrivateAccountCredentialError(13, SECRET))
        result = snap.run()
    assert result["error"] == result["filesystem_error"]["class"] == "PermissionError"
    diagnostic = module.filesystem_diagnostic(PermissionError(13, SECRET), "unrestricted-private-phase",
                                              "replace", "../../private-account.json")
    assert diagnostic == {"phase": "unknown", "class": "PermissionError", "errno": 13, "operation": "replace"}


def test_non_integer_os_codes_and_unknown_operation_are_not_recorded():
    error = PermissionError(13, SECRET)
    error.errno = "private-account"
    error.winerror = True
    assert module.filesystem_diagnostic(error, "details", "private-operation", SECRET) == {
        "phase": "details", "class": "PermissionError"}


def test_historical_read_failure_omits_external_cache_path(tmp_path, monkeypatch):
    snap = snapshot(tmp_path, Session())
    cache = tmp_path / "private-account.json"
    cache.write_text("[]", encoding="utf-8")
    original = Path.read_text

    def fail(path, *args, **kwargs):
        if path == cache:
            raise FileNotFoundError(2, SECRET, str(cache))
        return original(path, *args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(Path, "read_text", fail)
        result = snap.run([cache])
    assert result["filesystem_error"] == {"phase": "historical_retention", "class": "FileNotFoundError", "errno": 2}
    assert result["error"] == "FileNotFoundError" and result["status"] == "partial"
    assert cache.read_bytes() == b"[]"


def test_diagnostic_failure_keeps_actual_cli_exit_one(tmp_path, monkeypatch, capsys):
    active = tmp_path / "active-cache.json"
    active.write_text("[]", encoding="utf-8")
    out = tmp_path / "snapshot"
    primary = PermissionError(13, SECRET)

    def broken(*args, **kwargs):
        raise RuntimeError("secondary diagnostic credential")

    monkeypatch.setattr(module.requests, "Session", Session)
    monkeypatch.setattr(module, "filesystem_diagnostic", broken)
    monkeypatch.setattr(sys, "argv", ["fetch_blacklibrary_snapshot", "--out", str(out),
                                     "--historical-cache", str(active)])
    inject_write_failure(monkeypatch, out, "details.json", "replace", primary)
    assert module.main() == 1
    captured = capsys.readouterr()
    summary = json.loads(captured.out.splitlines()[-1])
    assert summary["status"] == "partial" and "filesystem_error" not in summary
    assert captured.err == "" and "credential" not in captured.out
    persisted = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert persisted["error"] == "PermissionError"


@pytest.mark.parametrize("name,phase", TARGETS)
def test_actual_cli_permission_error_is_exit_one_and_recoverable(tmp_path, name, phase):
    """Run the real __main__ entry point in a fresh interpreter, with offline transport."""
    root = Path(__file__).resolve().parents[1]
    out = tmp_path / "snapshot"
    active = tmp_path / "active-cache.json"
    active.write_text(json.dumps([existing(), existing(2)]), encoding="utf-8")
    active_bytes = active.read_bytes()
    harness = tmp_path / "offline_cli.py"
    harness.write_text('''import runpy, sys, time
from pathlib import Path
import requests
from tests.test_blacklibrary_snapshot import Session
time.sleep = lambda _: None
requests.Session = Session
sys.modules.pop("scripts.fetch_blacklibrary_snapshot", None)
out, name, active = sys.argv[1:]
target = Path(out) / name
original = Path.replace
def fail(path, destination):
    if destination == target:
        error = PermissionError(13, "Bearer private-account credential", "C:/private/account/file.json")
        error.winerror = 5
        raise error
    return original(path, destination)
Path.replace = fail
sys.argv = ["fetch_blacklibrary_snapshot", "--out", out, "--historical-cache", active]
runpy.run_module("scripts.fetch_blacklibrary_snapshot", run_name="__main__")
''', encoding="utf-8")
    env = dict(os.environ, PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(root))
    completed = subprocess.run([sys.executable, str(harness), str(out), name, str(active)],
                               cwd=root, env=env, capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert completed.returncode == 1 and completed.stderr == ""
    summary = json.loads(completed.stdout.splitlines()[-1])
    assert summary["status"] == "partial"
    assert summary["filesystem_error"] == {"phase": phase, "operation": "replace", "path": name,
                                           "class": "PermissionError", "errno": 13, "winerror": 5}
    assert "Bearer" not in completed.stdout and "private-account" not in completed.stdout
    assert "C:/private/account" not in completed.stdout
    before = frozen_json(out)
    with pytest.raises(ValueError) as caught:
        merge_snapshot(out, [existing(), existing(2)])
    assert str(caught.value) == BOUNDARY_ERROR and frozen_json(out) == before
    stage = tmp_path / "merge-staging"
    merge_cli = subprocess.run([sys.executable, "-m", "db_compile.blacklibrary_snapshot",
                                "--snapshot", str(out), "--existing", str(active), "--out", str(stage)],
                               cwd=root, env=env, capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert merge_cli.returncode == 1 and BOUNDARY_ERROR in merge_cli.stderr
    assert "KeyError" not in merge_cli.stderr and "Bearer" not in merge_cli.stderr
    assert not stage.exists() and frozen_json(out) == before
    assert active.read_bytes() == active_bytes
    resumed = module.Snapshot(out, session=Session(), interval=0, sleep=lambda _: None)
    assert resumed.run([active])["status"] == "complete_known_endpoints"
    _, _, report = merge_snapshot(out, [existing(), existing(2)])
    assert report["accepted"] == 1 and report["retained_previous"] == ["2"]
    assert active.read_bytes() == active_bytes
