"""wiki_engine/_io.py 测试：原子写与生成内容哈希登记表。"""
from __future__ import annotations

import pytest

from wiki_engine._io import (
    GEN_HASHES_NAME,
    GenHashesCorrupt,
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
