"""ingest.py 加载层/纯函数单测：页码 1-based（C1）、增量去重（H3）、
TLS 白名单（H8）、get_book_name 书名剥离。

说明：import ingest 会执行其顶部的代理环境变量设置与 requests.Session.request
monkeypatch（H8 收窄后仅对 hf-mirror.com 关 verify，其余请求正常校验），
测试全程无网络调用。
"""
from pathlib import Path

import requests
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

import ingest
from ingest import _is_hf_mirror_url, delete_stale_chunks, get_book_name
from tests.conftest import make_pdf


# ── C1：load_pdf 页码 1-based ──

def test_load_pdf_page_metadata_is_one_based(tmp_path):
    """PyMuPDFLoader 原始 page 是 0 起始，load_pdf 必须归一为 1-based，
    与 llm_refine.extract_pages 的约定对齐（引用展示"第X页"）。"""
    pdf = make_pdf(tmp_path / "测试书1.1.pdf",
                   ["FIRST PAGE TEXT", "SECOND PAGE TEXT"])
    docs = ingest.load_pdf(pdf)
    assert [d.metadata["page"] for d in docs] == [1, 2]
    assert all(d.metadata["source"] == str(pdf) for d in docs)
    assert all(d.metadata["book"] == "测试书" for d in docs)


# ── get_book_name：书名剥离规则 ──

def test_get_book_name_strips_version_and_group():
    assert get_book_name(Path("黑暗天使10版中文老湿腐版1.12.pdf")) == "黑暗天使10版中文"
    assert get_book_name(Path("钛帝国十版CODEX-20251112.pdf")) == "钛帝国十版"


def test_get_book_name_keeps_mid_name_digits():
    """文件名中间的数字不得截断（旧策略曾把 '6月4日…' 截成 '6月'）。"""
    assert get_book_name(Path("6月4日分数中文.pdf")) == "6月4日分数中文"


def test_get_book_name_falls_back_to_stem_when_stripped_empty():
    assert get_book_name(Path("1.12.pdf")) == "1.12"


# ── H3：增量入库删除旧 chunk ──

class _FakeEmb:
    """极简假嵌入：固定 4 维向量，仅为构建可用的 FAISS 索引，不做真实编码。"""

    def embed_documents(self, texts):
        return [[float(len(t) % 5) + 1.0, 1.0, 0.0, 0.0] for t in texts]

    def embed_query(self, text):
        return self.embed_documents([text])[0]


def _doc(text, source):
    return Document(page_content=text, metadata={"source": source, "book": "b"})


def test_delete_stale_chunks_removes_only_matching_source():
    store = FAISS.from_documents(
        [_doc("旧A1", "data/a.pdf"), _doc("旧A2", "data/a.pdf"),
         _doc("B1", "data/b.pdf")],
        _FakeEmb(),
    )
    removed = delete_stale_chunks(store, {"data/a.pdf"})
    assert removed == 2
    remaining = [d.metadata["source"] for d in store.docstore._dict.values()]
    assert remaining == ["data/b.pdf"]


def test_delete_stale_chunks_noop_when_no_match():
    store = FAISS.from_documents([_doc("B1", "data/b.pdf")], _FakeEmb())
    assert delete_stale_chunks(store, {"data/zzz.pdf"}) == 0
    assert len(store.docstore._dict) == 1


def test_reingest_same_source_has_no_duplicates():
    """同 source 重入库：先删旧 chunk 再 merge，库内不得新旧并存。"""
    emb = _FakeEmb()
    store = FAISS.from_documents(
        [_doc("单位甲 旧内容", "data/a.pdf"), _doc("B1", "data/b.pdf")], emb)

    new_chunks = [_doc("单位甲 新内容", "data/a.pdf"),
                  _doc("单位甲2 新内容", "data/a.pdf")]
    removed = delete_stale_chunks(
        store, {c.metadata["source"] for c in new_chunks})
    assert removed == 1
    store.merge_from(FAISS.from_documents(new_chunks, emb))

    a_docs = sorted(d.page_content for d in store.docstore._dict.values()
                    if d.metadata["source"] == "data/a.pdf")
    assert a_docs == ["单位甲 新内容", "单位甲2 新内容"]
    assert len(store.docstore._dict) == 3   # a×2 + b×1，无重复


# ── H8：TLS 校验收窄为 hf-mirror.com 单 host ──

def test_is_hf_mirror_url_whitelist():
    assert _is_hf_mirror_url("https://hf-mirror.com/BAAI/bge-m3")
    assert _is_hf_mirror_url("https://cdn.hf-mirror.com/x")
    assert not _is_hf_mirror_url("https://evil-hf-mirror.com/x")
    assert not _is_hf_mirror_url("https://evilhf-mirror.com/x")
    assert not _is_hf_mirror_url("https://pypi.org/simple")
    assert not _is_hf_mirror_url("not a url")


def test_session_request_verify_only_disabled_for_hf_mirror(monkeypatch):
    """monkeypatch 后的 Session.request 只对 hf-mirror.com 注入 verify=False。"""
    calls = {}

    def fake_orig(self, method, url, **kwargs):
        calls[url] = kwargs.get("verify", "default")

    monkeypatch.setattr(ingest, "_orig_request", fake_orig)
    s = requests.Session()
    s.request("GET", "https://hf-mirror.com/models")
    s.request("GET", "https://api.github.com/")
    assert calls["https://hf-mirror.com/models"] is False
    assert calls["https://api.github.com/"] == "default"


def test_ssl_default_context_not_globally_disabled():
    """H8 回归锁：ingest 不得再替换全局 ssl 默认上下文/置空 CA bundle。"""
    import os
    import ssl
    assert ssl._create_default_https_context is not ssl._create_unverified_context
    assert os.environ.get("CURL_CA_BUNDLE") != ""
    assert os.environ.get("REQUESTS_CA_BUNDLE") != ""
