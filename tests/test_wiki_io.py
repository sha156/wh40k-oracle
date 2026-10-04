"""wiki_engine/_io.py 测试：原子写与生成内容哈希登记表。"""
from __future__ import annotations

import os
import stat
from types import SimpleNamespace

import pytest

from wiki_engine import _io

from wiki_engine._io import (
    GEN_HASHES_NAME,
    GenHashesCorrupt,
    atomic_write_text,
    load_gen_hashes,
    save_gen_hashes,
    text_sha256,
)


class TestAtomicWriteText:
    def test_actual_replace_rejection_cleans_owned_temp(self, tmp_path):
        target = tmp_path / "occupied-directory"
        target.mkdir()
        child = target / "original"
        child.write_bytes(b"preserve original bytes")
        planted = tmp_path / "occupied-directory.tmp"
        planted.write_bytes(b"unrelated")
        with pytest.raises(OSError):
            atomic_write_text(target, "replacement")
        assert child.read_bytes() == b"preserve original bytes"
        assert planted.read_bytes() == b"unrelated"
        assert set(tmp_path.iterdir()) == {target, planted}

    def test_real_read_only_target_permissions(self, tmp_path):
        target = tmp_path / "page"
        target.write_bytes(b"original")
        target.chmod(stat.S_IREAD)
        try:
            if os.name == "nt":
                with pytest.raises(PermissionError):
                    atomic_write_text(target, "replacement")
                assert target.read_bytes() == b"original"
            else:
                atomic_write_text(target, "replacement")
                assert target.read_text() == "replacement"
                assert stat.S_IMODE(target.stat().st_mode) == stat.S_IREAD
            assert list(tmp_path.iterdir()) == [target]
        finally:
            target.chmod(stat.S_IREAD | stat.S_IWRITE)

    def test_success_does_not_delete_a_reused_temporary_name(self, tmp_path, monkeypatch):
        target = tmp_path / "page"
        original_replace = os.replace
        reused = []

        def replace(source, destination):
            original_replace(source, destination)
            source.write_bytes(b"unrelated after publication")
            reused.append(source)

        monkeypatch.setattr(_io.os, "replace", replace)
        atomic_write_text(target, "replacement")
        assert target.read_text() == "replacement"
        assert reused[0].read_bytes() == b"unrelated after publication"

    def test_exclusive_creation_rejects_even_a_unique_name_collision(self, tmp_path, monkeypatch):
        target = tmp_path / "page"
        outside = tmp_path / "outside"
        outside.write_bytes(b"sentinel")
        collision = tmp_path / ".page-planted.tmp"
        collision.symlink_to(outside)
        names = iter(["planted", "ours"])
        monkeypatch.setattr(_io.uuid, "uuid4", lambda: SimpleNamespace(hex=next(names)))
        atomic_write_text(target, "replacement")
        assert target.read_text() == "replacement" and not target.is_symlink()
        assert outside.read_bytes() == b"sentinel" and collision.is_symlink()
        assert set(tmp_path.iterdir()) == {target, outside, collision}

    def test_fdopen_failure_closes_descriptor_and_cleans_temp(self, tmp_path, monkeypatch):
        target = tmp_path / "page"
        target.write_bytes(b"original")
        failure = LookupError("invalid encoding")
        descriptors = []

        def fail(fd, *args, **kwargs):
            descriptors.append(fd)
            raise failure

        monkeypatch.setattr(_io.os, "fdopen", fail)
        with pytest.raises(LookupError) as caught:
            atomic_write_text(target, "replacement")
        assert caught.value is failure
        with pytest.raises(OSError):
            os.fstat(descriptors[0])
        assert target.read_bytes() == b"original" and list(tmp_path.iterdir()) == [target]

    def test_permission_copy_failure_preserves_target(self, tmp_path, monkeypatch):
        target = tmp_path / "page"
        target.write_bytes(b"original")
        failure = PermissionError("cannot copy mode")

        def fail(*args):
            raise failure

        monkeypatch.setattr(_io.os, "chmod", fail)
        with pytest.raises(PermissionError) as caught:
            atomic_write_text(target, "replacement")
        assert caught.value is failure
        assert target.read_bytes() == b"original" and list(tmp_path.iterdir()) == [target]

    def test_read_only_permission_replace_failure_cleanup(self, tmp_path, monkeypatch):
        target = tmp_path / "page"
        target.write_bytes(b"original")
        target.chmod(stat.S_IREAD)
        failure = OSError("replace failed after permission copy")

        def fail(*args):
            raise failure

        monkeypatch.setattr(_io.os, "replace", fail)
        try:
            with pytest.raises(OSError) as caught:
                atomic_write_text(target, "replacement")
            assert caught.value is failure
            assert target.read_bytes() == b"original" and list(tmp_path.iterdir()) == [target]
        finally:
            target.chmod(stat.S_IREAD | stat.S_IWRITE)

    @pytest.mark.parametrize("name", ["cleave.md", ".gen_hashes.json", "log.md"])
    def test_planted_temporary_symlink_is_untouched(self, tmp_path, name):
        outside = tmp_path / "sentinel"
        outside.write_bytes(b"outside original")
        target = tmp_path / "wiki" / name
        target.parent.mkdir()
        target.write_bytes(b"target original")
        planted = target.with_name(target.name + ".tmp")
        planted.symlink_to(outside)
        atomic_write_text(target, "replacement 中文\n", newline="\n")
        assert outside.read_bytes() == b"outside original"
        assert planted.is_symlink() and planted.resolve() == outside
        assert not target.is_symlink() and stat.S_ISREG(target.stat().st_mode)
        assert target.read_bytes() == "replacement 中文\n".encode()
        assert set(target.parent.iterdir()) == {target, planted}

    @pytest.mark.parametrize("newline", [None, "\n"])
    @pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
    def test_encoding_and_newline_bytes_match_normal_open(self, tmp_path, newline, encoding):
        expected = tmp_path / "expected"
        text = "中文 α\nsecond\r\nlast\n"
        with open(str(expected), "w", encoding=encoding, newline=newline) as stream:
            stream.write(text)
        target = tmp_path / "actual"
        atomic_write_text(target, text, encoding=encoding, newline=newline)
        assert target.read_bytes() == expected.read_bytes()

    @pytest.mark.parametrize("failure", [OSError("replace failed"), KeyboardInterrupt("cancelled")])
    def test_replace_failure_preserves_target_and_cleans_only_owned_temp(self, tmp_path, monkeypatch, failure):
        target = tmp_path / "page"
        target.write_bytes(b"original")
        planted = tmp_path / "page.tmp"
        planted.write_bytes(b"unrelated")
        observed = []

        def fail(source, destination):
            source = type(target)(source)
            assert destination == target
            assert source.parent == target.parent and source != planted
            assert not source.is_symlink()
            # Windows can rename it only after the text handle has closed.
            moved = source.with_suffix(".closed")
            os.rename(source, moved)
            os.rename(moved, source)
            observed.append(source)
            raise failure

        monkeypatch.setattr(_io.os, "replace", fail)
        with pytest.raises(type(failure)) as caught:
            atomic_write_text(target, "replacement")
        assert caught.value is failure
        assert target.read_bytes() == b"original" and planted.read_bytes() == b"unrelated"
        assert observed and not observed[0].exists()
        assert set(tmp_path.iterdir()) == {target, planted}

    @pytest.mark.parametrize("failure", [OSError("write failed"), KeyboardInterrupt("write cancelled")])
    @pytest.mark.parametrize("close_failure", [False, True])
    def test_partial_write_failure_cleanup(self, tmp_path, monkeypatch, failure, close_failure):
        target = tmp_path / "page"
        target.write_bytes(b"original")
        planted = tmp_path / "page.tmp"
        planted.write_bytes(b"unrelated")
        original = os.fdopen

        class FailedWriter:
            def __init__(self, stream):
                self.stream = stream

            def close(self):
                self.stream.close()
                if close_failure:
                    raise OSError("secondary close failure")

            def write(self, text):
                self.stream.write("partial")
                self.stream.flush()
                raise failure

        monkeypatch.setattr(_io.os, "fdopen", lambda *a, **kw: FailedWriter(original(*a, **kw)))
        with pytest.raises(type(failure)) as caught:
            atomic_write_text(target, "replacement")
        assert caught.value is failure
        assert target.read_bytes() == b"original" and planted.read_bytes() == b"unrelated"
        assert set(tmp_path.iterdir()) == {target, planted}

    def test_encoding_failure_preserves_target(self, tmp_path):
        target = tmp_path / "page"
        target.write_bytes(b"original")
        with pytest.raises(UnicodeEncodeError):
            atomic_write_text(target, "中文", encoding="ascii")
        assert target.read_bytes() == b"original"
        assert list(tmp_path.iterdir()) == [target]

    def test_existing_permissions_preserved(self, tmp_path):
        target = tmp_path / "page"
        target.write_bytes(b"original")
        target.chmod(0o640 if os.name == "posix" else stat.S_IREAD | stat.S_IWRITE)
        before = stat.S_IMODE(target.stat().st_mode)
        atomic_write_text(target, "replacement")
        assert stat.S_IMODE(target.stat().st_mode) == before

    def test_creates_parent_and_writes(self, tmp_path):
        p = tmp_path / "sub" / "f.txt"
        atomic_write_text(p, "第一版")
        assert p.read_text(encoding="utf-8") == "第一版"

    def test_replaces_existing(self, tmp_path):
        p = tmp_path / "f.txt"
        atomic_write_text(p, "第一版")
        atomic_write_text(p, "第二版")
        assert p.read_text(encoding="utf-8") == "第二版"

    def test_no_tmp_leftover(self, tmp_path):
        atomic_write_text(tmp_path / "f.txt", "内容")
        assert list(tmp_path.rglob("*.tmp")) == []


class TestGenHashes:
    def test_roundtrip(self, tmp_path):
        h = text_sha256("页面内容")
        save_gen_hashes(tmp_path, {"factions/x/units/a.md": h})
        assert load_gen_hashes(tmp_path) == {"factions/x/units/a.md": h}

    def test_missing_returns_empty(self, tmp_path):
        assert load_gen_hashes(tmp_path) == {}

    # ⚠️ 这两条从前断言「损坏 → 返回空表」，那是把一个错误的降级方向钉成了规格
    # （审查 R2-M7）：空表会让调用链走到 `registered is None` ⇒ **无条件覆盖**，
    # 于是「检测到人工编辑就跳过覆盖」这道保护在登记表损坏时不是变严而是整个消失，
    # 且 CLI 照常打印一切正常。安全方向是「宁可不写」，所以现在必须抛。
    def test_corrupt_raises_instead_of_silently_disabling_protection(self, tmp_path):
        (tmp_path / GEN_HASHES_NAME).write_text("{损坏的JSON", encoding="utf-8")
        with pytest.raises(GenHashesCorrupt):
            load_gen_hashes(tmp_path)

    def test_non_dict_raises(self, tmp_path):
        (tmp_path / GEN_HASHES_NAME).write_text("[1, 2]", encoding="utf-8")
        with pytest.raises(GenHashesCorrupt):
            load_gen_hashes(tmp_path)

    def test_missing_file_still_returns_empty(self, tmp_path):
        """成对负向：**文件不存在**是首次生成的正常情形，仍返回空表、不许抛。"""
        assert load_gen_hashes(tmp_path) == {}

    def test_non_string_values_dropped(self, tmp_path):
        (tmp_path / GEN_HASHES_NAME).write_text(
            '{"a.md": "abc", "b.md": 123}', encoding="utf-8")
        assert load_gen_hashes(tmp_path) == {"a.md": "abc"}
