"""wiki_engine/_io.py 测试：原子写与生成内容哈希登记表。"""
from __future__ import annotations

from wiki_engine._io import (
    GEN_HASHES_NAME,
    atomic_write_text,
    load_gen_hashes,
    save_gen_hashes,
    text_sha256,
)


class TestAtomicWriteText:
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

    def test_corrupt_returns_empty(self, tmp_path):
        (tmp_path / GEN_HASHES_NAME).write_text("{损坏的JSON", encoding="utf-8")
        assert load_gen_hashes(tmp_path) == {}

    def test_non_dict_returns_empty(self, tmp_path):
        (tmp_path / GEN_HASHES_NAME).write_text("[1, 2]", encoding="utf-8")
        assert load_gen_hashes(tmp_path) == {}

    def test_non_string_values_dropped(self, tmp_path):
        (tmp_path / GEN_HASHES_NAME).write_text(
            '{"a.md": "abc", "b.md": 123}', encoding="utf-8")
        assert load_gen_hashes(tmp_path) == {"a.md": "abc"}
