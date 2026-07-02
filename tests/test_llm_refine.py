from pathlib import Path

from llm_refine import extract_pages


def test_extract_pages_returns_text_and_hash(tiny_pdf):
    pages = extract_pages(tiny_pdf)
    assert [p["page"] for p in pages] == [1, 2]
    assert "UNIT ALPHA" in pages[0]["text"]
    assert "WEAPON TABLE" in pages[1]["text"]
    assert len(pages[0]["sha256"]) == 64
    assert pages[0]["sha256"] != pages[1]["sha256"]
