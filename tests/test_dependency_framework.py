"""Exercise the supported LangChain APIs without model assets or paid requests."""

import json

import httpx
import numpy as np
import pytest
from langchain_community.retrievers import BM25Retriever
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_experimental.text_splitter import SemanticChunker
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter


class TopicEmbeddings(Embeddings):
    """Small distinct topics make the actual index/chunker behavior observable."""

    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text):
        vector = np.array([1 + text.lower().count("armour"),
                           1 + text.lower().count("shoot"), 1.0])
        return (vector / np.linalg.norm(vector)).tolist()


def test_faiss_serialization_retrievers_and_metadata(tmp_path):
    docs = [Document(id="armour", page_content="Armour armour saves wounds.", metadata={"page": 7, "layer": "rules"}),
            Document(id="shoot", page_content="Shoot shoot ranged weapons.", metadata={"page": 8, "layer": "codex-base"}),
            Document(id="move", page_content="Move warriors across terrain.", metadata={"page": 9, "layer": "codex-base"})]
    embeddings = TopicEmbeddings()
    store = FAISS.from_documents(docs, embeddings)
    store.save_local(str(tmp_path))
    # Only our own just-written test fixture is trusted for pickle loading.
    loaded = FAISS.load_local(str(tmp_path), embeddings, allow_dangerous_deserialization=True)
    np.testing.assert_array_equal(store.index.reconstruct_n(), loaded.index.reconstruct_n())
    assert loaded.index_to_docstore_id == store.index_to_docstore_id
    assert loaded.as_retriever(search_kwargs={"k": 1}).invoke("armour")[0] == docs[0]
    assert loaded.similarity_search("shoot", k=1, filter={"layer": "rules"}) == [docs[0]]
    assert BM25Retriever.from_documents(docs, k=1).invoke("armour")[0] == docs[0]


def test_semantic_and_recursive_chunkers_preserve_source():
    source = "Armour protects warriors. Armour stops wounds. Shoot at enemies. Shoot ranged weapons."
    doc = Document(page_content=source, metadata={"source": "toy.pdf", "page": 3})
    chunks = SemanticChunker(TopicEmbeddings(), breakpoint_threshold_type="percentile",
                             breakpoint_threshold_amount=50).split_documents([doc])
    assert chunks and all(chunk.metadata == doc.metadata for chunk in chunks)
    assert " ".join(chunk.page_content for chunk in chunks) == source
    recursive = RecursiveCharacterTextSplitter(chunk_size=45, chunk_overlap=0).split_documents([doc])
    assert len(recursive) > 1
    assert " ".join(chunk.page_content for chunk in recursive) == source


@pytest.mark.parametrize("model,base_url,extra_body", [
    ("deepseek-flash", "https://api.deepseek.com", {"thinking": {"type": "disabled"}}),
    ("glm-4-flash", "https://open.bigmodel.cn/api/paas/v4/", None),
])
def test_provider_chain_preserves_messages_and_streaming(model, base_url, extra_body):
    requests = []

    def respond(request):
        body = json.loads(request.content)
        requests.append((str(request.url), body))
        chunk = {"id": "toy", "object": "chat.completion.chunk", "created": 1, "model": model,
                 "choices": [{"index": 0, "delta": {"content": "Verified [toy.pdf p3]"}, "finish_reason": None}]}
        return httpx.Response(200, headers={"content-type": "text/event-stream"},
                              text=f"data: {json.dumps(chunk)}\n\ndata: [DONE]\n\n")

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        llm = ChatOpenAI(model=model, api_key="toy-unused", base_url=base_url,
                         http_client=client, streaming=True, extra_body=extra_body)
        prompt = ChatPromptTemplate.from_messages([("system", "Use {context}"),
                                                  ("human", "{question}")])
        answer = "".join((prompt | llm | StrOutputParser()).stream({"context": "toy.pdf p3", "question": "Armour"}))
    assert answer == "Verified [toy.pdf p3]"
    url, body = requests[0]
    assert url == base_url.rstrip("/") + "/chat/completions"
    assert body["model"] == model and body["stream"] is True
    assert body["messages"] == [{"role": "system", "content": "Use toy.pdf p3"},
                                 {"role": "user", "content": "Armour"}]
    if extra_body:
        assert body["thinking"] == extra_body["thinking"]
