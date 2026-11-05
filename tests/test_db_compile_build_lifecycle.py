"""Real SQLite handles must be released before Windows replacement or cleanup."""
import sqlite3

import pytest

import db_compile.build as build


def _track_connections(monkeypatch, events, fail_at=None, close_errors=False):
    connect = sqlite3.connect
    owned = []  # Retain handles: correctness must not depend on garbage collection.

    class Cursor(sqlite3.Cursor):
        def close(self):
            events.append("cursor.close")
            super().close()
            if close_errors:
                raise RuntimeError("cursor close failed")

    class Connection(sqlite3.Connection):
        def cursor(self):
            if fail_at == "cursor":
                raise ValueError("cursor failed")
            cur = super().cursor(factory=Cursor)
            owned.append(cur)
            return cur

        def commit(self):
            if fail_at == "commit":
                raise ValueError("commit failed")
            events.append("commit")
            super().commit()

        def close(self):
            events.append("connection.close")
            super().close()
            if close_errors:
                raise RuntimeError("connection close failed")

    def tracked_connect(*args, **kwargs):
        conn = connect(*args, **kwargs, factory=Connection)
        owned.append(conn)
        return conn

    monkeypatch.setattr(build.sqlite3, "connect", tracked_connect)
    return owned


def test_committed_replacement_releases_retained_handles(tmp_path, monkeypatch):
    events = []
    owned = _track_connections(monkeypatch, events)
    target = tmp_path / "target.sqlite"
    target.write_bytes(b"original target")
    monkeypatch.setattr(build, "preserve_archived_units", lambda *args: 0)
    replace = build.os.replace

    def checked_replace(source, destination):
        assert events == ["commit", "cursor.close", "connection.close"]
        assert target.read_bytes() == b"original target"
        replace(source, destination)
        events.append("replace")

    monkeypatch.setattr(build.os, "replace", checked_replace)
    build.build_database(tmp_path, target)
    assert owned and events[-1] == "replace"
    assert target.read_bytes().startswith(b"SQLite format 3")
    assert not target.with_suffix(".tmp.sqlite").exists()
    # Closed means closed even though strong references still exist.
    with pytest.raises(sqlite3.ProgrammingError):
        owned[0].execute("SELECT 1")


@pytest.mark.parametrize("stage", ["connect", "cursor", "schema", "archive", "commit", "replace"])
def test_failure_preserves_original_bytes_and_removes_temp(tmp_path, monkeypatch, stage):
    events = []
    owned = _track_connections(monkeypatch, events, fail_at=stage)
    target = tmp_path / "target.sqlite"
    target.write_bytes(b"original target")
    original_error = ValueError(stage + " failed")

    def fail(*args, **kwargs):
        raise original_error

    monkeypatch.setattr(build, "preserve_archived_units", lambda *args: 0)
    if stage == "connect":
        monkeypatch.setattr(build.sqlite3, "connect", fail)
    elif stage == "schema":
        monkeypatch.setattr(build, "ensure_columns", fail)
    elif stage == "archive":
        monkeypatch.setattr(build, "preserve_archived_units", fail)
    elif stage == "replace":
        monkeypatch.setattr(build.os, "replace", fail)

    with pytest.raises(ValueError, match=stage + " failed") as caught:
        build.build_database(tmp_path, target)
    if stage not in ("cursor", "commit"):
        assert caught.value is original_error
    assert target.read_bytes() == b"original target"
    assert not target.with_suffix(".tmp.sqlite").exists()
    if stage == "connect":
        assert not owned and not events
    elif stage == "cursor":
        assert events == ["connection.close"]
    else:
        assert events[-2:] == ["cursor.close", "connection.close"]
    if owned:
        with pytest.raises(sqlite3.ProgrammingError):
            owned[0].execute("SELECT 1")


@pytest.mark.parametrize("primary", [ValueError("archive failed"), KeyboardInterrupt("interrupted")])
def test_close_errors_do_not_mask_build_exception(tmp_path, monkeypatch, primary):
    events = []
    owned = _track_connections(monkeypatch, events, close_errors=True)
    target = tmp_path / "target.sqlite"
    target.write_bytes(b"original target")

    def fail(*args):
        raise primary

    monkeypatch.setattr(build, "preserve_archived_units", fail)
    with pytest.raises(type(primary)) as caught:
        build.build_database(tmp_path, target)
    assert caught.value is primary
    assert events == ["cursor.close", "connection.close"]
    assert owned and target.read_bytes() == b"original target"
    assert not target.with_suffix(".tmp.sqlite").exists()


def test_close_error_aborts_replacement_and_still_closes_connection(tmp_path, monkeypatch):
    events = []
    owned = _track_connections(monkeypatch, events, close_errors=True)
    target = tmp_path / "target.sqlite"
    target.write_bytes(b"original target")
    monkeypatch.setattr(build, "preserve_archived_units", lambda *args: 0)
    with pytest.raises(RuntimeError, match="cursor close failed"):
        build.build_database(tmp_path, target)
    assert events == ["commit", "cursor.close", "connection.close"]
    assert owned and target.read_bytes() == b"original target"
    assert not target.with_suffix(".tmp.sqlite").exists()


def test_caller_exception_does_not_hide_success_path_close_error(tmp_path, monkeypatch):
    events = []
    _track_connections(monkeypatch, events, close_errors=True)
    target = tmp_path / "target.sqlite"
    target.write_bytes(b"original target")
    monkeypatch.setattr(build, "preserve_archived_units", lambda *args: 0)
    try:
        raise ValueError("unrelated caller exception")
    except ValueError:
        with pytest.raises(RuntimeError, match="cursor close failed"):
            build.build_database(tmp_path, target)
    assert target.read_bytes() == b"original target"
    assert not target.with_suffix(".tmp.sqlite").exists()
