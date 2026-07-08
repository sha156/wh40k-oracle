# tests/test_db_compile_downloads.py
"""downloads：官方下载页版本监控的纯逻辑（文件名 diff / 汇总）——离线，不触网/不渲染。

渲染（scrapling→3.11）与 HEAD 走网络的部分不在单测覆盖，靠集成运行验证；
本文件锁死「版本信号 = 文件名哈希」的 diff 判定，这是监控能否报对改版的核心。
"""
from db_compile.downloads import (DocEntry, _filename_of, diff_category,
                                  summarize)


def test_filename_of_strips_path_and_query():
    assert _filename_of("https://x/eng_core-abc123.pdf") == "eng_core-abc123.pdf"
    assert _filename_of("https://x/a/b/f.pdf?v=2") == "f.pdf"


def test_diff_detects_added_changed_removed_unchanged():
    old = {
        "Core Rules": {"filename": "core-OLD.pdf"},
        "Orks": {"filename": "orks-v1.pdf"},
        "Legends": {"filename": "legends.pdf"},
    }
    new = [
        DocEntry("Core Rules", "core-NEW.pdf", "u"),     # 文件名变→改版
        DocEntry("Orks", "orks-v1.pdf", "u"),            # 文件名同→未变
        DocEntry("Tyranids", "tyra-new.pdf", "u"),       # 旧无→新增
    ]                                                    # Legends 新无→下架
    d = diff_category("warhammer-40000", old, new)
    assert [e.title for e in d.added] == ["Tyranids"]
    assert d.changed == [("Core Rules", "core-OLD.pdf", "core-NEW.pdf")]
    assert d.removed == ["Legends"]
    assert d.unchanged == 1
    assert d.has_changes


def test_diff_no_changes_when_identical():
    old = {"Core Rules": {"filename": "core-abc.pdf"}}
    new = [DocEntry("Core Rules", "core-abc.pdf", "u")]
    d = diff_category("warhammer-40000", old, new)
    assert not d.has_changes and d.unchanged == 1


def test_diff_first_run_all_added_against_empty_baseline():
    new = [DocEntry("Core Rules", "core.pdf", "u"),
           DocEntry("Orks", "orks.pdf", "u")]
    d = diff_category("warhammer-40000", {}, new)
    assert len(d.added) == 2 and not d.changed and not d.removed


def test_summarize_counts_across_categories():
    d1 = diff_category("a", {"X": {"filename": "x1"}},
                       [DocEntry("X", "x2", "u"), DocEntry("Y", "y1", "u")])
    d2 = diff_category("b", {"Z": {"filename": "z1"}}, [])
    total = summarize({"diffs": [d1, d2]})
    assert total == {"added": 1, "changed": 1, "removed": 1, "unchanged": 0}
