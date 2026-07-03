from pathlib import Path

from llm_refine import extract_pages, is_cached, page_paths, save_page


def test_extract_pages_returns_text_and_hash(tiny_pdf):
    pages = extract_pages(tiny_pdf)
    assert [p["page"] for p in pages] == [1, 2]
    assert "UNIT ALPHA" in pages[0]["text"]
    assert "WEAPON TABLE" in pages[1]["text"]
    assert len(pages[0]["sha256"]) == 64
    assert pages[0]["sha256"] != pages[1]["sha256"]


def _meta(sha, ver="v1", fallback=False):
    return {"sha256": sha, "prompt_version": ver, "model": "deepseek-chat",
            "verify_ok": True, "fallback": fallback}


def test_cache_roundtrip(tmp_path):
    save_page(tmp_path, 3, "## 单位A\n内容", _meta("abc"))
    md_path, meta_path = page_paths(tmp_path, 3)
    assert md_path.name == "page_003.md"
    assert meta_path.name == "page_003.meta.json"
    assert md_path.read_text(encoding="utf-8") == "## 单位A\n内容"
    assert is_cached(tmp_path, 3, "abc", "v1")


def test_cache_invalidated_by_sha_or_prompt_or_fallback(tmp_path):
    save_page(tmp_path, 1, "x", _meta("abc"))
    assert not is_cached(tmp_path, 1, "CHANGED", "v1")   # 页内容变了
    assert not is_cached(tmp_path, 1, "abc", "v2")       # prompt 升级了
    save_page(tmp_path, 2, "raw", _meta("abc", fallback=True))
    assert not is_cached(tmp_path, 2, "abc", "v1")       # 兜底页需重试
    assert not is_cached(tmp_path, 9, "abc", "v1")       # 不存在
