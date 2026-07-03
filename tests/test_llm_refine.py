import pytest
from pathlib import Path

from llm_refine import extract_pages, is_cached, page_paths, save_page, verify_numbers, refine_page


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
