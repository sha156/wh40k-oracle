"""中英配对测试：精确匹配 → 阵营推断 → 阵营内模糊匹配。"""
from wiki_compile.canonical import CanonicalEntry
from wiki_compile.extract import EntityCandidate
from wiki_compile.pair import Pair, PairingResult, normalize_name, pair_entities

CANONICAL = [
    CanonicalEntry("1", "Fire Warriors", "TAU"),
    CanonicalEntry("2", "Commander Farsight", "TAU"),
    CanonicalEntry("3", "Ta'unar Supremacy Armour", "TAU"),
    CanonicalEntry("4", "Hormagaunts", "TYR"),
]


def _cand(zh, en, book="钛书"):
    return EntityCandidate(book=book, raw_heading=(zh or "") + " " + (en or ""),
                           name_zh=zh, name_en=en, pages=[1])


class TestNormalize:
    def test_case_and_typographic_apostrophe(self):
        # 弯引号（PDF提取常见）与直引号归一
        assert normalize_name("TA\u2019UNAR SUPREMACY ARMOUR") == \
               normalize_name("Ta'unar Supremacy Armour")

    def test_extra_spaces_collapsed(self):
        assert normalize_name("FIRE  WARRIORS ") == "FIRE WARRIORS"


class TestPairEntities:
    def test_exact_match(self):
        r = pair_entities([_cand("火战士队", "FIRE WARRIORS")], CANONICAL)
        p = r.pairs[0]
        assert (p.zh, p.en, p.canonical_id, p.confidence) == (
            "火战士队", "Fire Warriors", "1", "exact")
        assert r.unmatched == []

    def test_fuzzy_restricted_to_book_faction(self):
        # 同书先有精确命中 TAU → 推断书=TAU → 模糊匹配只在 TAU 内找
        ents = [_cand("火战士队", "FIRE WARRIORS"),
                _cand("风暴烈阳指挥官", "COMANDER FARSIGHT")]  # 拼写缺字母 → 走模糊匹配
        r = pair_entities(ents, CANONICAL)
        confs = {p.en: p.confidence for p in r.pairs}
        assert confs["Commander Farsight"] == "fuzzy"

    def test_no_english_name_goes_unmatched(self):
        r = pair_entities([_cand("某中文条目", None)], CANONICAL)
        assert r.pairs == []
        assert r.unmatched[0].name_zh == "某中文条目"

    def test_no_close_match_goes_unmatched(self):
        r = pair_entities([_cand("完全无关", "TOTALLY UNRELATED THING")], CANONICAL)
        assert r.unmatched != []


class TestSameNameCanonicalDisambiguation:
    """H13：canonical 中跨阵营同名条目不得 last-write-wins 静默覆盖。"""

    CANON = [
        CanonicalEntry("t-wb", "Warboss", "TAU"),
        CanonicalEntry("o-wb", "Warboss", "ORK"),
        CanonicalEntry("t-fw", "Fire Warriors", "TAU"),
    ]

    def test_prefers_candidate_matching_book_faction(self):
        # 同书先有 TAU 精确锚点 → 同名多候选按本书阵营选 TAU 那条
        ents = [_cand("火战士队", "FIRE WARRIORS"), _cand("同名单位", "WARBOSS")]
        r = pair_entities(ents, self.CANON)
        wb = [p for p in r.pairs if p.en == "Warboss"]
        assert len(wb) == 1
        assert (wb[0].canonical_id, wb[0].faction_id) == ("t-wb", "TAU")
        assert r.unmatched == []

    def test_unresolvable_warns_and_goes_review_needed(self, capsys):
        # 本书无阵营锚点 → 无法消歧 → 警告 + 计入 review_needed，不静默选一条
        r = pair_entities([_cand("同名单位", "WARBOSS")], [
            CanonicalEntry("t-wb", "Warboss", "TAU"),
            CanonicalEntry("o-wb", "Warboss", "ORK")])
        assert r.pairs == []
        assert [e.name_zh for e in r.unmatched] == ["同名单位"]
        out = capsys.readouterr().out
        assert "无法" in out and "WARBOSS" in out


import json

from wiki_compile.pair_llm import llm_pair_book


class FakeCompletion:
    def __init__(self, content):
        class _Msg:  # 模拟 openai 响应结构 choices[0].message.content
            pass
        m = _Msg(); m.content = content
        class _Choice: pass
        ch = _Choice(); ch.message = m
        self.choices = [ch]


class FakeClient:
    """记录调用次数；返回固定 JSON。"""
    def __init__(self, mapping):
        self.calls = 0
        self._content = json.dumps(
            {"配对": [{"zh": k, "en": v} for k, v in mapping.items()]},
            ensure_ascii=False)
        class _Completions:
            def __init__(self, outer): self._o = outer
            def create(self, **kw):
                self._o.calls += 1
                return FakeCompletion(self._o._content)
        class _Chat:
            def __init__(self, outer): self.completions = _Completions(outer)
        self.chat = _Chat(self)


class TestLlmPairBook:
    def test_pairs_from_llm_json(self, tmp_path):
        client = FakeClient({"死亡之雨战机": "Sun Shark Bomber"})
        pairs = llm_pair_book(
            "钛书", [_cand("死亡之雨战机", None)],
            [CanonicalEntry("9", "Sun Shark Bomber", "TAU")],
            cache_dir=tmp_path, client=client)
        assert pairs[0].en == "Sun Shark Bomber"
        assert pairs[0].confidence == "llm"

    def test_null_answer_skipped(self, tmp_path):
        client = FakeClient({"神秘单位": None})
        pairs = llm_pair_book("钛书", [_cand("神秘单位", None)],
                              [CanonicalEntry("9", "Sun Shark Bomber", "TAU")],
                              cache_dir=tmp_path, client=client)
        assert pairs == []

    def test_cache_hit_skips_second_call(self, tmp_path):
        client = FakeClient({"死亡之雨战机": "Sun Shark Bomber"})
        args = ("钛书", [_cand("死亡之雨战机", None)],
                [CanonicalEntry("9", "Sun Shark Bomber", "TAU")])
        llm_pair_book(*args, cache_dir=tmp_path, client=client)
        llm_pair_book(*args, cache_dir=tmp_path, client=client)
        assert client.calls == 1


class FakeBadClient:
    """返回非法 JSON 内容，验证响应容错。"""
    def __init__(self, content="这不是JSON{损坏"):
        self.calls = 0
        _self = self

        class _Completions:
            def create(self, **kw):
                _self.calls += 1
                return FakeCompletion(content)

        class _Chat:
            def __init__(self): self.completions = _Completions()
        self.chat = _Chat()


class TestLlmPairRobustness:
    def test_malformed_json_returns_empty_and_no_cache(self, tmp_path):
        client = FakeBadClient()
        pairs = llm_pair_book(
            "钛书", [_cand("死亡之雨战机", None)],
            [CanonicalEntry("9", "Sun Shark Bomber", "TAU")],
            cache_dir=tmp_path, client=client)
        assert pairs == []
        assert client.calls == 1
        # 坏响应绝不落缓存
        assert list(tmp_path.glob("*.json")) == []

    def test_duplicate_name_zh_no_entity_lost(self, tmp_path):
        # 同名 name_zh、不同页码的两个实体：配对后两者都应存活，不被折叠丢失
        e1 = EntityCandidate(book="钛书", raw_heading="死亡之雨战机",
                             name_zh="死亡之雨战机", name_en=None, pages=[1])
        e2 = EntityCandidate(book="钛书", raw_heading="死亡之雨战机",
                             name_zh="死亡之雨战机", name_en=None, pages=[7])
        client = FakeClient({"死亡之雨战机": "Sun Shark Bomber"})
        pairs = llm_pair_book(
            "钛书", [e1, e2],
            [CanonicalEntry("9", "Sun Shark Bomber", "TAU")],
            cache_dir=tmp_path, client=client)
        assert len(pairs) == 2
        assert {tuple(p.pages) for p in pairs} == {(1,), (7,)}
        assert all(p.en == "Sun Shark Bomber" for p in pairs)


class FlakyClient:
    """前 fail_times 次调用抛异常，之后返回固定 JSON（模拟限流/网络抖动）。"""
    def __init__(self, mapping, fail_times=1):
        self.calls = 0
        content = json.dumps(
            {"配对": [{"zh": k, "en": v} for k, v in mapping.items()]},
            ensure_ascii=False)
        _self = self

        class _Completions:
            def create(self, **kw):
                _self.calls += 1
                if _self.calls <= fail_times:
                    raise RuntimeError("模拟限流")
                return FakeCompletion(content)

        class _Chat:
            def __init__(self): self.completions = _Completions()
        self.chat = _Chat()


class TestLlmRetry:
    """H12：LLM 裸调加重试（最多 3 次、指数退避）。"""

    def test_retry_after_transient_failure(self, tmp_path, monkeypatch):
        import wiki_compile.pair_llm as pl
        monkeypatch.setattr(pl.time, "sleep", lambda s: None)  # 免等退避
        client = FlakyClient({"死亡之雨战机": "Sun Shark Bomber"}, fail_times=1)
        pairs = llm_pair_book(
            "钛书", [_cand("死亡之雨战机", None)],
            [CanonicalEntry("9", "Sun Shark Bomber", "TAU")],
            cache_dir=tmp_path, client=client)
        assert client.calls == 2          # 第一次失败 + 第二次成功
        assert pairs[0].en == "Sun Shark Bomber"

    def test_exhausted_retries_raise(self, tmp_path, monkeypatch):
        import pytest
        import wiki_compile.pair_llm as pl
        monkeypatch.setattr(pl.time, "sleep", lambda s: None)
        client = FlakyClient({}, fail_times=99)
        with pytest.raises(RuntimeError):
            llm_pair_book(
                "钛书", [_cand("死亡之雨战机", None)],
                [CanonicalEntry("9", "Sun Shark Bomber", "TAU")],
                cache_dir=tmp_path, client=client)
        assert client.calls == pl.MAX_RETRIES  # 恰好重试 3 次后放弃
        # 失败绝不落缓存
        assert list(tmp_path.glob("*.json")) == []


class TestRunLlmFallbackIsolation:
    """H12：单书 LLM 彻底失败时隔离该书，其他书不受影响。"""

    def test_failed_book_does_not_break_others(self, tmp_path, monkeypatch, capsys):
        import openai
        import wiki_compile.pair_llm as pl
        from wiki_compile.pair import Pair, PairingResult
        from wiki_compile.pair_llm import run_llm_fallback

        monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key")
        monkeypatch.setenv("HTTPS_PROXY", "")   # 不构造代理 http_client
        monkeypatch.setattr(pl.time, "sleep", lambda s: None)

        ok_content = json.dumps(
            {"配对": [{"zh": "残B", "en": "Beta Unit"}]}, ensure_ascii=False)
        calls = {"A": 0, "B": 0}

        class _Completions:
            def create(self, **kw):
                prompt = kw["messages"][0]["content"]
                if "书A" in prompt:
                    calls["A"] += 1
                    raise RuntimeError("持续失败")
                calls["B"] += 1
                return FakeCompletion(ok_content)

        class _Chat:
            def __init__(self): self.completions = _Completions()

        class FakeOpenAI:
            def __init__(self, **kw): self.chat = _Chat()

        monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)

        anchor_a = Pair(zh="锚A", en="Anchor A", canonical_id="a0",
                        faction_id="TAU", book="书A", pages=[1], confidence="exact")
        anchor_b = Pair(zh="锚B", en="Anchor B", canonical_id="b0",
                        faction_id="ORK", book="书B", pages=[1], confidence="exact")
        canonical = [CanonicalEntry("a1", "Alpha Unit", "TAU"),
                     CanonicalEntry("b1", "Beta Unit", "ORK")]
        result = PairingResult(
            pairs=[anchor_a, anchor_b],
            unmatched=[_cand("残A", None, book="书A"),
                       _cand("残B", None, book="书B")])
        out = run_llm_fallback(result, canonical, tmp_path)

        assert calls["A"] == pl.MAX_RETRIES   # 书A 重试耗尽后放弃
        # 书B 不受影响，正常配对
        assert any(p.zh == "残B" and p.en == "Beta Unit" for p in out.pairs)
        # 书A 条目留在未匹配集合
        unmatched_zh = {e.name_zh for e in out.unmatched}
        assert "残A" in unmatched_zh and "残B" not in unmatched_zh
        assert "书A" in capsys.readouterr().out  # 打了单书失败警告


class TestRunLlmFallback:
    def test_no_api_key_returns_unchanged(self, tmp_path, monkeypatch):
        from wiki_compile.pair import Pair, PairingResult
        from wiki_compile.pair_llm import run_llm_fallback

        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        paired = Pair(zh="火战士队", en="Fire Warriors", canonical_id="1",
                      faction_id="TAU", book="钛书", pages=[1], confidence="exact")
        leftover = _cand("神秘单位", None)
        result = PairingResult(pairs=[paired], unmatched=[leftover])
        out = run_llm_fallback(result, CANONICAL, tmp_path)
        # 无 key：原样返回，不触网、不动内容
        assert out.pairs == [paired]
        assert out.unmatched == [leftover]

    def test_client_uses_proxy_from_env(self, tmp_path, monkeypatch):
        # 验证客户端构造读取 HTTPS_PROXY（默认回退 Clash 端口），不发真实网络请求：
        # 用假 OpenAI/httpx.Client 记录构造参数，且残余条目无阵营锚点，
        # 不会走到 llm_pair_book 的真实 create() 调用。
        import httpx
        import openai

        from wiki_compile.pair_llm import run_llm_fallback

        monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key")
        monkeypatch.setenv("HTTPS_PROXY", "http://proxy.example:1234")

        captured = {}

        class FakeHttpxClient:
            def __init__(self, proxy=None):
                captured["proxy"] = proxy

        class FakeOpenAI:
            def __init__(self, **kwargs):
                captured["kwargs"] = kwargs

        monkeypatch.setattr(httpx, "Client", FakeHttpxClient)
        monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)

        leftover = _cand("神秘单位", None)  # book 无精确命中票 → fid 为 None，不会调用 LLM
        result = PairingResult(pairs=[], unmatched=[leftover])
        out = run_llm_fallback(result, CANONICAL, tmp_path)

        assert captured["proxy"] == "http://proxy.example:1234"
        assert captured["kwargs"]["http_client"] is not None
        assert out.unmatched == [leftover]

    def test_client_no_proxy_when_env_blank(self, tmp_path, monkeypatch):
        # 显式设为空字符串 → 不传 http_client，走直连
        import openai

        from wiki_compile.pair_llm import run_llm_fallback

        monkeypatch.setenv("DEEPSEEK_API_KEY", "fake-key")
        monkeypatch.setenv("HTTPS_PROXY", "")

        captured = {}

        class FakeOpenAI:
            def __init__(self, **kwargs):
                captured["kwargs"] = kwargs

        monkeypatch.setattr(openai, "OpenAI", FakeOpenAI)

        leftover = _cand("神秘单位", None)
        result = PairingResult(pairs=[], unmatched=[leftover])
        run_llm_fallback(result, CANONICAL, tmp_path)

        assert "http_client" not in captured["kwargs"]
