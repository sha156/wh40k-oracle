"""archive_old_pdfs.py 测试：版本分组、归档选择。"""
from __future__ import annotations

import pytest
from pathlib import Path

# 将 archive_old_pdfs 函数导入（虽是独立脚本，但可直接 import）
from archive_old_pdfs import (
    _detect_faction_key,
    _parse_version_date,
    _has_chinese,
    _has_faction_pack_name,
    detect_version_groups,
    select_archive_targets,
)


class TestDetectFactionKey:
    def test_english_faction_pack(self):
        assert _detect_faction_key("Faction Pack Tau Empire") == "tau-empire"

    def test_chinese_faction_name(self):
        assert _detect_faction_key("星际战士10版中文老湿腐版1.41") == "space-marines"

    def test_core_rules_en(self):
        assert _detect_faction_key("Core Rules - New 40K Core Rules") == "core-rules"

    def test_unknown_returns_none(self):
        assert _detect_faction_key("xyz_random_file") is None


class TestParseVersionDate:
    def test_full_date(self):
        assert _parse_version_date("钛帝国十版CODEX-20251112") == (2025, 11, 12)

    def test_v_prefix(self):
        assert _parse_version_date("黑色圣堂CODEX-双子星版 V1.20") == (1, 20)

    def test_minor_version(self):
        assert _parse_version_date("艾达灵族10版中文 1.13") > (1, 2)

    def test_no_version(self):
        assert _parse_version_date("帝国骑士中文") == (0,)


class TestLanguageDetection:
    def test_chinese_stem(self):
        assert _has_chinese("星际战士中文版") is True

    def test_english_stem(self):
        assert _has_chinese("Faction Pack Space Marines") is False

    def test_faction_pack_detection(self):
        assert _has_faction_pack_name("Faction Pack Tau Empire") is True
        assert _has_faction_pack_name("星际战士中文版") is False


class TestDetectVersionGroups:
    def test_groups_by_faction(self, tmp_path):
        data = tmp_path / "data"
        data.mkdir()
        (data / "Faction Pack Tau Empire.pdf").write_text("en")
        (data / "钛帝国十版CODEX-20251112.pdf").write_text("zh new")
        (data / "钛帝国十版CODEX-20250115.pdf").write_text("zh old")

        groups = detect_version_groups(data)
        # Tau-related should be grouped under tau-empire
        tau_key = None
        for key in groups:
            if "tau" in key:
                tau_key = key
                break
        assert tau_key is not None
        assert len(groups[tau_key]) == 3

    def test_single_pdf_no_archive(self, tmp_path):
        data = tmp_path / "data"
        data.mkdir()
        (data / "unique_book.pdf").write_text("content")

        groups = detect_version_groups(data)
        targets = select_archive_targets(groups)
        assert len(targets) == 0  # 只有一本，不需要归档


class TestEmptyDataDir:
    """MEDIUM #7：空 data/ 目录不得裸抛 StopIteration。"""

    def test_empty_groups_returns_empty(self):
        assert select_archive_targets({}) == []

    def test_empty_dir_archive_run(self, tmp_path):
        from archive_old_pdfs import archive_old_versions
        data = tmp_path / "data"
        data.mkdir()
        moved = archive_old_versions(data, data / "archive", dry_run=False)
        assert moved == []


class TestDestinationExists:
    """MEDIUM #9：archive/ 下同名文件已存在时跳过并警告，不抛 FileExistsError。"""

    def test_existing_dst_skipped(self, tmp_path):
        from archive_old_pdfs import archive_old_versions
        data = tmp_path / "data"
        data.mkdir()
        archive = data / "archive"
        archive.mkdir()

        new = data / "钛帝国十版CODEX-20251112.pdf"
        old = data / "钛帝国十版CODEX-20250115.pdf"
        new.write_text("new")
        old.write_text("old")
        # 归档目标已存在同名文件
        (archive / "钛帝国十版CODEX-20250115.pdf").write_text("pre-existing")

        moved = archive_old_versions(data, archive, dry_run=False)
        # 不抛异常；源文件保留原地；未计入已移动列表
        assert old.exists()
        assert "钛帝国十版CODEX-20250115.pdf" not in moved
        # 预存文件内容未被覆盖
        assert (archive / "钛帝国十版CODEX-20250115.pdf").read_text() == "pre-existing"


class TestSelectArchiveTargets:
    def test_keep_newest_chinese(self, tmp_path):
        data = tmp_path / "data"
        data.mkdir()
        archive_dir = data / "archive"
        archive_dir.mkdir()

        new = data / "钛帝国十版CODEX-20251112.pdf"
        old = data / "钛帝国十版CODEX-20250115.pdf"
        new.write_text("new")
        old.write_text("old")

        groups = detect_version_groups(data)
        targets = select_archive_targets(groups)

        # old version should be archived
        archived_names = [t[0].name for t in targets]
        assert "钛帝国十版CODEX-20250115.pdf" in archived_names
        assert "钛帝国十版CODEX-20251112.pdf" not in archived_names
