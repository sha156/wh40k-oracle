from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings


def test_exact_text_reuse_preserves_order_vectors_and_new_source_metadata():
    from ingest import build_faiss_with_progress
    class Embedder(Embeddings):
        def __init__(self):
            self.seen = []
        def embed_documents(self, texts):
            self.seen.extend(texts)
            return [[float(len(t)), 1.0] for t in texts]
        def embed_query(self, text):
            return [float(len(text)), 1.0]
    embedding = Embedder()
    chunks = [Document(page_content="unchanged", metadata={"page": 9}),
              Document(page_content="longer new text", metadata={"page": 2}),
              Document(page_content="new", metadata={"page": 3})]
    store = build_faiss_with_progress(chunks, embedding, {"unchanged": [99.0, 1.0]})
    assert embedding.seen == ["new", "longer new text"]
    assert store.index.reconstruct(0).tolist() == [99.0, 1.0]
    assert store.index.reconstruct(1).tolist() == [15.0, 1.0]
    assert store.index.reconstruct(2).tolist() == [3.0, 1.0]
    assert store.docstore.search(store.index_to_docstore_id[0]).metadata == {"page": 9}
