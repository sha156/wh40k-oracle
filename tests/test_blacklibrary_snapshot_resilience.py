"""Bounded replacement controls; real Win32 locks do not diagnose production."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import fetch_blacklibrary_snapshot as module


DELAYS = [0.05, 0.15]
OLD = b'{"old": "preserved"}\n'
VALUE = {"new": "verified", "text": "规则"}


class HeldReader:
    """An explicit read handle with FILE_SHARE_DELETE deliberately absent."""

    def __init__(self, path):
        assert os.name == "nt", "The actual reader controls require Windows"
        self.kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        self.kernel.CreateFileW.argtypes = (
            wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID,
            wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
        self.kernel.CreateFileW.restype = wintypes.HANDLE
        self.kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        self.kernel.CloseHandle.restype = wintypes.BOOL
        self.handle = self.kernel.CreateFileW(str(path.resolve()), 0x80000000,
                                             0x1 | 0x2, None, 3, 0x80, None)
        if self.handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        self.closed = False

    def close(self):
        if not self.closed:
            if not self.kernel.CloseHandle(self.handle):
                raise ctypes.WinError(ctypes.get_last_error())
            self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()


def permission(errno=13, winerror=5):
    error = PermissionError(errno, "private exception text", "C:/private/filename")
    error.errno = errno
    error.winerror = winerror
    return error


def other_oserror():
    # OSError(13, ...) constructs PermissionError on CPython; start with a code
    # that keeps the base type, then supply the matching replacement codes.
    error = OSError(22, "non-permission error")
    assert type(error) is OSError
    error.errno = 13
    error.winerror = 5
    return error


def destination(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_bytes(OLD)
    return path, path.with_suffix(".json.tmp")


def count_preparation(monkeypatch):
    counts = {"encode": 0, "write_bytes": 0}
    encode, write = module.encode, Path.write_bytes

    def counted_encode(value):
        counts["encode"] += 1
        return encode(value)

    def counted_write(path, data):
        counts["write_bytes"] += 1
        return write(path, data)

    monkeypatch.setattr(module, "encode", counted_encode)
    monkeypatch.setattr(Path, "write_bytes", counted_write)
    return counts


def actual_replacements(monkeypatch, target):
    attempts, errors, tracebacks = [], [], []
    replace = Path.replace

    def tracked(path, destination):
        assert destination == target
        attempts.append(path)
        try:
            return replace(path, destination)
        except OSError as exc:
            errors.append(exc)
            tracebacks.append(exc.__traceback__)
            raise

    monkeypatch.setattr(Path, "replace", tracked)
    return attempts, errors, tracebacks


def error_codes(errors):
    return [{"class": type(exc).__name__, "errno": exc.errno,
             "winerror": getattr(exc, "winerror", None)} for exc in errors]


def has_traceback(exc, original):
    current = exc.__traceback__
    while current is not None:
        if current is original:
            return True
        current = current.tb_next
    return False


@pytest.mark.parametrize("release_after", [1, 2])
def test_real_windows_reader_release_recovers_without_diagnostic(tmp_path, monkeypatch, release_after):
    snap = module.Snapshot(tmp_path, session=SimpleNamespace())
    target, temp = destination(tmp_path)
    expected = module.encode(VALUE)
    counts = count_preparation(monkeypatch)
    attempts, errors, _ = actual_replacements(monkeypatch, target)
    sleeps = []
    with HeldReader(target) as reader:
        def release(delay):
            sleeps.append(delay)
            assert target.read_bytes() == OLD and temp.read_bytes() == expected
            assert counts == {"encode": 1, "write_bytes": 1}
            # Unlink/replacement after this read also requires closed handles.
            with temp.open("rb") as stream:
                assert stream.read() == expected
            if len(sleeps) == release_after:
                reader.close()

        monkeypatch.setattr(module.time, "sleep", release)
        result = snap._write_json("manifest.json", VALUE)
    assert sleeps == DELAYS[:release_after]
    assert len(attempts) == release_after + 1 and len(errors) == release_after
    assert error_codes(errors) == [{"class": "PermissionError", "errno": 13, "winerror": 5}] * release_after
    assert target.read_bytes() == expected and not temp.exists() and reader.closed
    assert result == module.digest(expected)
    assert counts == {"encode": 1, "write_bytes": 1}
    assert snap._filesystem_failure is None and "filesystem_error" not in snap.manifest
    (tmp_path / "win32-proof.json").write_text(json.dumps({
        "control": "released_reader", "release_after": release_after,
        "attempts": len(attempts), "delays": sleeps, "actual_errors": error_codes(errors),
        "preparation": counts, "old_bytes_preserved_until_release": True,
        "new_bytes_exact": True, "false_diagnostic": False,
        "handle_closed": reader.closed, "temp_consumed": not temp.exists(),
    }, indent=2), encoding="utf-8")


@pytest.mark.parametrize("observer_fails", [False, True])
def test_real_windows_persistent_reader_preserves_terminal_exception(tmp_path, monkeypatch, observer_fails):
    snap = module.Snapshot(tmp_path, session=SimpleNamespace())
    target, temp = destination(tmp_path)
    counts = count_preparation(monkeypatch)
    attempts, errors, tracebacks = actual_replacements(monkeypatch, target)
    sleeps, observed = [], []

    def wait(delay):
        sleeps.append(delay)
        assert target.read_bytes() == OLD

    def observe(exc, operation):
        observed.append((exc, module.filesystem_diagnostic(exc, "checkpoint", operation, "manifest.json")))
        if observer_fails:
            raise RuntimeError("secondary observer error")

    monkeypatch.setattr(module.time, "sleep", wait)
    with HeldReader(target) as reader:
        with pytest.raises(PermissionError) as caught:
            if observer_fails:
                module.write_json(target, VALUE, on_filesystem_error=observe)
            else:
                snap._write_json("manifest.json", VALUE)
        assert target.read_bytes() == OLD
    exc = caught.value
    assert len(attempts) == 3 and sleeps == DELAYS
    assert error_codes(errors) == [{"class": "PermissionError", "errno": 13, "winerror": 5}] * 3
    assert exc is errors[-1] and has_traceback(exc, tracebacks[-1])
    assert exc.__cause__ is None and exc.__context__ is None
    diagnostic = {"phase": "checkpoint", "operation": "replace", "path": "manifest.json",
                  "class": "PermissionError", "errno": 13, "winerror": 5}
    if observer_fails:
        assert observed == [(exc, diagnostic)]
    else:
        assert snap._filesystem_failure == (exc, diagnostic)
    assert counts == {"encode": 1, "write_bytes": 1}
    assert not temp.exists() and reader.closed
    (tmp_path / "win32-proof.json").write_text(json.dumps({
        "control": "persistent_reader", "observer_fails": observer_fails,
        "attempts": len(attempts), "delays": sleeps, "actual_errors": error_codes(errors),
        "preparation": counts, "diagnostic": diagnostic, "terminal_identity_preserved": True,
        "original_traceback_preserved": True, "context_and_cause_none": True,
        "old_bytes_exact": True, "owned_temp_cleaned": True, "handle_closed": reader.closed,
    }, indent=2), encoding="utf-8")


@pytest.mark.parametrize("platform,error", [
    ("posix", permission()), ("nt", permission(1, 5)), ("nt", permission(13, 32)),
    ("nt", permission(True, 5)), ("nt", permission(13, True)),
    ("nt", permission("13", 5)), ("nt", permission(13, "5")),
    ("nt", permission(13, None)), ("nt", other_oserror()),
    ("nt", FileNotFoundError(2, "absent")), ("nt", KeyboardInterrupt()),
], ids=["non_windows", "errno", "winerror", "bool_errno", "bool_winerror",
        "string_errno", "string_winerror", "missing_winerror", "oserror", "missing", "cancel"])
def test_nonmatching_replace_and_cancellation_never_sleep(tmp_path, monkeypatch, platform, error):
    target, temp = destination(tmp_path)
    calls, sleeps, observed = [], [], []

    def fail(path, destination):
        calls.append(path)
        raise error

    monkeypatch.setattr(module, "os", SimpleNamespace(name=platform))
    monkeypatch.setattr(module.time, "sleep", sleeps.append)
    monkeypatch.setattr(Path, "replace", fail)
    with pytest.raises(type(error)) as caught:
        module.write_json(target, VALUE, on_filesystem_error=lambda exc, op: observed.append((exc, op)))
    assert caught.value is error and len(calls) == 1 and sleeps == []
    assert observed == ([(error, "replace")] if isinstance(error, OSError) else [])
    assert target.read_bytes() == OLD and not temp.exists()


@pytest.mark.parametrize("operation", ["mkdir", "write_bytes"])
@pytest.mark.parametrize("cancel", [False, True])
def test_preparation_failure_does_not_retry_or_delete_unowned_temp(tmp_path, monkeypatch, operation, cancel):
    target, temp = destination(tmp_path)
    temp.write_bytes(b"pre-existing closed temp")
    calls, sleeps, observed = [], [], []
    error = KeyboardInterrupt() if cancel else permission()

    def fail(path, *args, **kwargs):
        calls.append(path)
        raise error

    monkeypatch.setattr(Path, operation, fail)
    monkeypatch.setattr(module.time, "sleep", sleeps.append)
    with pytest.raises(type(error)) as caught:
        module.write_json(target, VALUE, on_filesystem_error=lambda exc, op: observed.append((exc, op)))
    assert caught.value is error and len(calls) == 1 and sleeps == []
    assert target.read_bytes() == OLD and temp.read_bytes() == b"pre-existing closed temp"
    assert observed == ([] if cancel else [(error, operation)])


def test_encoding_failure_preserves_preexisting_temp(tmp_path, monkeypatch):
    target, temp = destination(tmp_path)
    temp.write_bytes(b"unowned")
    observed, sleeps = [], []
    monkeypatch.setattr(module.time, "sleep", sleeps.append)
    with pytest.raises(ValueError):
        module.write_json(target, {"invalid": float("nan")},
                          on_filesystem_error=lambda exc, op: observed.append((exc, op)))
    assert target.read_bytes() == OLD and temp.read_bytes() == b"unowned"
    assert observed == sleeps == []


@pytest.mark.parametrize("cancel_at", ["replace", "sleep"])
@pytest.mark.parametrize("cleanup_error", [OSError(13, "cleanup failed"), KeyboardInterrupt()])
def test_cleanup_failure_cannot_mask_primary_or_cancellation(tmp_path, monkeypatch, cancel_at, cleanup_error):
    target, temp = destination(tmp_path)
    primary = KeyboardInterrupt()
    calls, sleeps, cleanups, observed = [], [], [], []

    def fail_replace(path, destination):
        calls.append(path)
        raise primary if cancel_at == "replace" else permission()

    def fail_sleep(delay):
        sleeps.append(delay)
        raise primary

    def fail_cleanup(path):
        cleanups.append(path)
        raise cleanup_error

    monkeypatch.setattr(module.time, "sleep", fail_sleep)
    monkeypatch.setattr(Path, "replace", fail_replace)
    monkeypatch.setattr(Path, "unlink", fail_cleanup)
    with pytest.raises(KeyboardInterrupt) as caught:
        module.write_json(target, VALUE, on_filesystem_error=lambda exc, op: observed.append((exc, op)))
    assert caught.value is primary and len(calls) == 1
    assert sleeps == ([] if cancel_at == "replace" else [0.05])
    assert cleanups == [temp] and observed == []
    assert target.read_bytes() == OLD and temp.read_bytes() == module.encode(VALUE)


def test_exhausted_error_survives_observer_and_cleanup_failures(tmp_path, monkeypatch):
    target, temp = destination(tmp_path)
    errors = [permission() for _ in range(3)]
    calls, sleeps, observed = [], [], []

    def fail_replace(path, destination):
        calls.append(path)
        raise errors[len(calls) - 1]

    def observer(exc, operation):
        observed.append((exc, operation))
        raise RuntimeError("secondary observer")

    def fail_cleanup(path):
        assert path == temp
        raise PermissionError(13, "secondary cleanup")

    monkeypatch.setattr(module.time, "sleep", sleeps.append)
    monkeypatch.setattr(Path, "replace", fail_replace)
    monkeypatch.setattr(Path, "unlink", fail_cleanup)
    with pytest.raises(PermissionError) as caught:
        module.write_json(target, VALUE, on_filesystem_error=observer)
    assert caught.value is errors[-1] and caught.value.__context__ is None
    assert len(calls) == 3 and sleeps == DELAYS and observed == [(errors[-1], "replace")]
    assert target.read_bytes() == OLD and temp.read_bytes() == module.encode(VALUE)


def test_persistent_denial_semantics_survive(tmp_path, monkeypatch):
    """Same-node parent/candidate control for the unchanged terminal boundary."""
    target, _ = destination(tmp_path)
    errors, observed = [], []
    replace = Path.replace

    def tracked(path, destination):
        try:
            return replace(path, destination)
        except OSError as exc:
            errors.append(exc)
            raise

    def observer(exc, operation):
        observed.append((exc, operation))
        raise RuntimeError("secondary observer")

    monkeypatch.setattr(Path, "replace", tracked)
    monkeypatch.setattr(module.time, "sleep", lambda _: None)
    with HeldReader(target):
        with pytest.raises(PermissionError) as caught:
            module.write_json(target, VALUE, on_filesystem_error=observer)
        assert target.read_bytes() == OLD
    assert caught.value is errors[-1]
    assert error_codes(errors)[-1] == {"class": "PermissionError", "errno": 13, "winerror": 5}
    assert observed == [(caught.value, "replace")]
    assert caught.value.__cause__ is None and caught.value.__context__ is None


@pytest.mark.parametrize("operation", ["mkdir", "write_bytes", "replace"])
def test_cancellation_semantics_survive_at_each_operation(tmp_path, monkeypatch, operation):
    """Both actual revisions must propagate cancellation immediately."""
    target, _ = destination(tmp_path)
    primary, calls, sleeps, observed = KeyboardInterrupt(), [], [], []

    def fail(path, *args, **kwargs):
        calls.append(path)
        raise primary

    monkeypatch.setattr(Path, operation, fail)
    monkeypatch.setattr(module.time, "sleep", sleeps.append)
    with pytest.raises(KeyboardInterrupt) as caught:
        module.write_json(target, VALUE, on_filesystem_error=lambda exc, op: observed.append((exc, op)))
    assert caught.value is primary and len(calls) == 1
    assert observed == sleeps == [] and target.read_bytes() == OLD


@pytest.mark.parametrize("terminal", [permission(13, 32), other_oserror(), KeyboardInterrupt()],
                         ids=["nonmatching", "oserror", "cancel"])
def test_second_attempt_nonmatching_error_or_cancellation_stops_immediately(tmp_path, monkeypatch, terminal):
    target, temp = destination(tmp_path)
    counts = count_preparation(monkeypatch)
    calls, sleeps, observed = [], [], []

    def fail(path, destination):
        calls.append(path)
        raise permission() if len(calls) == 1 else terminal

    monkeypatch.setattr(module.time, "sleep", sleeps.append)
    monkeypatch.setattr(Path, "replace", fail)
    with pytest.raises(type(terminal)) as caught:
        module.write_json(target, VALUE, on_filesystem_error=lambda exc, op: observed.append((exc, op)))
    assert caught.value is terminal and len(calls) == 2 and sleeps == [0.05]
    assert observed == ([(terminal, "replace")] if isinstance(terminal, OSError) else [])
    assert counts == {"encode": 1, "write_bytes": 1}
    assert target.read_bytes() == OLD and not temp.exists()
