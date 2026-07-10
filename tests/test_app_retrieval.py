"""app.py 可独立导入的纯函数单测：RRF 融合、查询扩展（测试补课，M）。

说明：import app 会执行模块级 Streamlit 调用（st.set_page_config 等）——
bare 模式（无 ScriptRunContext）下 Streamlit 只打告警不抛异常；jieba/
terms.json/wh40k.sqlite 的加载均为本地文件读取，无网络副作用。
"""
from langchain_core.documents import Document

from app import expand_query, reciprocal_rank_fusion


def _doc(text, source="s.pdf", page=1):
    return Document(page_content=text, metadata={"source": source, "page": page})


# ── reciprocal_rank_fusion ──

def test_rrf_doc_in_both_lists_ranks_first():
    shared = _doc("同时命中", page=3)
    faiss_docs = [_doc("向量第一", page=1), shared]
    bm25_docs = [shared, _doc("关键词第二", page=2)]
    merged = reciprocal_rank_fusion(faiss_docs, bm25_docs)
    assert merged[0].page_content == "同时命中"   # 双榜命中得分最高
    assert len(merged) == 3                       # 去重后 3 条


def test_rrf_empty_inputs_returns_empty():
    assert reciprocal_rank_fusion([], []) == []


def test_rrf_single_list_preserves_order():
    docs = [_doc("a", page=1), _doc("b", page=2), _doc("c", page=3)]
    merged = reciprocal_rank_fusion(docs, [])
    assert [d.page_content for d in merged] == ["a", "b", "c"]


def test_rrf_dedup_uses_source_page_and_prefix():
    """同 source+page+前50字符 视为同一文档，只保留一份。"""
    a1 = _doc("完全相同的内容", source="x.pdf", page=7)
    a2 = _doc("完全相同的内容", source="x.pdf", page=7)
    merged = reciprocal_rank_fusion([a1], [a2])
    assert len(merged) == 1


# ── expand_query ──

def test_expand_query_appends_alias_and_keeps_original():
    q = "激素虫的移动力是多少"
    out = expand_query(q)
    assert out.startswith(q)     # 扩展而非替换，原词保留
    assert "刀虫" in out          # UNIT_ALIASES: 激素虫 → 刀虫


def test_expand_query_no_alias_returns_unchanged():
    # 纯 ASCII 查询不可能命中任何中文别名键
    q = "hello world 12345"
    assert expand_query(q) == q
