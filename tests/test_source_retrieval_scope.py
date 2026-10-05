"""Synthetic flat FAISS/BM25 regressions; no model, network or active index."""
import copy

import pytest

import corpus_manifest as corpus

pytest.importorskip("streamlit", reason="Full retrieval stack is local-only")
import app
import faiss
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS


HISTORICAL = {"edition": "11", "layer": "rules", "status": "historical",
              "effective_date": "2026-06-20", "scope": "withdrawn full chapter pack"}


def manifest():
    return {"defaults": {"edition": "10", "layer": "codex-base"},
            "prefixes": [{"prefix": "Faction Pack", "edition": "11", "layer": "overlay"}],
            "books": {"Faction Pack Archived": dict(HISTORICAL),
                      "Current Rules": {"edition": "11", "layer": "rules", "status": "current",
                                        "effective_date": "2026-09-30", "scope": "core rules"}}}


class QueryOnlyEmbedding(Embeddings):
    def embed_documents(self, texts):
        raise AssertionError("Stored vectors must not be re-embedded")

    def embed_query(self, text):
        return [0.0]


def store_fixture(historical_count=240, filler_count=300):
    texts, vectors, metadata = [], [], []
    for i in range(historical_count + filler_count):
        texts.append("needle" if i < historical_count else "unrelated filler")
        vectors.append([float(i) / 10000])
        # Stored metadata intentionally predates the exact declaration.
        metadata.append({"book": "Faction Pack Archived", "source": "old.pdf", "page": i + 1,
                         "edition": "11", "layer": "rules"})
    for name, layer, distance in (("Current Rules", "rules", 100.0),
                                   ("Carry Codex", "codex-base", 101.0)):
        texts.append("needle " + "supporting text " * 40)
        vectors.append([distance])
        metadata.append({"book": name, "source": name + ".pdf", "page": 1,
                         "edition": "10", "layer": layer})
    store = FAISS.from_embeddings(list(zip(texts, vectors)), QueryOnlyEmbedding(), metadatas=metadata)
    bm25 = BM25Retriever.from_documents(list(store.docstore._dict.values()), k=2,
                                       preprocess_func=app.chinese_tokenize)
    return store, bm25


@pytest.fixture
def scoped(monkeypatch):
    monkeypatch.setattr(app, "_CORPUS_MANIFEST", manifest())
    monkeypatch.setattr(app, "FAISS_TOP_K", 2)
    monkeypatch.setattr(app, "BM25_TOP_K", 2)
    monkeypatch.setattr(app, "RULES_FLOOR_K", 1)
    monkeypatch.setattr(app, "RERANK_TOP_N", 4)
    return monkeypatch


def test_classification_preserves_reviewed_temporal_fields_and_origin():
    before = manifest()
    tags, origin = corpus.classify_book_with_origin("Faction Pack Archived", before)
    assert origin == "exact"
    assert tags == HISTORICAL
    assert before == manifest()


@pytest.mark.parametrize("field,value", [("status", "retired-ish"), ("status", None),
                                        ("effective_date", "2026-02-30"),
                                        ("effective_date", "20260930"),
                                        ("effective_date", 20260930),
                                        ("scope", []), ("scope", " ")])
def test_invalid_optional_metadata_is_rejected(field, value):
    data = manifest()
    data["books"]["Faction Pack Archived"][field] = value
    with pytest.raises(ValueError):
        corpus.classify_book_with_origin("Faction Pack Archived", data)


@pytest.mark.parametrize("origin", ["prefixes", "defaults"])
def test_historical_exclusions_require_exact_names(origin):
    data = manifest()
    data["books"] = {}
    if origin == "prefixes":
        data["prefixes"] = [{"prefix": "Faction Pack", **HISTORICAL}]
    else:
        data["prefixes"] = []
        data["defaults"] = dict(HISTORICAL)
    with pytest.raises(ValueError, match="exact book"):
        corpus.classify_book_with_origin("Faction Pack Unknown", data)


def test_historical_access_requires_a_date():
    data = manifest()
    data["books"]["Faction Pack Archived"]["effective_date"] = None
    with pytest.raises(ValueError):
        corpus.classify_book("Faction Pack Archived", data)


def test_default_codex_and_prefix_never_infer_retirement():
    assert corpus.classify_book("Carry Codex", manifest()) == {"edition": "10", "layer": "codex-base"}
    assert corpus.classify_book("Faction Pack Other", manifest()) == {"edition": "11", "layer": "overlay"}


def test_exact_current_override_replaces_stale_indexed_history():
    resolver = getattr(corpus, "resolve_book_metadata", None)
    assert callable(resolver), "Validated index/manifest metadata resolver is required"
    meta = {"book": "Current Rules", **HISTORICAL}
    before = copy.deepcopy(meta)
    tags = resolver(meta, manifest())
    assert tags["status"] == "current" and tags["effective_date"] == "2026-09-30"
    assert meta == before


def test_stored_history_is_respected_when_no_exact_override():
    resolver = getattr(corpus, "resolve_book_metadata", None)
    assert callable(resolver)
    assert resolver({"book": "Stored Archive", **HISTORICAL}, manifest())["status"] == "historical"


def test_current_and_carry_forward_scope_do_not_become_full_body_certification():
    data = manifest()
    data["books"]["Carry Codex"] = {"edition": "10", "layer": "codex-base",
                                     "status": "carry_forward", "effective_date": None,
                                     "scope": "codex base with overlay required"}
    assert corpus.classify_book("Carry Codex", data) == data["books"]["Carry Codex"]


def test_default_bm25_build_excludes_historical_before_statistics(scoped):
    store, _ = store_fixture()
    if hasattr(app, "_build_bm25"):
        app._build_bm25.clear()
    retriever = app.build_bm25(store)
    assert {doc.metadata["book"] for doc in retriever.docs} == {"Current Rules", "Carry Codex"}


def test_existing_unscoped_bm25_is_prepared_before_topk(scoped):
    store, bm25 = store_fixture()
    assert all(doc.metadata["book"] == "Faction Pack Archived" for doc in bm25.invoke("needle"))
    scoped.setattr(store, "as_retriever", lambda **kwargs: type("Empty", (), {"invoke": lambda self, q: []})())
    scoped.setattr(store, "similarity_search", lambda *args, **kwargs: [])
    result = app.hybrid_retrieve("needle", store, bm25, None)
    assert {p["book"] for p in result} == {"Current Rules", "Carry Codex"}


def test_faiss_full_pool_prevents_dominant_historical_topk_starvation(scoped):
    store, _ = store_fixture()
    before = bytes(faiss.serialize_index(store.index))
    metadata_before = copy.deepcopy([doc.metadata for doc in store.docstore._dict.values()])
    result = app.hybrid_retrieve("needle", store, None, None)
    assert {p["book"] for p in result} == {"Current Rules", "Carry Codex"}
    assert bytes(faiss.serialize_index(store.index)) == before
    assert [doc.metadata for doc in store.docstore._dict.values()] == metadata_before


def test_rules_floor_uses_same_scope_and_dynamic_complete_pool(scoped):
    store, _ = store_fixture(historical_count=8010, filler_count=0)
    scoped.setattr(store, "as_retriever", lambda **kwargs: type("Empty", (), {"invoke": lambda self, q: []})())
    result = app.hybrid_retrieve("needle", store, None, None)
    assert len(result) == 1 and result[0]["book"] == "Current Rules"
    assert result[0]["edition"] == "11"  # exact override beats stored edition=10


def test_explicit_historical_access_returns_date_scope_and_clear_text_label(scoped):
    store, _ = store_fixture()
    result = app.hybrid_retrieve("needle", store, None, None, filter_books=["Faction Pack Archived"])
    assert result and {p["book"] for p in result} == {"Faction Pack Archived"}
    for passage in result:
        assert passage["status"] == "historical"
        assert passage["effective_date"] == "2026-06-20"
        assert passage["scope"] == HISTORICAL["scope"]
        assert passage["text"].startswith("Historical source; effective 2026-06-20")
        assert "not current rules" in passage["source_note"]
    context = app.format_context(result)
    assert "historical" in context and "2026-06-20" in context and HISTORICAL["scope"] in context


def test_explicit_book_bm25_selection_precedes_ranking(scoped):
    store, bm25 = store_fixture()
    scoped.setattr(store, "as_retriever", lambda **kwargs: type("Empty", (), {"invoke": lambda self, q: []})())
    result = app.hybrid_retrieve("needle", store, bm25, None, filter_books=["Carry Codex"])
    assert result and {p["book"] for p in result} == {"Carry Codex"}


def test_historical_can_be_recovered_from_default_scoped_bm25(scoped):
    store, _ = store_fixture()
    if hasattr(app, "_build_bm25"):
        app._build_bm25.clear()
    bm25 = app.build_bm25(store)
    scoped.setattr(store, "as_retriever", lambda **kwargs: type("Empty", (), {"invoke": lambda self, q: []})())
    result = app.hybrid_retrieve("needle", store, bm25, None, filter_books=["Faction Pack Archived"])
    assert result and result[0]["status"] == "historical"


def test_current_exact_override_remains_available_with_stored_history(scoped):
    store, _ = store_fixture(historical_count=0, filler_count=0)
    current = next(doc for doc in store.docstore._dict.values() if doc.metadata["book"] == "Current Rules")
    current.metadata.update(HISTORICAL)
    result = app.hybrid_retrieve("needle", store, None, None)
    assert any(p["book"] == "Current Rules" and p.get("status") == "current" for p in result)


def test_unknown_explicit_book_does_not_inject_other_rules(scoped):
    store, bm25 = store_fixture()
    assert app.hybrid_retrieve("needle", store, bm25, None, filter_books=["Unknown Book"]) == []


def test_current_date_and_scope_survive_retrieval_context(scoped):
    store, _ = store_fixture(historical_count=0, filler_count=0)
    result = app.hybrid_retrieve("needle", store, None, None)
    current = next(p for p in result if p["book"] == "Current Rules")
    assert current["effective_date"] == "2026-09-30" and current["scope"] == "core rules"
    assert "effective 2026-09-30" in app.format_context([current])


def test_absent_declarations_preserve_legacy_passages(scoped):
    scoped.setattr(app, "_CORPUS_MANIFEST", {"defaults": {"edition": "10", "layer": "codex-base"},
                                           "prefixes": [], "books": {}})
    store, _ = store_fixture(historical_count=0, filler_count=0)
    result = app.hybrid_retrieve("needle", store, None, None)
    assert result and all("status" not in p and "source_note" not in p for p in result)
    assert all(not p["text"].startswith("Historical source") for p in result)


def test_reranker_only_sees_eligible_candidates(scoped):
    store, bm25 = store_fixture()

    class Recorder:
        def rerank(self, request):
            assert all(p["meta"]["book"] != "Faction Pack Archived" for p in request.passages)
            return request.passages

    assert app.hybrid_retrieve("needle", store, bm25, Recorder())


def test_exact_rules_layer_override_applies_before_floor_selection(scoped):
    store, _ = store_fixture(historical_count=0, filler_count=0)
    current = next(doc for doc in store.docstore._dict.values() if doc.metadata["book"] == "Current Rules")
    current.metadata["layer"] = "codex-base"
    # No historical declaration remains to accidentally trigger scoping.
    scoped.setattr(app, "_CORPUS_MANIFEST", {**manifest(), "books": {"Current Rules": manifest()["books"]["Current Rules"]}})
    scoped.setattr(store, "as_retriever", lambda **kwargs: type("Empty", (), {"invoke": lambda self, q: []})())
    result = app.hybrid_retrieve("needle", store, None, None)
    assert result and result[0]["book"] == "Current Rules" and result[0]["layer"] == "rules"


def test_uninspectable_bm25_rebuilds_from_full_docstore(scoped):
    store, bm25 = store_fixture()
    class Legacy:
        def invoke(self, query):
            return bm25.invoke(query)
    scoped.setattr(store, "as_retriever", lambda **kwargs: type("Empty", (), {"invoke": lambda self, q: []})())
    scoped.setattr(store, "similarity_search", lambda *args, **kwargs: [])
    result = app.hybrid_retrieve("needle", store, Legacy(), None)
    assert {p["book"] for p in result} == {"Current Rules", "Carry Codex"}


def test_uninspectable_scoped_bm25_reports_failure_instead_of_false_zero_hit(scoped):
    class Store:
        def as_retriever(self, **kwargs):
            return type("Empty", (), {"invoke": lambda self, q: []})()
        def similarity_search(self, *args, **kwargs):
            return []
    class Legacy:
        def invoke(self, query):
            return []
    errors = []
    assert app.hybrid_retrieve("needle", Store(), Legacy(), None, errors=errors) == []
    assert any("BM25" in error and "inspectable" in error for error in errors)


def test_manifest_cache_key_does_not_reuse_pre_exclusion_bm25(scoped):
    store, _ = store_fixture()
    if hasattr(app, "_build_bm25"):
        app._build_bm25.clear()
    without = copy.deepcopy(manifest())
    del without["books"]["Faction Pack Archived"]
    scoped.setattr(app, "_CORPUS_MANIFEST", without)
    before = app.build_bm25(store)
    assert any(doc.metadata["book"] == "Faction Pack Archived" for doc in before.docs)
    scoped.setattr(app, "_CORPUS_MANIFEST", manifest())
    after = app.build_bm25(store)
    assert all(doc.metadata["book"] != "Faction Pack Archived" for doc in after.docs)
