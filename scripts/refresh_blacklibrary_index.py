"""Stage a Black Library index refresh, retaining every other document/vector.

Run with ``python -m scripts.refresh_blacklibrary_index``. The output must be a
new directory; publishing is a separate operation after the staged checks pass.
Use the same local BGE-M3 snapshot as the existing index, never a different model.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np
from langchain_community.vectorstores import FAISS


def refresh(store, docs, embeddings):
    if not docs or any(d.metadata.get("source") != "blacklibrary" for d in docs):
        raise ValueError("Expected non-empty Black Library documents")
    retained, reusable, stale = {}, {}, []
    for pos, doc_id in store.index_to_docstore_id.items():
        doc = store.docstore.search(doc_id)
        vector = store.index.reconstruct(pos)
        if doc.metadata.get("source") == "blacklibrary":
            reusable[doc.page_content] = vector.tolist()
            stale.append(doc_id)
        else:
            retained[doc_id] = (doc, vector)
    vectors = [reusable.get(d.page_content) for d in docs]
    missing = sorted((i for i, v in enumerate(vectors) if v is None), key=lambda i: len(docs[i].page_content))
    for offset in range(0, len(missing), 8):
        ids = missing[offset:offset + 8]
        result = embeddings.embed_documents([docs[i].page_content for i in ids])
        if len(result) != len(ids):
            raise ValueError("Embedding count mismatch")
        for i, vector in zip(ids, result):
            vectors[i] = vector
        print("Embedded {}/{} changed documents".format(min(offset + 8, len(missing)), len(missing)), flush=True)
    matrix = np.asarray(vectors, dtype=np.float32)
    if matrix.shape != (len(docs), store.index.d) or not np.isfinite(matrix).all():
        raise ValueError("Embedding dimensions or values do not match the existing index")
    replacement = FAISS.from_embeddings(
        list(zip([d.page_content for d in docs], matrix.tolist())), embeddings,
        metadatas=[d.metadata for d in docs])
    if stale:
        store.delete(stale)
    store.merge_from(replacement)
    positions = {doc_id: pos for pos, doc_id in store.index_to_docstore_id.items()}
    for doc_id, (doc, vector) in retained.items():
        if store.docstore.search(doc_id) != doc or not np.array_equal(store.index.reconstruct(positions[doc_id]), vector):
            raise ValueError("Non-Black-Library content changed")
    assert store.index.ntotal == len(retained) + len(docs)
    return {"removed_blacklibrary": len(stale), "new_blacklibrary": len(docs),
            "embedded": len(missing), "reused": len(docs) - len(missing),
            "retained_documents_and_vectors_verified": len(retained), "total": store.index.ntotal}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, type=Path)
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--model", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists() or not (args.model / "modules.json").is_file():
        parser.error("Use a new output directory and a complete local model snapshot")
    from hf_embeddings_compat import build_huggingface_embeddings
    from db_compile.blacklibrary import build_blacklibrary_docs
    from corpus_manifest import classify_book, load_manifest
    embeddings = build_huggingface_embeddings(
        model_name=str(args.model.resolve()), model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True, "batch_size": 8})
    store = FAISS.load_local(str(args.index), embeddings, allow_dangerous_deserialization=True)
    docs = build_blacklibrary_docs(args.db)
    tag = classify_book("黑图书馆", load_manifest(Path("corpus_manifest.json")))
    for doc in docs:
        doc.metadata.update(tag)
    report = refresh(store, docs, embeddings)
    store.save_local(str(args.out))
    for path in args.index.iterdir():
        if path.is_file() and path.name not in ("index.faiss", "index.pkl", "blacklibrary-refresh.json"):
            shutil.copy2(path, args.out / path.name)
    (args.out / "blacklibrary-refresh.json").write_bytes((json.dumps(report, indent=2) + "\n").encode())
    print(json.dumps(report))


if __name__ == "__main__":
    main()
