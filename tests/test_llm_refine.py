import sys

import pytest
from pathlib import Path

from llm_refine import extract_pages, is_cached, page_paths, save_page, verify_numbers, refine_page
from tests.conftest import make_pdf


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


def test_verify_numbers_pass_when_subset():
    src = "箭弹发射器 18 5 2+ 3 0 1"
    md = "| 箭弹发射器 | 18 | 5 | 2+ | 3 | 0 | 1 |"
    assert verify_numbers(src, md) == []


def test_verify_numbers_flags_invented_tokens():
    src = "M 10 T 4"
    md = "| M | T |\n| 10 | 7 |"          # 7 是原文没有的
    assert verify_numbers(src, md) == ["7"]


def test_verify_numbers_flags_excess_count():
    src = "W 5"
    md = "5 5 5"                            # 5 出现次数超过原文
    assert verify_numbers(src, md) == ["5"]


class _FakeChoice:
    def __init__(self, content):
        class _Msg:
            pass
        self.message = _Msg()
        self.message.content = content


class _FakeClient:
    """openai.OpenAI 形状的假客户端：按脚本依次返回/抛错。"""
    def __init__(self, script):
        self._script = list(script)
        self.calls = 0

        class _Completions:
            def create(_self, **kwargs):
                self.calls += 1
                item = self._script.pop(0)
                if isinstance(item, Exception):
                    raise item

                class _Resp:
                    choices = [_FakeChoice(item)]
                return _Resp()

        class _Chat:
            completions = _Completions()

        self.chat = _Chat()


def test_refine_page_returns_content():
    client = _FakeClient(["## 单位A\n| M |"])
    assert refine_page(client, "原文", "") == "## 单位A\n| M |"


def test_refine_page_strips_code_fence():
    client = _FakeClient(["```markdown\n## 单位A\n```"])
    assert refine_page(client, "原文", "") == "## 单位A"


def test_refine_page_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr("llm_refine.time.sleep", lambda s: None)
    client = _FakeClient([RuntimeError("boom"), "## OK"])
    assert refine_page(client, "原文", "") == "## OK"
    assert client.calls == 2


def test_refine_page_raises_after_max_retries(monkeypatch):
    monkeypatch.setattr("llm_refine.time.sleep", lambda s: None)
    client = _FakeClient([RuntimeError("a"), RuntimeError("b"), RuntimeError("c")])
    with pytest.raises(RuntimeError):
        refine_page(client, "原文", "")


import json as _json

import llm_refine
from llm_refine import process_book


def test_process_book_writes_pages_and_summary(tmp_path, tiny_pdf, monkeypatch):
    monkeypatch.setattr(llm_refine, "refine_page",
                        lambda client, text, tail, sp=None: "## E\n" + text.strip())
    summary = process_book(client=None, pdf_path=tiny_pdf, out_root=tmp_path)
    assert summary["total"] == 2
    assert summary["done"] == 2
    assert summary["failed"] == 0
    book_dir = tmp_path / "book"
    assert (book_dir / "page_001.md").exists()
    meta = _json.loads((book_dir / "page_001.meta.json").read_text(encoding="utf-8"))
    assert meta["fallback"] is False and meta["verify_ok"] is True


def test_process_book_uses_cache_on_second_run(tmp_path, tiny_pdf, monkeypatch):
    monkeypatch.setattr(llm_refine, "refine_page",
                        lambda client, text, tail, sp=None: "## E\nok " + text.strip())
    process_book(client=None, pdf_path=tiny_pdf, out_root=tmp_path)
    calls = []
    monkeypatch.setattr(llm_refine, "refine_page",
                        lambda client, text, tail, sp=None: calls.append(1) or "## X")
    summary = process_book(client=None, pdf_path=tiny_pdf, out_root=tmp_path)
    assert summary["cached"] == 2 and calls == []


def test_process_book_fallback_on_llm_failure(tmp_path, tiny_pdf, monkeypatch):
    def boom(client, text, tail, sp=None):
        raise RuntimeError("LLM down")
    monkeypatch.setattr(llm_refine, "refine_page", boom)
    summary = process_book(client=None, pdf_path=tiny_pdf, out_root=tmp_path)
    assert summary["failed"] == 2
    md = (tmp_path / "book" / "page_001.md").read_text(encoding="utf-8")
    assert "UNIT ALPHA" in md            # 兜底写入原始文本
    meta = _json.loads((tmp_path / "book" / "page_001.meta.json")
                       .read_text(encoding="utf-8"))
    assert meta["fallback"] is True


def test_process_book_writes_skipped_pages_json(tmp_path, monkeypatch):
    """第二页文本过短（< MIN_TEXT_CHARS），应计入 skipped 并落盘 skipped_pages.json。"""
    pdf_path = make_pdf(
        tmp_path / "book2.pdf",
        ["UNIT ALPHA M 6 T 4 SV 3+ W 5", "x"],
    )
    monkeypatch.setattr(llm_refine, "refine_page",
                        lambda client, text, tail, sp=None: "## E\n" + text.strip())
    summary = process_book(client=None, pdf_path=pdf_path, out_root=tmp_path)

    assert summary["total"] == 2
    assert summary["skipped"] == 1
    assert summary["done"] == 1

    book_dir = tmp_path / "book2"
    skipped_path = book_dir / "skipped_pages.json"
    assert skipped_path.exists()
    skipped_pages = _json.loads(skipped_path.read_text(encoding="utf-8"))
    assert skipped_pages == [2]
    # 短页不应被当作正常任务处理，不产出 page_002.md
    assert not (book_dir / "page_002.md").exists()


class _StubOpenAIClient:
    """占位客户端：只验证 main() 会用 api_key/base_url 构造它，不发起任何网络请求。"""
    def __init__(self, **kwargs):
        self.kwargs = kwargs


def test_main_exits_1_when_api_key_missing(monkeypatch, tmp_path, capsys):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    # 即便不小心构造了真实客户端也不应发生网络调用；这里额外兜底防御
    monkeypatch.setattr("openai.OpenAI", _StubOpenAIClient)
    monkeypatch.setattr(sys, "argv",
                        ["llm_refine.py", "--all", "--data-dir", str(tmp_path)])

    with pytest.raises(SystemExit) as exc_info:
        llm_refine.main()

    assert exc_info.value.code == 1
    assert "DEEPSEEK_API_KEY" in capsys.readouterr().out


def test_main_exits_1_when_book_substring_matches_nothing(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
    monkeypatch.setattr("openai.OpenAI", _StubOpenAIClient)
    monkeypatch.setattr(sys, "argv",
                        ["llm_refine.py", "--book", "NO_SUCH_BOOK_XYZ",
                         "--data-dir", str(tmp_path)])

    with pytest.raises(SystemExit) as exc_info:
        llm_refine.main()

    assert exc_info.value.code == 1
    assert "NO_SUCH_BOOK_XYZ" in capsys.readouterr().out


# ── --chinese-only 覆盖率过滤 ──

def test_pdf_page_count(tiny_pdf):
    assert llm_refine._pdf_page_count(tiny_pdf) == 2


def test_filter_chinese_pending_skips_fully_refined(tmp_path):
    pdf_done = make_pdf(tmp_path / "钛帝国.pdf", ["page one", "page two"])
    pdf_todo = make_pdf(tmp_path / "吞世者.pdf", ["page one", "page two"])
    out_root = tmp_path / "refined"
    done_dir = out_root / "钛帝国"
    done_dir.mkdir(parents=True)
    (done_dir / "page_001.md").write_text("x", encoding="utf-8")
    (done_dir / "page_002.md").write_text("x", encoding="utf-8")

    kept = llm_refine._filter_chinese_pending(
        [pdf_done, pdf_todo], out_root, min_coverage=0.9)

    assert kept == [pdf_todo]


def test_filter_chinese_pending_keeps_partial(tmp_path):
    pdf = make_pdf(tmp_path / "死亡守卫.pdf", ["p1", "p2", "p3", "p4"])
    out_root = tmp_path / "refined"
    part_dir = out_root / "死亡守卫"
    part_dir.mkdir(parents=True)
    (part_dir / "page_001.md").write_text("x", encoding="utf-8")

    kept = llm_refine._filter_chinese_pending([pdf], out_root, min_coverage=0.9)

    assert kept == [pdf]
