from pathlib import Path

from md_chunker import chunk_markdown, load_refined_book

BASE = {"source": "data/x.pdf", "book": "测试书"}


def test_splits_by_h2_and_tracks_unit_and_page():
    pages = [
        (1, "## 单位A\n| M | T |\n| 6 | 4 |"),
        (2, "## 单位B\n内容B"),
    ]
    chunks = chunk_markdown(pages, BASE)
    assert len(chunks) == 2
    assert chunks[0].metadata["unit"] == "单位A"
    assert chunks[0].metadata["page"] == 1
    assert chunks[1].metadata["unit"] == "单位B"
    assert chunks[1].metadata["page"] == 2
    assert chunks[0].metadata["book"] == "测试书"
    assert "| 6 | 4 |" in chunks[0].page_content


def test_cross_page_entry_merges_and_cont_marker_stripped():
    pages = [
        (1, "## 单位A\n第一页内容"),
        (2, "<!--CONT-->\n第二页延续内容"),
    ]
    chunks = chunk_markdown(pages, BASE)
    assert len(chunks) == 1
    assert "第一页内容" in chunks[0].page_content
    assert "第二页延续内容" in chunks[0].page_content
    assert "<!--CONT-->" not in chunks[0].page_content


def test_preamble_before_first_h2_becomes_own_chunk():
    pages = [(1, "# 书名\n前言文字"), (1, "## 单位A\n内容")]
    chunks = chunk_markdown(pages, BASE)
    assert len(chunks) == 2
    assert chunks[0].metadata["unit"] == "书名"
    assert "前言文字" in chunks[0].page_content


def test_oversize_entry_splits_at_h3_and_repeats_heading():
    body = "## 大单位\n| M |\n### 远程武器\n" + ("x" * 1500) \
           + "\n### 技能\n" + ("y" * 1500)
    chunks = chunk_markdown([(1, body)], BASE, max_chunk_chars=1000)
    assert len(chunks) >= 2
    assert all(c.metadata["unit"] == "大单位" for c in chunks)
    assert chunks[0].page_content.startswith("## 大单位")
    assert chunks[1].page_content.startswith("## 大单位（续）")


def test_load_refined_book_reads_pages_in_order(tmp_path):
    book_dir = tmp_path / "mybook"
    book_dir.mkdir()
    (book_dir / "page_001.md").write_text("## 单位A\n甲", encoding="utf-8")
    (book_dir / "page_002.md").write_text("## 单位B\n乙", encoding="utf-8")
    chunks = load_refined_book(Path("data/mybook.pdf"), tmp_path, BASE)
    assert [c.metadata["unit"] for c in chunks] == ["单位A", "单位B"]
    assert [c.metadata["page"] for c in chunks] == [1, 2]


def test_load_refined_book_returns_none_when_missing(tmp_path):
    assert load_refined_book(Path("data/nothere.pdf"), tmp_path, BASE) is None
