import numpy as np
import pytest
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS

from scripts.refresh_blacklibrary_index import refresh


class FakeEmbeddings(Embeddings):
    def __init__(self):
        self.seen = []

    def embed_documents(self, texts):
        self.seen.extend(texts)
        return [[float(len(t)), 1.0] for t in texts]

    def embed_query(self, text):
        return self.embed_documents([text])[0]


def test_refresh_preserves_other_sources_and_reuses_exact_text():
    embed = FakeEmbeddings()
    docs = [Document(page_content=t, metadata={"source": s}) for t, s in
            [("Official rule", "rules.pdf"), ("Old Chinese", "blacklibrary"), ("Same", "blacklibrary")]]
    store = FAISS.from_documents(docs, embed)
    official_id = store.index_to_docstore_id[0]
    official_document = store.docstore.search(official_id)
    official_vector = store.index.reconstruct(0)
    embed.seen.clear()
    result = refresh(store, [Document(page_content=t, metadata={"source": "blacklibrary"})
                             for t in ("New Chinese", "Same")], embed)
    assert embed.seen == ["New Chinese"]
    assert result["removed_blacklibrary"] == 2 and result["reused"] == 1
    assert store.docstore.search(official_id) == official_document
    assert np.array_equal(store.index.reconstruct(0), official_vector)
    assert "Old Chinese" not in [d.page_content for d in store.docstore._dict.values()]


def test_empty_refresh_fails_before_deleting_old_records():
    embed = FakeEmbeddings()
    store = FAISS.from_documents([Document(page_content="Old", metadata={"source": "blacklibrary"})], embed)
    with pytest.raises(ValueError, match="non-empty"):
        refresh(store, [], embed)
    assert store.index.ntotal == 1
